import os
import subprocess
from pathlib import Path

from .errors import ClanError

from .dirs import flake_registry, unfree_nixpkgs


def nix_shell(packages: list[str], cmd: list[str]) -> list[str]:
    # we cannot use nix-shell inside the nix sandbox
    # in our tests we just make sure we have all the packages
    if os.environ.get("IN_NIX_SANDBOX"):
        return cmd
    wrapped_packages = [f"nixpkgs#{p}" for p in packages]
    return (
        [
            "nix",
            "shell",
            "--extra-experimental-features",
            "nix-command flakes",
            "--flake-registry",
            str(flake_registry()),
        ]
        + wrapped_packages
        + ["-c"]
        + cmd
    )


def unfree_nix_shell(packages: list[str], cmd: list[str]) -> list[str]:
    if os.environ.get("IN_NIX_SANDBOX"):
        return cmd
    return (
        [
            "nix",
            "shell",
            "--extra-experimental-features",
            "nix-command flakes",
            "-f",
            str(unfree_nixpkgs()),
        ]
        + packages
        + ["-c"]
        + cmd
    )


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
