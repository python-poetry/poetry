from __future__ import annotations


def get_request_title(request: str, implementation: str, free_threaded: bool) -> str:
    add_info = implementation
    if free_threaded:
        add_info += ", free-threaded"
    return f"<c1>{request}</> (<b>{add_info}</>)"
