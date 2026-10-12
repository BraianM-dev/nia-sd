"""Low-cost game discovery for SteamOS, Steam, Heroic and custom game roots.

The scanner reads manifests and /proc only. It never injects into a game process
or reads process memory.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_APPID_RE = re.compile(r'"appid"\s+"(\d+)"', re.IGNORECASE)
_NAME_RE = re.compile(r'"name"\s+"([^"]+)"', re.IGNORECASE)
_INSTALL_RE = re.compile(r'"installdir"\s+"([^"]+)"', re.IGNORECASE)
_LIBRARY_PATH_RE = re.compile(r'"(?:path|\d+)"\s+"([^"]+)"', re.IGNORECASE)
_SKIP_NAMES = {
    "heroic", "epic", "gog", "lutris", "steam", "games", "compatdata",
    "compatibilitytools.d", "downloads", "prefixes", "redistributables",
}
_SKIP_PROCESSES = {
    "steam", "steamwebhelper", "gamescope", "wineserver", "wine",
    "proton", "explorer.exe", "launcher.exe", "crashpad_handler", "crashhandler.exe",
    "unitycrashhandler64.exe", "epicgameslauncher.exe", "goggalaxy.exe",
    "heroic", "legendary", "lutris", "pressure-vessel",
}


def _steam_roots() -> List[Path]:
    home = Path.home()
    candidates = [
        home / ".steam" / "steam",
        home / ".local" / "share" / "Steam",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
    ]
    roots: List[Path] = []
    for candidate in candidates:
        if candidate.exists():
            roots.append(candidate)
    return roots


def _library_roots(steam_roots: Iterable[Path]) -> List[Path]:
    roots: List[Path] = list(steam_roots)
    for root in list(roots):
        manifest = root / "steamapps" / "libraryfolders.vdf"
        if not manifest.exists():
            continue
        try:
            text = manifest.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in _LIBRARY_PATH_RE.finditer(text):
            raw_path = match.group(1).replace("\\\\", "/")
            candidate = Path(raw_path).expanduser()
            if candidate.exists():
                roots.append(candidate)
    unique: Dict[str, Path] = {}
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        unique[str(resolved)] = resolved
    return list(unique.values())


def default_game_roots() -> List[Path]:
    home = Path.home()
    roots = [home / "Games", home / "Games" / "Heroic", home / "Games" / "GOG",
             home / "Games" / "Epic", home / ".local" / "share" / "lutris" / "runners"]
    for library in _library_roots(_steam_roots()):
        roots.append(library / "steamapps" / "common")
    return [path for path in roots if path.exists()]


def _inside(path: Path, roots: Sequence[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except (OSError, ValueError):
            pass
    return False


def scan_installed_games(custom_roots: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """Return Steam manifest entries and game folders from common launcher roots."""
    supplied = [Path(os.path.expandvars(os.path.expanduser(str(p)))) for p in (custom_roots or [])]
    custom_libraries = [p for p in supplied if (p / "steamapps").is_dir()]
    steam_roots = _library_roots([*_steam_roots(), *custom_libraries])
    result: Dict[str, Dict[str, Any]] = {}
    for library in steam_roots:
        apps = library / "steamapps"
        if not apps.is_dir():
            continue
        for manifest in apps.glob("appmanifest_*.acf"):
            try:
                text = manifest.read_text(encoding="utf-8", errors="ignore")
                appid_match = _APPID_RE.search(text)
                if not appid_match:
                    continue
                appid = appid_match.group(1)
                title_match = _NAME_RE.search(text)
                install_match = _INSTALL_RE.search(text)
                title = title_match.group(1) if title_match else "Juego Steam " + appid
                install_path = apps / "common" / install_match.group(1) if install_match else apps / "common"
                game_id = "steam:" + appid
                result[game_id] = {
                    "id": game_id, "appid": appid, "title": title,
                    "platform": "Steam", "install_path": str(install_path),
                }
            except OSError:
                continue

    roots = default_game_roots()
    for path in supplied:
        if path.exists():
            roots.append(path)
    for root in roots:
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or child.name.casefold() in _SKIP_NAMES:
                continue
            # Steam titles already come from app manifests; avoid duplicate catalog rows.
            if "steamapps" in str(root).casefold():
                continue
            key = str(child.resolve())
            result.setdefault("folder:" + key, {
                "id": "folder:" + key, "appid": "", "title": child.name,
                "platform": _platform_for_path(child), "install_path": key,
            })
    return sorted(result.values(), key=lambda item: item["title"].casefold())


def _platform_for_path(path: Path) -> str:
    lowered = str(path).casefold()
    if "heroic" in lowered:
        return "Heroic"
    if "gog" in lowered:
        return "GOG"
    if "epic" in lowered:
        return "Epic / Heroic"
    if "lutris" in lowered:
        return "Lutris"
    return "No Steam / carpeta personalizada"


def _read_proc(pid: str, name: str) -> bytes:
    try:
        return (Path("/proc") / pid / name).read_bytes()
    except (OSError, PermissionError):
        return b""


def _process_environment(pid: str) -> Dict[str, str]:
    raw = _read_proc(pid, "environ")
    values: Dict[str, str] = {}
    for part in raw.split(b"\0"):
        if b"=" not in part:
            continue
        key, value = part.split(b"=", 1)
        try:
            k = key.decode("utf-8", errors="ignore")
            if k in {"SteamAppId", "SteamGameId", "STEAM_COMPAT_DATA_PATH", "WINEPREFIX"}:
                values[k] = value.decode("utf-8", errors="ignore")
        except Exception:
            continue
    return values


def find_running_game(custom_roots: Optional[Iterable[str]] = None,
                      catalog: Optional[Sequence[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """Find a foreground game by Steam app id or executable path, independent of store."""
    roots = default_game_roots()
    roots.extend(Path(os.path.expandvars(os.path.expanduser(str(p)))) for p in custom_roots or [])
    roots = [p for p in roots if p.exists()]
    games = list(catalog or scan_installed_games(custom_roots))
    by_appid = {str(game.get("appid")): game for game in games if game.get("appid")}
    try:
        pids = [entry.name for entry in Path("/proc").iterdir() if entry.name.isdigit()]
    except OSError:
        return None

    for pid in pids:
        comm_raw = _read_proc(pid, "comm")
        comm = comm_raw.decode("utf-8", errors="ignore").strip()
        if not comm or comm.casefold() in _SKIP_PROCESSES:
            continue
        env = _process_environment(pid)
        appid = env.get("SteamAppId") or env.get("SteamGameId")
        if appid and appid in by_appid:
            game = dict(by_appid[appid])
            game.update({"process_id": int(pid), "process_name": comm, "session_key": game["id"]})
            return game

        cmdline = _read_proc(pid, "cmdline").decode("utf-8", errors="ignore").split("\0")
        exe_candidates: List[Path] = []
        other_candidates: List[Path] = []
        for arg in cmdline:
            candidate = Path(arg.strip('"')).expanduser()
            if not candidate.is_absolute():
                continue
            if candidate.suffix.casefold() == ".exe":
                exe_candidates.append(candidate)
            elif candidate.suffix.casefold() in {".x86", ".x86_64"}:
                other_candidates.append(candidate)
            elif candidate.exists() and candidate.name.casefold() not in {"proton", "wine", "wine64", "python", "python3"}:
                other_candidates.append(candidate)
        candidates = exe_candidates + other_candidates
        exe_link = Path("/proc") / pid / "exe"
        try:
            candidates.append(Path(os.readlink(exe_link)))
        except OSError:
            pass

        selected: Optional[Path] = None
        for candidate in candidates:
            lowered = candidate.name.casefold()
            if lowered in _SKIP_PROCESSES or lowered.startswith("crash"):
                continue
            if _inside(candidate, roots) or (candidate.suffix.casefold() == ".exe" and
                    (env.get("STEAM_COMPAT_DATA_PATH") or env.get("WINEPREFIX"))):
                selected = candidate
                break
        if selected is None:
            continue

        matched = None
        for game in games:
            install = Path(str(game.get("install_path", "")))
            if install.exists() and _inside(selected, [install]):
                matched = game
                break
        title = matched.get("title") if matched else selected.stem
        platform = matched.get("platform") if matched else _platform_for_path(selected)
        game_id = matched.get("id") if matched else "process:" + str(selected.resolve())
        return {
            "id": game_id, "appid": (matched or {}).get("appid", ""),
            "title": title or comm, "platform": platform,
            "install_path": str((matched or {}).get("install_path", selected.parent)),
            "process_id": int(pid), "process_name": comm,
            "executable": str(selected), "session_key": game_id,
        }
    return None
