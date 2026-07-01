from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any


CHROME_EPOCH_MICROS = 11644473600000000
DEFAULT_PROFILE_NAME = "Default"


@dataclass(frozen=True)
class BookmarkEntry:
    title: str
    url: str
    folder_path: str


def get_default_bookmarks_path() -> Path:
    return get_profile_bookmarks_path("Default")


def get_configured_profile_name() -> str:
    profile = os.getenv("CHROME_PROFILE_NAME", DEFAULT_PROFILE_NAME).strip()
    return profile or DEFAULT_PROFILE_NAME


def get_chrome_user_data_dir() -> Path:
    custom_dir = os.getenv("CHROME_USER_DATA_DIR", "").strip()
    if custom_dir:
        return Path(custom_dir).expanduser()

    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"

    if system == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        if local_app_data:
            return Path(local_app_data) / "Google" / "Chrome" / "User Data"
        return Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"

    if system == "Linux":
        candidates = [
            Path.home() / ".config" / "google-chrome",
            Path.home() / ".config" / "chromium",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"


def get_profile_bookmarks_path(profile_name: str | None = None) -> Path:
    resolved_profile = (profile_name or get_configured_profile_name()).strip() or DEFAULT_PROFILE_NAME
    return get_chrome_user_data_dir() / resolved_profile / "Bookmarks"


def load_bookmarks(bookmarks_path: Path | None = None) -> dict[str, Any]:
    path = bookmarks_path or get_profile_bookmarks_path()
    if not path.exists():
        raise FileNotFoundError(f"Chrome bookmarks file was not found at: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_bookmarks(data: dict[str, Any]) -> list[BookmarkEntry]:
    roots = data.get("roots", {})
    entries: list[BookmarkEntry] = []

    def walk(node: dict[str, Any], parents: list[str]) -> None:
        node_type = node.get("type")
        if node_type == "url":
            entries.append(
                BookmarkEntry(
                    title=node.get("name", ""),
                    url=node.get("url", ""),
                    folder_path=" / ".join(parents) if parents else "(root)",
                )
            )
            return

        if node_type == "folder" or "children" in node:
            node_name = node.get("name", "")
            next_parents = parents + ([node_name] if node_name else [])
            for child in node.get("children", []):
                if isinstance(child, dict):
                    walk(child, next_parents)

    for root_name in ("bookmark_bar", "other", "synced"):
        root = roots.get(root_name)
        if isinstance(root, dict):
            pretty_root = {
                "bookmark_bar": "Bookmarks Bar",
                "other": "Other Bookmarks",
                "synced": "Mobile Bookmarks",
            }.get(root_name, root_name)
            walk(root, [pretty_root])

    return entries


def list_bookmark_folders(data: dict[str, Any]) -> list[str]:
    roots = data.get("roots", {})
    folders: list[str] = []

    def walk(node: dict[str, Any], parents: list[str]) -> None:
        if not isinstance(node, dict):
            return

        node_name = node.get("name", "")
        next_parents = parents + ([node_name] if node_name else [])
        if next_parents:
            folders.append(" / ".join(next_parents))

        for child in node.get("children", []):
            if isinstance(child, dict) and child.get("type") == "folder":
                walk(child, next_parents)

    for root_name in ("bookmark_bar", "other", "synced"):
        root = roots.get(root_name)
        if not isinstance(root, dict):
            continue
        pretty_root = {
            "bookmark_bar": "Bookmarks Bar",
            "other": "Other Bookmarks",
            "synced": "Mobile Bookmarks",
        }.get(root_name, root_name)
        walk(root, [pretty_root])

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(folders))


def _split_folder_path(folder_path: str) -> list[str]:
    normalized = folder_path.replace(" / ", "/")
    return [part.strip() for part in normalized.split("/") if part.strip()]


def _root_info(first_segment: str) -> tuple[str, str] | None:
    normalized = first_segment.strip().lower()
    alias_map = {
        "bookmarks bar": ("bookmark_bar", "Bookmarks Bar"),
        "bookmark bar": ("bookmark_bar", "Bookmarks Bar"),
        "bar": ("bookmark_bar", "Bookmarks Bar"),
        "other bookmarks": ("other", "Other Bookmarks"),
        "other": ("other", "Other Bookmarks"),
        "mobile bookmarks": ("synced", "Mobile Bookmarks"),
        "synced": ("synced", "Mobile Bookmarks"),
    }
    return alias_map.get(normalized)


def find_folder_node(data: dict[str, Any], folder_path: str) -> tuple[dict[str, Any], str] | None:
    parts = _split_folder_path(folder_path)
    if not parts:
        return None

    root = _root_info(parts[0])
    if root is None:
        return None

    root_key, root_label = root
    node = data.get("roots", {}).get(root_key)
    if not isinstance(node, dict):
        return None

    traversed = [root_label]
    for part in parts[1:]:
        match: dict[str, Any] | None = None
        for child in node.get("children", []):
            if (
                isinstance(child, dict)
                and child.get("type") == "folder"
                and str(child.get("name", "")).strip().lower() == part.strip().lower()
            ):
                match = child
                break
        if match is None:
            return None
        node = match
        traversed.append(str(node.get("name", "")).strip() or part.strip())

    return node, " / ".join(traversed)


def filter_bookmarks(
    entries: list[BookmarkEntry],
    query: str | None = None,
    folder: str | None = None,
    limit: int = 30,
) -> list[BookmarkEntry]:
    query_norm = (query or "").strip().lower()
    folder_norm = (folder or "").strip().lower()

    filtered = []
    for entry in entries:
        if query_norm:
            haystack = f"{entry.title} {entry.url} {entry.folder_path}".lower()
            if query_norm not in haystack:
                continue
        if folder_norm and folder_norm not in entry.folder_path.lower():
            continue
        filtered.append(entry)

    return filtered[: max(limit, 1)]


def _find_max_id(node: dict[str, Any]) -> int:
    max_id = 0

    def walk(current: Any) -> None:
        nonlocal max_id
        if isinstance(current, dict):
            node_id = current.get("id")
            if isinstance(node_id, str) and node_id.isdigit():
                max_id = max(max_id, int(node_id))
            for value in current.values():
                walk(value)
        elif isinstance(current, list):
            for item in current:
                walk(item)

    walk(node)
    return max_id


def chrome_timestamp_now() -> str:
    unix_micros = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    return str(CHROME_EPOCH_MICROS + unix_micros)


def ensure_bookmarks_bar(data: dict[str, Any]) -> dict[str, Any]:
    roots = data.setdefault("roots", {})
    bar = roots.get("bookmark_bar")
    if isinstance(bar, dict):
        bar.setdefault("children", [])
        bar.setdefault("name", "Bookmarks bar")
        bar.setdefault("type", "folder")
        bar.setdefault("id", str(_find_max_id(data) + 1))
        return bar

    bar = {
        "children": [],
        "date_added": chrome_timestamp_now(),
        "date_last_used": "0",
        "date_modified": chrome_timestamp_now(),
        "guid": "",
        "id": str(_find_max_id(data) + 1),
        "name": "Bookmarks bar",
        "type": "folder",
    }
    roots["bookmark_bar"] = bar
    return bar


def is_safe_to_write_bookmarks() -> tuple[bool, str]:
    try:
        import subprocess

        proc = subprocess.run(
            ["pgrep", "-x", "Google Chrome"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return True, "Warning: Google Chrome appears to be running. Bookmark changes will still be written."
    except Exception:
        pass

    return True, "safe"


def add_bookmark_to_bar(
    data: dict[str, Any],
    url: str,
    title: str,
) -> dict[str, str]:
    bar = ensure_bookmarks_bar(data)
    children = bar.setdefault("children", [])

    next_id = str(_find_max_id(data) + 1)
    now = chrome_timestamp_now()
    node = {
        "date_added": now,
        "date_last_used": "0",
        "guid": "",
        "id": next_id,
        "name": title,
        "type": "url",
        "url": url,
    }

    children.append(node)
    bar["date_modified"] = now
    return {"id": next_id, "name": title, "url": url, "folder": "Bookmarks Bar"}


def add_bookmark_to_folder(
    data: dict[str, Any],
    url: str,
    title: str,
    folder_path: str,
) -> dict[str, str]:
    folder_match = find_folder_node(data, folder_path)
    if folder_match is None:
        raise LookupError(f"Bookmark folder not found: {folder_path}")

    folder_node, canonical_folder_path = folder_match
    children = folder_node.setdefault("children", [])

    next_id = str(_find_max_id(data) + 1)
    now = chrome_timestamp_now()
    node = {
        "date_added": now,
        "date_last_used": "0",
        "guid": "",
        "id": next_id,
        "name": title,
        "type": "url",
        "url": url,
    }

    children.append(node)
    folder_node["date_modified"] = now
    return {"id": next_id, "name": title, "url": url, "folder": canonical_folder_path}


def backup_and_write(data: dict[str, Any], bookmarks_path: Path | None = None) -> tuple[Path, Path]:
    path = bookmarks_path or get_default_bookmarks_path()
    if not path.exists():
        raise FileNotFoundError(f"Chrome bookmarks file was not found at: {path}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"Bookmarks.backup.{timestamp}.json")
    shutil.copy2(path, backup_path)

    temp_path = path.with_name(f"Bookmarks.tmp.{timestamp}.json")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)

    return backup_path, path
