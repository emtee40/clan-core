import subprocess
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from tests.age_keys import SopsSetup
from tests.fixtures_flakes import generate_flake
from tests.helpers import cli
from tests.helpers.nixos_config import nested_dict
from tests.root import CLAN_CORE

from clan_cli.clan_uri import FlakeId
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.vars.public_modules import in_repo
from clan_cli.vars.secret_modules import password_store, sops

from tests.helpers.vms import run_vm_in_thread, wait_vm_down, qga_connect, qmp_connect


def test_deployment(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    ssh_port = 54322
    config = nested_dict()
    config["clan"]["virtualisation"]["graphics"] = False
    config["services"]["getty"]["autologinUser"] = "root"
    config["services"]["openssh"]["enable"] = True
    config["networking"]["firewall"]["enable"] = False
    # TODO: fix bug that ignores the --target-host flag set below
    config["clan"]["networking"]["targetHost"] = "foo"
    config["users"]["users"]["root"]["openssh"]["authorizedKeys"]["keys"] = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDuhpzDHBPvn8nv8RH1MRomDOaXyP4GziQm7r3MZ1Syk grmpf"
    ]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = (
        "echo hello > $out/my_secret && echo hello > $out/my_value"
    )
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs=dict(my_machine=config),
    )
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    ssh_port = run_vm_in_thread("my_machine", ssh_port=ssh_port)
    print(f"ssh_port: {ssh_port}")
    qga = qga_connect("my_machine")
    # ensure secret does not yet exist
    qga.run("! ls /run/secrets/my_machine/my_generator/my_secret", check=True)
    # update machine
    cli.run(["machines", "update", "my_machine", "--target-host", f"root@localhost:{ssh_port}?StrictHostKeyChecking=no"])
    # ensure secret is deployed
    qga.run("ls /run/secrets/my_machine/my_generator/my_secret", check=True)
    qga.exec_cmd("poweroff")
    wait_vm_down("my_machine")
