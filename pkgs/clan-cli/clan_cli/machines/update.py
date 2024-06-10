import argparse
import json
import logging
import os
import shlex
import sys

from ..cmd import run
from ..completions import add_dynamic_completer, complete_machines
from ..errors import ClanError
from ..facts.generate import generate_facts
from ..facts.upload import upload_secrets
from ..machines.machines import Machine
from ..nix import nix_command, nix_metadata
from ..ssh import HostKeyCheck
from .inventory import get_all_machines, get_selected_machines
from .machine_group import MachineGroup

log = logging.getLogger(__name__)


def is_path_input(node: dict[str, dict[str, str]]) -> bool:
    locked = node.get("locked")
    if not locked:
        return False
    return locked["type"] == "path" or locked.get("url", "").startswith("file://")


def upload_sources(
    flake_url: str, remote_url: str, always_upload_source: bool = False
) -> str:
    if not always_upload_source:
        flake_data = nix_metadata(flake_url)
        url = flake_data["resolvedUrl"]
        has_path_inputs = any(
            is_path_input(node) for node in flake_data["locks"]["nodes"].values()
        )
        if not has_path_inputs and not is_path_input(flake_data):
            # No need to upload sources, we can just build the flake url directly
            # FIXME: this might fail for private repositories?
            return url
        if not has_path_inputs:
            # Just copy the flake to the remote machine, we can substitute other inputs there.
            path = flake_data["path"]
            env = os.environ.copy()
            # env["NIX_SSHOPTS"] = " ".join(opts.remote_ssh_options)
            assert remote_url
            cmd = nix_command(
                [
                    "copy",
                    "--to",
                    f"ssh://{remote_url}",
                    "--no-check-sigs",
                    path,
                ]
            )
            run(cmd, env=env, error_msg="failed to upload sources")
            return path

    # Slow path: we need to upload all sources to the remote machine
    assert remote_url
    cmd = nix_command(
        [
            "flake",
            "archive",
            "--to",
            f"ssh://{remote_url}",
            "--json",
            flake_url,
        ]
    )
    log.info("run %s", shlex.join(cmd))
    proc = run(cmd, error_msg="failed to upload sources")

    try:
        return json.loads(proc.stdout)["path"]
    except (json.JSONDecodeError, OSError) as e:
        raise ClanError(
            f"failed to parse output of {shlex.join(cmd)}: {e}\nGot: {proc.stdout}"
        )


def deploy_nixos(machines: MachineGroup) -> None:
    """
    Deploy to all hosts in parallel
    """

    def deploy(machine: Machine) -> None:
        host = machine.build_host
        target = f"{host.user or 'root'}@{host.host}"
        ssh_arg = f"-p {host.port}" if host.port else ""
        env = os.environ.copy()
        env["NIX_SSHOPTS"] = ssh_arg

        generate_facts([machine], None, False)
        upload_secrets(machine)

        path = upload_sources(".", target)

        if host.host_key_check != HostKeyCheck.STRICT:
            ssh_arg += " -o StrictHostKeyChecking=no"
        if host.host_key_check == HostKeyCheck.NONE:
            ssh_arg += " -o UserKnownHostsFile=/dev/null"

        ssh_arg += " -i " + host.key if host.key else ""

        cmd = [
            "nixos-rebuild",
            "switch",
            "--fast",
            "--option",
            "keep-going",
            "true",
            "--option",
            "accept-flake-config",
            "true",
            "--build-host",
            "",
            *machine.nix_options,
            "--flake",
            f"{path}#{machine.name}",
        ]
        if target_host := host.meta.get("target_host"):
            target_host = f"{target_host.user or 'root'}@{target_host.host}"
            cmd.extend(["--target-host", target_host])
        ret = host.run(cmd, check=False)
        # re-retry switch if the first time fails
        if ret.returncode != 0:
            ret = host.run(cmd)

    machines.run_function(deploy)


def update(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    machines = []
    if len(args.machines) == 1 and args.target_host is not None:
        machine = Machine(
            name=args.machines[0], flake=args.flake, nix_options=args.option
        )
        machine.target_host_address = args.target_host
        machines.append(machine)

    elif args.target_host is not None:
        print("target host can only be specified for a single machine")
        exit(1)
    else:
        if len(args.machines) == 0:
            ignored_machines = []
            for machine in get_all_machines(args.flake, args.option):
                if machine.deployment_info.get("requireExplicitUpdate", False):
                    continue
                try:
                    machine.build_host
                except ClanError:  # check if we have a build host set
                    ignored_machines.append(machine)
                    continue

                machines.append(machine)

            if not machines and ignored_machines != []:
                print(
                    "WARNING: No machines to update. The following defined machines were ignored because they do not have `clan.networking.targetHost` nixos option set:",
                    file=sys.stderr,
                )
                for machine in ignored_machines:
                    print(machine, file=sys.stderr)

        else:
            machines = get_selected_machines(args.flake, args.option, args.machines)

    deploy_nixos(MachineGroup(machines))


def register_update_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machines",
        type=str,
        nargs="*",
        default=[],
        metavar="MACHINE",
        help="machine to update. If no machine is specified, all machines will be updated.",
    )

    add_dynamic_completer(machines_parser, complete_machines)

    parser.add_argument(
        "--target-host",
        type=str,
        help="address of the machine to update, in the format of user@host:1234",
    )
    parser.set_defaults(func=update)
