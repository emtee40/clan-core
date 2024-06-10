import fileinput
import json
import logging
import os
import shutil
import subprocess as sp
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from root import CLAN_CORE

from clan_cli.dirs import nixpkgs_source

log = logging.getLogger(__name__)


# substitutes string sin a file.
# This can be used on the flake.nix or default.nix of a machine
def substitute(
    file: Path,
    clan_core_flake: Path | None = None,
    flake: Path = Path(__file__).parent,
) -> None:
    sops_key = str(flake.joinpath("sops.key"))
    for line in fileinput.input(file, inplace=True):
        line = line.replace("__NIXPKGS__", str(nixpkgs_source()))
        if clan_core_flake:
            line = line.replace("__CLAN_CORE__", str(clan_core_flake))
            line = line.replace(
                "git+https://git.clan.lol/clan/clan-core", str(clan_core_flake)
            )
        line = line.replace("__CLAN_SOPS_KEY_PATH__", sops_key)
        line = line.replace("__CLAN_SOPS_KEY_DIR__", str(flake))
        print(line, end="")


class FlakeForTest(NamedTuple):
    path: Path


def generate_flake(
    temporary_home: Path,
    flake_template: Path,
    substitutions: dict[str, str] = {
        "__CHANGE_ME__": "_test_vm_persistence",
        "git+https://git.clan.lol/clan/clan-core": "path://" + str(CLAN_CORE),
    },
    # define the machines directly including their config
    machine_configs: dict[str, dict] = {},
) -> FlakeForTest:
    """
    Creates a clan flake with the given name.
    Machines are fully generated from the machine_configs.

    Example:
        machine_configs = dict(
            my_machine=dict(
                clanCore=dict(
                    backups=dict(
                        ...
                    )
                )
            )
        )
    """

    # copy the template to a new temporary location
    flake = temporary_home / "flake"
    shutil.copytree(flake_template, flake)
    sp.run(["chmod", "+w", "-R", str(flake)], check=True)

    # substitute `substitutions` in all files of the template
    for file in flake.rglob("*"):
        if file.is_file():
            print(f"Final Content of {file}:")
            for line in fileinput.input(file, inplace=True):
                for key, value in substitutions.items():
                    line = line.replace(key, value)
                print(line, end="")

    # generate machines from machineConfigs
    for machine_name, machine_config in machine_configs.items():
        settings_path = flake / "machines" / machine_name / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(machine_config, indent=2))

    if "/tmp" not in str(os.environ.get("HOME")):
        log.warning(
            f"!! $HOME does not point to a temp directory!! HOME={os.environ['HOME']}"
        )

    # TODO: Find out why test_vms_api.py fails in nix build
    # but works in pytest when this bottom line is commented out
    sp.run(
        ["git", "config", "--global", "init.defaultBranch", "main"],
        cwd=flake,
        check=True,
    )
    sp.run(["git", "init"], cwd=flake, check=True)
    sp.run(["git", "add", "."], cwd=flake, check=True)
    sp.run(["git", "config", "user.name", "clan-tool"], cwd=flake, check=True)
    sp.run(["git", "config", "user.email", "clan@example.com"], cwd=flake, check=True)
    sp.run(["git", "commit", "-a", "-m", "Initial commit"], cwd=flake, check=True)

    return FlakeForTest(flake)


