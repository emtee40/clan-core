import argparse
import importlib
import json
import logging
import os
import shutil
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .cmd import Log, run
from .errors import ClanError
from .facts.secret_modules import SecretStoreBase
from .machines.machines import Machine
from .nix import nix_shell

log = logging.getLogger(__name__)


def list_available_ssh_keys(ssh_dir: Path = Path("~/.ssh").expanduser()) -> list[Path]:
    """
    Function to list all available SSH public keys in the default .ssh directory.
    Returns a list of paths to available public key files.
    """
    public_key_patterns = ["*.pub"]
    available_keys: list[Path] = []

    # Check for public key files
    for pattern in public_key_patterns:
        for key_path in ssh_dir.glob(pattern):
            if key_path.is_file():
                available_keys.append(key_path)

    return available_keys


def read_public_key_contents(public_keys: list[Path]) -> list[str]:
    """
    Function to read and return the contents of available SSH public keys.
    Returns a list containing the contents of each public key.
    """
    public_key_contents = []

    for key_path in public_keys:
        try:
            with open(key_path.expanduser()) as key_file:
                public_key_contents.append(key_file.read().strip())
        except FileNotFoundError:
            log.error(f"Public key file not found: {key_path}")

    return public_key_contents


def get_locale() -> tuple[str, str]:
    """
    Function to get the current default locale from the system.
    """
    default_locale = "en_US.UTF-8"
    keymap = "en"

    res = run(["locale", "lang_ab", "country_ab2", "charmap"])

    if res.returncode == 0:
        arr = res.stdout.strip().split("\n")
        default_locale = f"{arr[0]}_{arr[1]}.{arr[2]}"
        keymap = arr[0]

    return (keymap, default_locale)


def flash_machine(
    machine: Machine,
    *,
    mode: str,
    disks: dict[str, str],
    system_config: dict[str, Any],
    dry_run: bool,
    debug: bool,
) -> None:
    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    secret_facts_store: SecretStoreBase = secret_facts_module.SecretStore(
        machine=machine
    )
    with TemporaryDirectory() as tmpdir_:
        tmpdir = Path(tmpdir_)
        upload_dir = machine.secrets_upload_directory

        if upload_dir.startswith("/"):
            local_dir = tmpdir / upload_dir[1:]
        else:
            local_dir = tmpdir / upload_dir

        local_dir.mkdir(parents=True)
        secret_facts_store.upload(local_dir)
        disko_install = []

        if os.geteuid() != 0:
            if shutil.which("sudo") is None:
                raise ClanError(
                    "sudo is required to run disko-install as a non-root user"
                )
            disko_install.append("sudo")

        disko_install.append("disko-install")
        if dry_run:
            disko_install.append("--dry-run")
        if debug:
            disko_install.append("--debug")
        for name, device in disks.items():
            disko_install.extend(["--disk", name, device])

        disko_install.extend(["--extra-files", str(local_dir), upload_dir])
        disko_install.extend(["--flake", str(machine.flake) + "#" + machine.name])
        disko_install.extend(["--mode", str(mode)])
        disko_install.extend(
            [
                "--system-config",
                json.dumps(system_config),
            ]
        )

        cmd = nix_shell(
            ["/home/lhebendanz/Projects/disko"],
            disko_install,
        )
        run(cmd, log=Log.BOTH, error_msg=f"Failed to flash {machine}")


@dataclass
class FlashOptions:
    flake: Path
    machine: str
    disks: dict[str, str]
    ssh_keys_path: list[Path]
    dry_run: bool
    confirm: bool
    debug: bool
    mode: str
    language: str
    keymap: str


class AppendDiskAction(argparse.Action):
    def __init__(self, option_strings: str, dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        disks = getattr(namespace, self.dest)
        assert isinstance(values, list), "values must be a list"
        disks[values[0]] = values[1]


def flash_command(args: argparse.Namespace) -> None:
    opts = FlashOptions(
        flake=args.flake,
        machine=args.machine,
        disks=args.disk,
        ssh_keys_path=args.ssh_pubkey,
        dry_run=args.dry_run,
        confirm=not args.yes,
        debug=args.debug,
        mode=args.mode,
        language=args.lang,
        keymap=args.keymap,
    )

    machine = Machine(opts.machine, flake=opts.flake)
    if opts.confirm and not opts.dry_run:
        disk_str = ", ".join(f"{name}={device}" for name, device in opts.disks.items())
        msg = f"Install {machine.name}"
        if disk_str != "":
            msg += f" to {disk_str}"
        msg += "? [y/N] "
        ask = input(msg)
        if ask != "y":
            return

    root_keys = read_public_key_contents(opts.ssh_keys_path)
    if opts.confirm and not root_keys:
        msg = "Should we add your SSH public keys to the root user? [y/N] "
        ask = input(msg)
        if ask == "y":
            pubkeys = list_available_ssh_keys()
            root_keys.extend(read_public_key_contents(pubkeys))
    elif not opts.confirm and not root_keys:
        pubkeys = list_available_ssh_keys()
        root_keys.extend(read_public_key_contents(pubkeys))
    # If ssh-pubkeys set, we don't need to ask for confirmation
    elif opts.confirm and root_keys:
        pass
    elif not opts.confirm and root_keys:
        pass
    else:
        raise ClanError("Invalid state")

    console_keymap, default_locale = get_locale()
    extra_config = {
        "users": {
            "users": {"root": {"openssh": {"authorizedKeys": {"keys": root_keys}}}}
        },
        "console": {
            "keyMap": opts.keymap if opts.keymap else console_keymap,
        },
        "i18n": {
            "defaultLocale": opts.language if opts.language else default_locale,
        },
    }

    flash_machine(
        machine,
        mode=opts.mode,
        disks=opts.disks,
        system_config=extra_config,
        dry_run=opts.dry_run,
        debug=opts.debug,
    )


def register_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "machine",
        type=str,
        help="machine to install",
    )
    parser.add_argument(
        "--disk",
        type=str,
        nargs=2,
        metavar=("name", "value"),
        action=AppendDiskAction,
        help="device to flash to",
        default={},
    )
    mode_help = textwrap.dedent("""\
        Specify the mode of operation. Valid modes are: format, mount."
        Format will format the disk before installing.
        Mount will mount the disk before installing.
        Mount is useful for updating an existing system without losing data.
        """)
    parser.add_argument(
        "--mode",
        type=str,
        help=mode_help,
        choices=["format", "mount"],
        default="format",
    )
    parser.add_argument(
        "--ssh-pubkey",
        type=Path,
        action="append",
        default=[],
        help="ssh pubkey file to add to the root user. Can be used multiple times",
    )
    parser.add_argument(
        "--lang",
        type=str,
        help="system language",
    )
    parser.add_argument(
        "--keymap",
        type=str,
        help="system keymap",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="do not ask for confirmation",
        default=False,
    )
    parser.add_argument(
        "--dry-run",
        help="Only build the system, don't flash it",
        default=False,
        action="store_true",
    )
    parser.set_defaults(func=flash_command)
