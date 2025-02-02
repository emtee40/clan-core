import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from clan_cli.api import API
from clan_cli.cmd import run_no_stdout
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.inventory import Machine, load_inventory_eval, save_inventory
from clan_cli.nix import nix_eval, nix_shell

log = logging.getLogger(__name__)


@API.register
def set_machine(flake_url: str | Path, machine_name: str, machine: Machine) -> None:
    inventory = load_inventory_eval(flake_url)

    inventory.machines[machine_name] = machine

    save_inventory(inventory, flake_url, "machines: edit '{machine_name}'")


@API.register
def list_inventory_machines(flake_url: str | Path) -> dict[str, Machine]:
    inventory = load_inventory_eval(flake_url)
    return inventory.machines


@dataclass
class MachineDetails:
    machine: Machine
    has_hw_specs: bool = False
    # TODO:
    # has_disk_specs: bool = False


@API.register
def get_inventory_machine_details(
    flake_url: str | Path, machine_name: str
) -> MachineDetails:
    inventory = load_inventory_eval(flake_url)
    machine = inventory.machines.get(machine_name)
    if machine is None:
        raise ClanError(f"Machine {machine_name} not found in inventory")

    hw_config_path = (
        Path(flake_url) / "machines" / Path(machine_name) / "hardware-configuration.nix"
    )

    return MachineDetails(
        machine=machine,
        has_hw_specs=hw_config_path.exists(),
    )


@API.register
def list_nixos_machines(flake_url: str | Path) -> list[str]:
    cmd = nix_eval(
        [
            f"{flake_url}#nixosConfigurations",
            "--apply",
            "builtins.attrNames",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)

    try:
        res = proc.stdout.strip()
        data = json.loads(res)
        return data
    except json.JSONDecodeError as e:
        raise ClanError(f"Error decoding machines from flake: {e}")


@dataclass
class ConnectionOptions:
    keyfile: str | None = None
    timeout: int = 2


@API.register
def check_machine_online(
    flake_url: str | Path, machine_name: str, opts: ConnectionOptions | None
) -> Literal["Online", "Offline"]:
    machine = load_inventory_eval(flake_url).machines.get(machine_name)
    if not machine:
        raise ClanError(f"Machine {machine_name} not found in inventory")

    hostname = machine.deploy.targetHost

    if not hostname:
        raise ClanError(f"Machine {machine_name} does not specify a targetHost")

    timeout = opts.timeout if opts and opts.timeout else 20

    cmd = nix_shell(
        ["nixpkgs#util-linux", *(["nixpkgs#openssh"] if hostname else [])],
        [
            "ssh",
            *(["-i", f"{opts.keyfile}"] if opts and opts.keyfile else []),
            # Disable strict host key checking
            "-o StrictHostKeyChecking=no",
            # Disable known hosts file
            "-o UserKnownHostsFile=/dev/null",
            f"-o ConnectTimeout={timeout}",
            f"{hostname}",
            "true",
            "&> /dev/null",
        ],
    )
    try:
        proc = run_no_stdout(cmd)
        if proc.returncode != 0:
            return "Offline"

        return "Online"
    except ClanCmdError:
        return "Offline"


def list_command(args: argparse.Namespace) -> None:
    flake_path = args.flake.path
    for name in list_nixos_machines(flake_path):
        print(name)


def register_list_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=list_command)