def create_flake(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    flake_template: str | Path,
    clan_core_flake: Path | None = None,
    # names referring to pre-defined machines from ../machines
    machines: list[str] = [],
    # alternatively specify the machines directly including their config
    machine_configs: dict[str, dict] = {},
    remote: bool = False,
) -> Iterator[FlakeForTest]:
    """
    Creates a flake with the given name and machines.
    The machine names map to the machines in ./test_machines
    """
    if isinstance(flake_template, Path):
        template_path = flake_template
    else:
        template_path = Path(__file__).parent / flake_template

    flake_template_name = template_path.name

    # copy the template to a new temporary location
    flake = temporary_home / flake_template_name
    shutil.copytree(template_path, flake)
    sp.run(["chmod", "+w", "-R", str(flake)], check=True)

    # add the requested machines to the flake
    if machines:
        (flake / "machines").mkdir(parents=True, exist_ok=True)
    for machine_name in machines:
        machine_path = Path(__file__).parent / "machines" / machine_name
        shutil.copytree(machine_path, flake / "machines" / machine_name)
        substitute(flake / "machines" / machine_name / "default.nix", flake)

    # generate machines from machineConfigs
    for machine_name, machine_config in machine_configs.items():
        settings_path = flake / "machines" / machine_name / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(machine_config, indent=2))

    # in the flake.nix file replace the string __CLAN_URL__ with the the clan flake
    # provided by get_test_flake_toplevel
    flake_nix = flake / "flake.nix"
    # this is where we would install the sops key to, when updating
    substitute(flake_nix, clan_core_flake, flake)

    if "/tmp" not in str(os.environ.get("HOME")):
        log.warning(
            f"!! $HOME does not point to a temp directory!! HOME={os.environ['HOME']}"
        )

    # TODO: Find out why test_vms_api.py fails in nix build
    # but works in pytest when this bottom line is commented out
    sp.run(
        ["git", "config", "--global", "init.defaultBranch", "main"],
        cwd=flake,
        check=True,
    )
    sp.run(["git", "init"], cwd=flake, check=True)
    sp.run(["git", "add", "."], cwd=flake, check=True)
    sp.run(["git", "config", "user.name", "clan-tool"], cwd=flake, check=True)
    sp.run(["git", "config", "user.email", "clan@example.com"], cwd=flake, check=True)
    sp.run(["git", "commit", "-a", "-m", "Initial commit"], cwd=flake, check=True)

    if remote:
        with tempfile.TemporaryDirectory():
            yield FlakeForTest(flake)
    else:
        yield FlakeForTest(flake)


@pytest.fixture
def test_flake(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    yield from create_flake(monkeypatch, temporary_home, "test_flake")
    # check that git diff on ./sops is empty
    if (temporary_home / "test_flake" / "sops").exists():
        git_proc = sp.run(
            ["git", "diff", "--exit-code", "./sops"],
            cwd=temporary_home / "test_flake",
            stderr=sp.PIPE,
        )
        if git_proc.returncode != 0:
            log.error(git_proc.stderr.decode())
            raise Exception(
                "git diff on ./sops is not empty. This should not happen as all changes should be committed"
            )


@pytest.fixture
def test_flake_with_core(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    if not (CLAN_CORE / "flake.nix").exists():
        raise Exception(
            "clan-core flake not found. This test requires the clan-core flake to be present"
        )
    yield from create_flake(
        monkeypatch,
        temporary_home,
        "test_flake_with_core",
        CLAN_CORE,
    )


@pytest.fixture
def test_local_democlan(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    democlan = os.getenv(key="DEMOCLAN_ROOT")
    if democlan is None:
        raise Exception(
            "DEMOCLAN_ROOT not set. This test requires the democlan flake to be present"
        )
    democlan_p = Path(democlan).resolve()
    if not democlan_p.is_dir():
        raise Exception(
            f"DEMOCLAN_ROOT ({democlan_p}) is not a directory. This test requires the democlan directory to be present"
        )

    yield FlakeForTest(democlan_p)


@pytest.fixture
def test_flake_with_core_and_pass(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    if not (CLAN_CORE / "flake.nix").exists():
        raise Exception(
            "clan-core flake not found. This test requires the clan-core flake to be present"
        )
    yield from create_flake(
        monkeypatch,
        temporary_home,
        "test_flake_with_core_and_pass",
        CLAN_CORE,
    )


@pytest.fixture
def test_flake_minimal(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    if not (CLAN_CORE / "flake.nix").exists():
        raise Exception(
            "clan-core flake not found. This test requires the clan-core flake to be present"
        )
    yield from create_flake(
        monkeypatch,
        temporary_home,
        CLAN_CORE / "templates" / "minimal",
        CLAN_CORE,
    )
