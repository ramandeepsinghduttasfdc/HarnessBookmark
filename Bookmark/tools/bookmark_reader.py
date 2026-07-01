from __future__ import annotations

from core.chrome_bookmarks import filter_bookmarks, flatten_bookmarks, get_profile_bookmarks_path, list_bookmark_folders, load_bookmarks


def list_chrome_bookmarks(
    query: str | None = None,
    folder: str | None = None,
    limit: int = 25,
) -> dict[str, object]:
    """List bookmarks from configured Chrome profile with optional query/folder filters."""
    data = load_bookmarks(get_profile_bookmarks_path())
    all_entries = flatten_bookmarks(data)
    selected = filter_bookmarks(all_entries, query=query, folder=folder, limit=limit)

    return {
        "total_found": len(selected),
        "total_available": len(all_entries),
        "items": [
            {
                "title": entry.title,
                "url": entry.url,
                "folder": entry.folder_path,
            }
            for entry in selected
        ],
    }


def list_chrome_bookmark_folders(limit: int = 200) -> dict[str, object]:
    """List available bookmark folders for configured Chrome profile."""
    data = load_bookmarks(get_profile_bookmarks_path())
    folders = list_bookmark_folders(data)
    safe_limit = max(limit, 1)
    return {
        "total_folders": len(folders),
        "folders": folders[:safe_limit],
    }
