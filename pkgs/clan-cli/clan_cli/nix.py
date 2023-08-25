import os
import subprocess
from pathlib import Path

from .errors import ClanError


def nix_shell(packages: list[str], cmd: list[str]) -> list[str]:
    flake = os.environ.get("CLAN_FLAKE")
    # in unittest we will have all binaries provided
    if flake is None:
        return cmd
    wrapped_packages = [f"path:{flake}#{p}" for p in packages]
    return ["nix", "shell"] + wrapped_packages + ["-c"] + cmd


def nix_build(package: str) -> Path:
    flake = os.environ.get("CLAN_FLAKE")
    if flake is None:
        package = os.environ.get("CLAN_PACKAGE_${package}", package)
        if package is None:
            raise ClanError("CLAN_PACKAGE_${package} is not set")
        return Path(package)
    proc = subprocess.run(
        ["nix", "build", "--print-out-paths", "--no-link", f"path:{flake}#{package}"],
        check=True,
        text=True,
        capture_output=True,
    )
    return Path(proc.stdout.strip())
