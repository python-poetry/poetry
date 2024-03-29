#!/usr/bin/env bash
#
# Copyright 2024 Bjorn Neergaard
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
#
# This script is used to automatically create backport pull requests. It is
# smart enough to require no arguments if run against a PR branch, assuming the
# upstream repo conforms to the default prefixes. Target branches will be
# determined by labels present on the original pull request.
#
# It is capable of handling PRs merged with a commit, by rebase and by
# squash-and-rebase. The backport pull request will have its title, body and
# labels derived from the original. The cherry-picked comments can be signed off,
# and a comment will be created if requested.
#
# In particular, this script assumes the 'origin' remote points to the target
# repository for backports. We also assume we can freely clobber local and remote
# branches using our backport branch naming scheme and that you don't mind if we
# prune your worktrees for you.
#
# This script can push the backport branches to a fork if a corresponding
# --remote is passed.

basename=${0##*/}

# Check for Homebrew-installed getopt on macOS.
for g in /{usr/local,opt/homebrew}/opt/gnu-getopt/bin/getopt; do
    test -x "$g" && : GETOPT="${GETOPT:=$g}" && break
done || : GETOPT="${GETOPT:=getopt}"

"${GETOPT}" --test >/dev/null
if [ $? -ne 4 ]; then
    printf >&2 '%s: GNU getopt is required, please ensure it is available in the PATH\n' "$basename"
    exit 1
fi

if ! command -v gh >/dev/null; then
    printf >&2 "%s: the GitHub CLI (\`gh') is required, please ensure it is available in the PATH\n" "$basename"
fi

usage() {
    printf >&2 '%s -h|--help\n' "$basename"
    printf >&2 '%s [-s|--signoff] [-c|--comment] --pr [pr] --remote [remote] --branch-prefix [prefix] --label-prefix [prefix]\n' "$basename"
}

args="$("${GETOPT}" -o h,s,c -l help,signoff,comment,pr:,remote:,branch-prefix:,label-prefix: -n "$basename" -- "$@")" || exit $?
eval set -- "$args"
unset args

while [ "$#" -gt 0 ]; do
    case "$1" in
    --pr | --remote | --branch-prefix | --label-prefix)
        flag="${1:2}"
        printf -v "${flag//-/_}" '%s' "$2"
        shift 2
        ;;
    -s | --signoff)
        signoff=1
        shift
        ;;
    -c | --comment)
        comment=1
        shift
        ;;
    -h | --help)
        usage
        exit
        ;;
    -- | *)
        shift
        break
        ;;
    esac
done

set -eux -o pipefail

# Determine the number of the target pull request, if not already supplied.
: pr="${pr:=$(gh pr view --json number --jq '.number')}"

# Use the 'origin' remote by default; if a fork is desired, a corresponding remote should
# be specified, e.g. `gh repo fork --remote-name fork` and `--remote fork`.
: remote="${remote:=origin}"

# Use 'backport/' as a default prefix for both the resulting branch and the triggering label.
: branch_prefix="${branch_prefix:=backport/}"
: label_prefix="${label_prefix:=backport/}"

# Determine the owner of the target remote (necessary to open a pull request) based on the URL.
remote_owner=$(basename "$(dirname "$(git remote get-url --push "$remote")")")

# Get the state, base branch and merge commit (if it exists) of the pull request.
pr_meta=$(gh pr view --json state,baseRefName,mergeCommit --jq '[.state,.baseRefName,.mergeCommit.oid][]' "$pr")
pr_state=$(sed '1q;d' <<<"$pr_meta")
pr_base=$(sed '2q;d' <<<"$pr_meta")
pr_mergecommit=$(sed '3q;d' <<<"$pr_meta")

# Get the list of commits present in the pull request.
pr_commits=$(gh pr view --json commits --jq '.commits[].oid' "$pr")

# Get the title and body of the pull request.
pr_title_body=$(gh pr view --json title,body --jq '[.title,.body][]' "$pr")
pr_title=$(head -n 1 <<<"$pr_title_body")
pr_body=$(tail -n +2 <<<"$pr_title_body")
# Gather the list of labels on the pull request.
pr_labels=$(gh pr view --json labels --jq '.labels[].name' "$pr")

# Fetch origin, to ensure we have the latest commits on all upstream branches.
git fetch origin
# Fetch the latest pull request head, to ensure we have all commits available locally.
# It will be available as FETCH_HEAD for the remainder of this script.
git fetch origin "refs/pull/${pr}/head"

# Determine which commits should be cherry-picked. This can be surprisingly complex,
# but the typical cases present on GitHub are handled here.
if [ "$pr_state" = OPEN ] || [ "$(git rev-list --no-walk --count --merges "$pr_mergecommit")" -eq 1 ]; then
    # Unmerged, or merge commit: the list of commits is equivalent to the pull request.
    backport_commits=$pr_commits
