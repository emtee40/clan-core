import logging
import os
import sys
import urllib
from pathlib import Path

log = logging.getLogger(__name__)


def get_clan_flake_toplevel_or_env() -> Path | None:
    if clan_dir := os.environ.get("CLAN_DIR"):
        return Path(clan_dir)
    return get_clan_flake_toplevel()


def get_clan_flake_toplevel() -> Path | None:
    return find_toplevel([".clan-flake", ".git", ".hg", ".svn", "flake.nix"])


def find_git_repo_root() -> Path | None:
    return find_toplevel([".git"])


def clan_key_safe(flake_url: str) -> str:
    """
    only embed the url in the path, not the clan name, as it would involve eval.
    """
    quoted_url = urllib.parse.quote_plus(flake_url)
    return f"{quoted_url}"


def find_toplevel(top_level_files: list[str]) -> Path | None:
    """Returns the path to the toplevel of the clan flake"""
    for project_file in top_level_files:
        initial_path = Path(os.getcwd())
        path = Path(initial_path)
        while path.parent != path:
            if (path / project_file).exists():
                return path
            path = path.parent
    return None


def user_config_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA", os.path.expanduser("~\\AppData\\Roaming\\")))
    elif sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Application Support/"))
    else:
        return Path(os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config")))


def user_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(
            os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local\\"))
        )
    elif sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Application Support/"))
    else:
        return Path(os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share")))


def user_cache_dir() -> Path:
    if sys.platform == "win32":
        return Path(
            os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local\\"))
        )
    elif sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Caches/"))
    else:
        return Path(os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache")))


def user_gcroot_dir() -> Path:
    p = user_config_dir() / "clan" / "gcroots"
    p.mkdir(parents=True, exist_ok=True)
    return p


def machine_gcroot(flake_url: str) -> Path:
    # Always build icon so that we can symlink it to the gcroot
    gcroot_dir = user_gcroot_dir()
    clan_gcroot = gcroot_dir / clan_key_safe(flake_url)
    clan_gcroot.mkdir(parents=True, exist_ok=True)
    return clan_gcroot


def user_history_file() -> Path:
    return user_config_dir() / "clan" / "history"


def vm_state_dir(flake_url: str, vm_name: str) -> Path:
    clan_key = clan_key_safe(flake_url)
    return user_data_dir() / "clan" / "vmstate" / clan_key / vm_name


def machines_dir(flake_dir: Path) -> Path:
    return flake_dir / "machines"


def specific_machine_dir(flake_dir: Path, machine: str) -> Path:
    return machines_dir(flake_dir) / machine


def module_root() -> Path:
    return Path(__file__).parent


def nixpkgs_flake() -> Path:
    return (module_root() / "nixpkgs").resolve()


def nixpkgs_source() -> Path:
    return (module_root() / "nixpkgs" / "path").resolve()
