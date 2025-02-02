import argparse
import dataclasses
import json
import logging
from pathlib import Path

from clan_cli.api import API
from clan_cli.clan_uri import FlakeId
from clan_cli.errors import ClanError
from clan_cli.git import commit_file

from ..cmd import run, run_no_stdout
from ..completions import add_dynamic_completer, complete_machines
from ..machines.machines import Machine
from ..nix import nix_config, nix_eval, nix_shell
from .types import machine_name_type

log = logging.getLogger(__name__)


@dataclasses.dataclass
class HardwareInfo:
    system: str | None


@API.register
def show_machine_hardware_info(
    clan_dir: str | Path, machine_name: str
) -> HardwareInfo | None:
    """
    Show hardware information for a machine returns None if none exist.
    """

    hw_file = Path(f"{clan_dir}/machines/{machine_name}/hardware-configuration.nix")

    is_template = hw_file.exists() and "throw" in hw_file.read_text()
    if not hw_file.exists() or is_template:
        return None

    system = show_machine_hardware_platform(clan_dir, machine_name)
    return HardwareInfo(system)


@API.register
def show_machine_deployment_target(
    clan_dir: str | Path, machine_name: str
) -> str | None:
    """
    Show hardware information for a machine returns None if none exist.
    """
    config = nix_config()
    system = config["system"]
    cmd = nix_eval(
        [
            f"{clan_dir}#clanInternals.machines.{system}.{machine_name}",
            "--apply",
            "machine: { inherit (machine.config.clan.core.networking) targetHost; }",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)
    res = proc.stdout.strip()

    target_host = json.loads(res)
    return target_host.get("targetHost", None)


@API.register
def show_machine_hardware_platform(
    clan_dir: str | Path, machine_name: str
) -> str | None:
    """
    Show hardware information for a machine returns None if none exist.
    """
    config = nix_config()
    system = config["system"]
    cmd = nix_eval(
        [
            f"{clan_dir}#clanInternals.machines.{system}.{machine_name}",
            "--apply",
            "machine: { inherit (machine.config.nixpkgs.hostPlatform) system; }",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)
    res = proc.stdout.strip()

    host_platform = json.loads(res)
    return host_platform.get("system", None)


@API.register
def generate_machine_hardware_info(
    clan_dir: FlakeId,
    machine_name: str,
    hostname: str | None = None,
    password: str | None = None,
    keyfile: str | None = None,
    force: bool | None = False,
) -> HardwareInfo:
    """
    Generate hardware information for a machine
    and place the resulting *.nix file in the machine's directory.
    """

    machine = Machine(machine_name, flake=clan_dir)
    if hostname is not None:
        machine.target_host_address = hostname

    host = machine.target_host
    target_host = f"{host.user or 'root'}@{host.host}"
    cmd = nix_shell(
        [
            "nixpkgs#openssh",
            "nixpkgs#sshpass",
            # Provides nixos-generate-config on non-NixOS systems
            "nixpkgs#nixos-install-tools",
        ],
        [
            *(["sshpass", "-p", f"{password}"] if password else []),
            "ssh",
            *(["-i", f"{keyfile}"] if keyfile else []),
            # Disable known hosts file
            "-o",
            "UserKnownHostsFile=/dev/null",
            # Disable strict host key checking. The GUI user cannot type "yes" into the ssh terminal.
            "-o",
            "StrictHostKeyChecking=no",
            *(
                ["-p", str(machine.target_host.port)]
                if machine.target_host.port
                else []
            ),
            target_host,
            "nixos-generate-config",
            # Filesystems are managed by disko
            "--no-filesystems",
            "--show-hardware-config",
        ],
    )
    out = run(cmd)
    if out.returncode != 0:
        log.error(f"Failed to inspect {machine_name}. Address: {hostname}")
        log.error(out)
        raise ClanError(f"Failed to inspect {machine_name}. Address: {hostname}")

    hw_file = Path(f"{clan_dir}/machines/{machine_name}/hardware-configuration.nix")
    hw_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if the hardware-configuration.nix file is a template
    is_template = hw_file.exists() and "throw" in hw_file.read_text()

    if hw_file.exists() and not force and not is_template:
        raise ClanError(
            "File exists.",
            description="Hardware file already exists. To force overwrite the existing configuration use '--force'.",
            location=f"{__name__} {hw_file}",
        )

    with open(hw_file, "w") as f:
        f.write(out.stdout)
        print(f"Successfully generated: {hw_file}")

    system = show_machine_hardware_platform(clan_dir, machine_name)

    commit_file(
        hw_file, clan_dir.path, f"Generate hardware configuration for {machine_name}"
    )

    return HardwareInfo(system)


def hw_generate_command(args: argparse.Namespace) -> None:
    hw_info = generate_machine_hardware_info(
        args.flake, args.machine, args.hostname, args.password, args.force
    )
    print("----")
    print("Successfully generated hardware information.")
    print(f"Target: {args.machine} ({args.hostname})")
    print(f"System: {hw_info.system}")
    print("----")


def register_hw_generate(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=hw_generate_command)
    machine_parser = parser.add_argument(
        "machine",
        help="the name of the machine",
        type=machine_name_type,
    )
    machine_parser = parser.add_argument(
        "target_host",
        type=str,
        nargs="?",
        help="ssh address to install to in the form of user@host:2222",
    )
    machine_parser = parser.add_argument(
        "--password",
        help="Pre-provided password the cli will prompt otherwise if needed.",
        type=str,
        required=False,
    )
    machine_parser = parser.add_argument(
        "--force",
        help="Will overwrite the hardware-configuration.nix file.",
        action="store_true",
    )
    add_dynamic_completer(machine_parser, complete_machines)