else
    # The cherry commits represent those commits that were cherry-picked from the pull request to the base.
    pr_cherry_commits=$(git cherry refs/remotes/origin/main FETCH_HEAD | sed -n '/^- / s/- //p')
    # The rebased commits represent those commits present in the base that correspond to the pull request.
    pr_rebased_commits=$(git cherry FETCH_HEAD refs/remotes/origin/main | sed -n '/^- / s/- //p')

    # Look for cherry-picks (which is what a conflict-free and non-interactive rebase merge
    # effectively does). Note that a squash confuses the list of rebased commits;
    # to make our heuristics as effective as possible, we have two checks:
    # * Git must successfully identify the list of commits cherry-picked from the PR.
    # * The number of commits in the pull request and identified for backport must match.
    if [ "$pr_cherry_commits" = "$pr_commits" ] \
        && [ "$(wc -l <<<"$pr_rebased_commits")" -eq "$(wc -l <<<"$pr_commits")" ]; then
        # Rebase: the list of commits is those rebased into the base branch.
        backport_commits=$pr_rebased_commits
    else
        # Squash-and-rebase: the list of commits is the singular merged commit.
        backport_commits=$pr_mergecommit
    fi
fi

# Create a temporary directory in which to hold worktrees for each backport attempt.
workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"; git worktree prune -v' EXIT

# Create some arrays to track success and failure.
backport_urls=()
failed_backports=()

# Iterate over all labels matching the prefix to determine what branches must be backported.
while IFS= read -r backport_label; do
    target_branch="${backport_label/#${label_prefix}}"
    backport_branch="${branch_prefix}${pr}-${target_branch}"

    # Check that the target branch and base branch are not the same. This heads off some
    # potential errors.
    if [ "$target_branch" = "$pr_base" ]; then
        continue
    fi

    # Create a new backport branch, in a new worktree, based on the target branch.
    backport_worktree="${workdir}/${backport_branch}"
    git worktree add -B "$backport_branch" "$backport_worktree" "refs/remotes/origin/${target_branch}"

    # Cherry-pick the commits from the target branch in order.
    for commit in $backport_commits; do
        if ! git -C "$backport_worktree" cherry-pick -x ${signoff:+-s} "$commit"; then
            # If a cherry-pick fails, record the branch and move on.
            failed_backports+=("$target_branch")
            continue 2
        fi
    done

    # Push the resulting backport branch to the configured remote.
    git push -f "$remote" "$backport_branch"

    # Create a derived title and label for the PR.
    backport_title="[${target_branch} backport] ${pr_title}"
    backport_body="Backport #${pr} to ${target_branch}."
    if [ -n "$pr_body" ]; then
        backport_body+=$'\n\n'"---"$'\n\n'"$pr_body"
    fi
    # Determine which labels should be brought over to the new pull request, formatted as the CLI expects.
    backport_labels=$(grep -v "^${label_prefix}" <<<"$pr_labels" | head -c -1 | tr '\n' ',')

    # Check for any open backports; note this is a heuristic as we just grab the first pull request
    # that matches our generated branch name. This is unlikely to fail as we filter by author, however.
    backport_url=$(gh pr list --author '@me' --head "$backport_branch" --json url --jq 'first(.[].url)')
    if [ -n "$backport_url" ]; then
        # Update the pull request title and body.
        # TODO: update labels?
        gh pr edit "$backport_url" --title "$backport_title" --body "$backport_body"
        found_backport=1
    else
        # Create a new pull request from the backport branch, against the target branch.
        backport_url=$(gh pr create --base "$target_branch" --head "${remote_owner}:${backport_branch}" \
            --title "$backport_title" --body-file - \
            --label "$backport_labels" \
            <<<"$backport_body" | tail -n 1)
    fi

    # Track this successful backport.
    backport_urls+=("$backport_url")
done < <(grep "^${label_prefix}" <<<"$pr_labels")

if [ -n "${comment:-}" ]; then
    # Generate a comment on the original PR, recording what backports we opened (or failed to open).
    if [ "${#backport_urls[@]}" -gt 0 ]; then
        comment_body+="Automated backport PRs opened:"$'\n'
        for backport_url in "${backport_urls[@]}"; do
            comment_body+="* ${backport_url}"$'\n'
        done
        comment_body+=$'\n'
    fi

    if [ "${#failed_backports[@]}" -gt 0 ]; then
        comment_body+="Backports failed on the following branches:"
        for failed_backport in "${failed_backports[@]}"; do
            comment_body+="* ${failed_backport}"$'\n'
        done
        comment_body+=$'\n'

        # If we're running in GitHub actions, link to the run log to diagnose why a backport failed.
        if [ -n "${GITHUB_ACTIONS:-}" ]; then
            comment_body+="Inspect the run at ${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
        fi
    fi

    if [ -n "$comment_body" ]; then
        # If we had any matches for an existing PR, we'll go ahead and assume we already commented.
        # Edit the existing comment instead.
        gh pr comment "$pr" ${found_backport:+--edit-last} --body-file - <<<"$comment_body"
    fi
fi
