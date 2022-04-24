#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s nullglob

cd "$(dirname "$(readlink -f "${BASH_SOURCE[@]}")")"

versions=( "$@" )
if [ ${#versions[@]} -eq 0 ]; then
	versions=( */ )
	json='{}'
else
	json="$(< versions.json)"
fi
versions=( "${versions[@]%/}" )

has_linux_version() {
	local dir="$1"; shift
	local dirVersion="$1"; shift
	local fullVersion="$1"; shift

	if ! wget -q -O /dev/null -o /dev/null --spider "https://www.python.org/ftp/python/$dirVersion/Python-$fullVersion.tar.xz"; then
		return 1
	fi

	return 0
}

has_windows_version() {
	# shellcheck disable=SC2034
	local dir="$1"; shift
	local dirVersion="$1"; shift
	local fullVersion="$1"; shift

	if ! wget -q -O /dev/null -o /dev/null --spider "https://www.python.org/ftp/python/$dirVersion/python-$fullVersion-amd64.exe"; then
		return 1
	fi

	return 0
}

for version in "${versions[@]}"; do
	rcVersion="${version%-rc}"
	export version rcVersion

	rcGrepV='-v'
	if [ "$rcVersion" != "$version" ]; then
		rcGrepV=
	fi

	mapfile -t possibles < <(
		{
			git ls-remote --tags https://github.com/python/cpython.git "refs/tags/v${rcVersion}.*" \
				| sed -r 's!^.*refs/tags/v([0-9a-z.]+).*$!\1!' \
				| grep "$rcGrepV" -E -- '[a-zA-Z]+' \
				|| :

			# this page has a very aggressive varnish cache in front of it, which is why we also scrape tags from GitHub
			curl -fsSL 'https://www.python.org/ftp/python/' \
				| grep '<a href="'"$rcVersion." \
				| sed -r 's!.*<a href="([^"/]+)/?".*!\1!' \
				| grep "$rcGrepV" -E -- '[a-zA-Z]+' \
				|| :
		} | sort -ruV
	)
	fullVersion=
	hasWindows=
	declare -A impossible=()
	for possible in "${possibles[@]}"; do
		rcPossible="${possible%%[a-z]*}"

		# varnish is great until it isn't (usually the directory listing we scrape below is updated/uncached significantly later than the release being available)
		if has_linux_version "$version" "$rcPossible" "$possible"; then
			fullVersion="$possible"
			if has_windows_version "$version" "$rcPossible" "$possible"; then
				hasWindows=1
			fi
			break
		fi

		if [ -n "${impossible[$rcPossible]:-}" ]; then
			continue
		fi
		impossible[$rcPossible]=1
		mapfile -t possibleVersions < <(
			wget -qO- -o /dev/null "https://www.python.org/ftp/python/$rcPossible/" \
				| grep '<a href="Python-'"$rcVersion"'.*\.tar\.xz"' \
				| sed -r 's!.*<a href="Python-([^"/]+)\.tar\.xz".*!\1!' \
				| grep "$rcGrepV" -E -- '[a-zA-Z]+' \
				| sort -rV \
				|| true
		)
		for possibleVersion in "${possibleVersions[@]}"; do
			if has_linux_version "$version" "$rcPossible" "$possibleVersion"; then
				fullVersion="$possibleVersion"
				if has_windows_version "$version" "$rcPossible" "$possible"; then
					hasWindows=1
				fi
				break
			fi
		done
	done

	if [ -z "$fullVersion" ]; then
		{
			echo
			echo
			echo "  error: cannot find $version (alpha/beta/rc?)"
			echo
			echo
		} >&2
		exit 1
	fi

	pythonVersion=$fullVersion
	echo "poetry: (python $pythonVersion${hasWindows:+, windows})"

	export pythonVersion hasWindows
	json="$(jq <<<"$json" -c '
		.[env.version] = {
			python: {
				version: env.pythonVersion
			},
			variants: [
				(
					"bullseye",
					"buster"
				| ., "slim-" + .), # https://github.com/docker-library/ruby/pull/142#issuecomment-320012893
				(
					"3.15",
					"3.14"
				| "alpine" + .),
				if env.hasWindows != "" then
					(
						"ltsc2022",
						"1809"
					| "windows/windowsservercore-" + .)
				else empty end
			],
		}
	')"
done

jq <<<"$json" -S . > versions.json
