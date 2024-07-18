import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, ClassVar

from ..cmd import run, run_no_stdout
from ..dirs import nixpkgs_flake, nixpkgs_source


def nix_command(flags: list[str]) -> list[str]:
    return ["nix", "--extra-experimental-features", "nix-command flakes", *flags]


def nix_flake_show(flake_url: str | Path) -> list[str]:
    return nix_command(
        [
            "flake",
            "show",
            "--json",
            "--show-trace",
            "--no-write-lock-file",
            f"{flake_url}",
        ]
    )


def nix_build(flags: list[str], gcroot: Path | None = None) -> list[str]:
    if gcroot is not None:
        return (
            nix_command(
                [
                    "build",
                    "--out-link",
                    str(gcroot),
                    "--print-out-paths",
                    "--no-write-lock-file",
                ]
            )
            + flags
        )
    else:
        return (
            nix_command(
                [
                    "build",
                    "--no-link",
                    "--print-out-paths",
                    "--no-write-lock-file",
                ]
            )
            + flags
        )


def nix_add_to_gcroots(nix_path: Path, dest: Path) -> None:
    cmd = ["nix-store", "--realise", f"{nix_path}", "--add-root", f"{dest}"]
    run(cmd)


def nix_config() -> dict[str, Any]:
    cmd = nix_command(["show-config", "--json"])
    proc = run_no_stdout(cmd)
    data = json.loads(proc.stdout)
    config = {}
    for key, value in data.items():
        config[key] = value["value"]
    return config


def nix_eval(flags: list[str]) -> list[str]:
    default_flags = nix_command(
        [
            "eval",
            "--show-trace",
            "--json",
            "--no-write-lock-file",
        ]
    )
    if os.environ.get("IN_NIX_SANDBOX"):
        with tempfile.TemporaryDirectory() as nix_store:
            return [
                *default_flags,
                "--override-input",
                "nixpkgs",
                str(nixpkgs_source()),
                # --store is required to prevent this error:
                # error: cannot unlink '/nix/store/6xg259477c90a229xwmb53pdfkn6ig3g-default-builder.sh': Operation not permitted
                "--store",
                nix_store,
                *flags,
            ]
    return default_flags + flags


def nix_metadata(flake_url: str | Path) -> dict[str, Any]:
    cmd = nix_command(["flake", "metadata", "--json", f"{flake_url}"])
    proc = run(cmd)
    data = json.loads(proc.stdout)
    return data


def nix_shell(packages: list[str], cmd: list[str]) -> list[str]:
    # we cannot use nix-shell inside the nix sandbox
    # in our tests we just make sure we have all the packages
    if os.environ.get("IN_NIX_SANDBOX") or os.environ.get("CLAN_NO_DYNAMIC_DEPS"):
        return cmd
    return [
        *nix_command(["shell", "--inputs-from", f"{nixpkgs_flake()!s}"]),
        *packages,
        "-c",
        *cmd,
    ]


# Cache for requested dependencies
class Programs:
    _allowed_programs = None
    _clan_static_deps = None
    _cached_paths: ClassVar[dict[str, list[str]]] = {}
    _to_resolve: ClassVar[list[str]] = []

    @classmethod
    def add_program(cls: type["Programs"], flake_ref: str) -> None:
        if cls._allowed_programs is None:
            cls._allowed_programs = set(
                json.loads(
                    (Path(__file__).parent / "allowed-programs.json").read_text()
                )
            )
        if cls._clan_static_deps is None:
            cls._clan_static_deps = json.loads(os.environ.get("CLAN_STATIC_DEPS", "{}"))
        if flake_ref in cls._cached_paths:
            return
        if flake_ref.startswith("nixpkgs#"):
            name = flake_ref.split("#")[1]
            if name not in cls._allowed_programs:
                raise ValueError(
                    f"Program {name} is not allowed as it is not in the allowed-programs.json file."
                )
            if name in cls._clan_static_deps:
                cls._cached_paths[flake_ref] = [cls._clan_static_deps[name]]
                return
        cls._to_resolve.append(flake_ref)

    @classmethod
    # TODO: optimize via multiprocessing
    def resolve_all(cls: type["Programs"]) -> None:
        for flake_ref in cls._to_resolve:
            if flake_ref in cls._cached_paths:
                continue
            build = subprocess.run(
                nix_command(
                    [
                        "build",
                        "--inputs-from",
                        f"{nixpkgs_flake()!s}",
                        "--no-link",
                        "--print-out-paths",
                        flake_ref,
                    ]
                ),
                capture_output=True,
            )
            paths = build.stdout.decode().strip().splitlines()
            cls._cached_paths[flake_ref] = list(map(lambda path: path + "/bin", paths))
        cls._to_resolve = []

    @classmethod
    def bin_paths(cls: type["Programs"], names_or_refs: list[str]) -> list[str]:
        for name_or_ref in names_or_refs:
            cls.add_program(name_or_ref)
        cls.resolve_all()
        paths = []
        for name_or_ref in names_or_refs:
            paths.extend(cls._cached_paths[name_or_ref])
        return paths


def path_for_programs(packages: list[str]) -> str:
    bin_paths = Programs.bin_paths(packages)
    return ":".join(bin_paths)


def env_for_programs(packages: list[str]) -> dict[str, str]:
    return os.environ | {"PATH": path_for_programs(packages)}
