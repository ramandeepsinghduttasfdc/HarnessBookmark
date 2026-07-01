from __future__ import annotations

from urllib.parse import urlparse

from core.chrome_bookmarks import add_bookmark_to_folder, backup_and_write, get_profile_bookmarks_path, is_safe_to_write_bookmarks, list_bookmark_folders, load_bookmarks


def _normalize_url(url: str) -> str:
    text = url.strip()
    if not text:
        raise ValueError("URL cannot be empty.")

    if "://" not in text:
        text = f"https://{text}"

    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be a valid http/https address.")

    return text


def create_chrome_bookmark(url: str, title: str, folder: str | None = None) -> dict[str, object]:
    """Create a new bookmark in a specific folder path for configured Chrome profile."""
    if folder is None or not folder.strip():
        return {
            "status": "folder_required",
            "message": "Please provide a destination folder path, for example: Bookmarks Bar / Work.",
            "suggestion": "Use list_chrome_bookmark_folders to see available folder structures.",
        }

    is_safe, reason = is_safe_to_write_bookmarks()

    normalized_url = _normalize_url(url)
    final_title = title.strip() or normalized_url

    profile_bookmarks_path = get_profile_bookmarks_path()
    data = load_bookmarks(profile_bookmarks_path)
    try:
        created = add_bookmark_to_folder(
            data,
            url=normalized_url,
            title=final_title,
            folder_path=folder,
        )
    except LookupError:
        available_folders = list_bookmark_folders(data)
        return {
            "status": "folder_not_found",
            "requested_folder": folder,
            "message": "The destination folder does not exist in Chrome bookmarks.",
            "suggestion": "Use list_chrome_bookmark_folders and choose one of the existing folder paths.",
            "available_folders_preview": available_folders[:25],
        }

    backup_path, bookmarks_path = backup_and_write(data, profile_bookmarks_path)

    result = {
        "status": "created",
        "bookmark_id": created["id"],
        "title": created["name"],
        "url": created["url"],
        "folder": created["folder"],
        "backup_file": str(backup_path),
        "bookmarks_file": str(bookmarks_path),
    }

    if reason != "safe":
        result["warning"] = reason

    return result
