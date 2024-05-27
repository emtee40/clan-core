import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from . import (
    backups,
    config,
    facts,
    flakes,
    flash,
    flatpak,
    history,
    machines,
    secrets,
    vms,
)
from .custom_logger import setup_logging
from .dirs import get_clan_flake_toplevel_or_env
from .errors import ClanCmdError, ClanError
from .profiler import profile
from .ssh import cli as ssh_cli

log = logging.getLogger(__name__)

argcomplete: ModuleType | None = None
try:
    import argcomplete  # type: ignore[no-redef]
except ImportError:
    pass


class AppendOptionAction(argparse.Action):
    def __init__(self, option_strings: str, dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        lst = getattr(namespace, self.dest)
        lst.append("--option")
        assert isinstance(values, list), "values must be a list"
        lst.append(values[0])
        lst.append(values[1])


def create_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="cLAN tool",
        epilog=(
            """
For more detailed information, visit: https://docs.clan.lol
        """
        ),
    )

    parser.add_argument(
        "--debug",
        help="Enable debug logging",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--option",
        help="Nix option to set",
        nargs=2,
        metavar=("name", "value"),
        action=AppendOptionAction,
        default=[],
    )

    def flake_path(arg: str) -> str | Path:
        flake_dir = Path(arg).resolve()
        if flake_dir.exists() and flake_dir.is_dir():
            return flake_dir
        return arg

    parser.add_argument(
        "--flake",
        help="path to the flake where the clan resides in, can be a remote flake or local, can be set through the [CLAN_DIR] environment variable",
        default=get_clan_flake_toplevel_or_env(),
        metavar="PATH",
        type=flake_path,
    )

    subparsers = parser.add_subparsers()

    parser_backups = subparsers.add_parser(
        "backups",
        help="manage backups of clan machines",
        description="manage backups of clan machines",
        epilog=(
            """
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    backups.register_parser(parser_backups)

    parser_flake = subparsers.add_parser(
        "flakes",
        help="create a clan flake inside the current directory",
        epilog=(
            """
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    flakes.register_parser(parser_flake)

    parser_config = subparsers.add_parser(
        "config",
        help="set nixos configuration",
        epilog=(
            """
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    config.register_parser(parser_config)

    parser_ssh = subparsers.add_parser("ssh", help="ssh to a remote machine")
    ssh_cli.register_parser(parser_ssh)

    parser_secrets = subparsers.add_parser(
        "secrets",
        help="manage secrets",
        epilog=(
            """
This subcommand provides an interface to secret facts.

Examples:

  $ clan secrets list [regex]
  Will list secrets for all managed machines.
  It accepts an optional regex, allowing easy filtering of returned secrets.

  $ clan secrets get [SECRET]
  Will display the content of the specified secret.

For more detailed information, visit: https://docs.clan.lol/getting-started/secrets/
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    secrets.register_parser(parser_secrets)

    parser_facts = subparsers.add_parser(
        "facts",
        help="manage facts",
        epilog=(
            """

This subcommand provides an interface to facts of clan machines.
Facts are artifacts that a service can generate.
There are public and secret facts. 
Public facts can be referenced by other machines directly.
Public facts can include: ip addresses, public keys.
Secret facts can include: passwords, private keys.

A service is an included clan-module that implements facts generation functionality.
For example the zerotier module will generate private and public facts.
In this case the public fact will be the resulting zerotier-ip of the machine.
The secret fact will be the zerotier-identity-secret, which is used by zerotier
to prove the machine has control of the zerotier-ip.

Examples:

  $ clan facts generate
  Will generate facts for all machines.
   
  $ clan facts generate --service [SERVICE] --regenerate
  Will regenerate facts, if they are already generated for a specific service.
  This is especially useful for resetting certain passwords while leaving the rest
  of the facts for a machine in place.

For more detailed information, visit: https://docs.clan.lol/getting-started/secrets/
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    facts.register_parser(parser_facts)

    parser_machine = subparsers.add_parser(
        "machines", help="manage machines and their configuration"
    )
    machines.register_parser(parser_machine)

    parser_vms = subparsers.add_parser("vms", help="manage virtual machines")
    vms.register_parser(parser_vms)

    parser_history = subparsers.add_parser("history", help="manage history")
    history.register_parser(parser_history)

    parser_flash = subparsers.add_parser(
        "flash", help="flash machines to usb sticks or into isos"
    )
    flash.register_parser(parser_flash)

    if argcomplete:
        argcomplete.autocomplete(parser)

    return parser


# this will be the entrypoint under /bin/clan (see pyproject.toml config)
@profile
def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()

    if args.debug:
        setup_logging(logging.DEBUG, root_log_name=__name__.split(".")[0])
        log.debug("Debug log activated")
        if flatpak.is_flatpak():
            log.debug("Running inside a flatpak sandbox")
    else:
        setup_logging(logging.INFO, root_log_name=__name__.split(".")[0])

    if not hasattr(args, "func"):
        return

    try:
        args.func(args)
    except ClanError as e:
        if args.debug:
            log.exception(e)
            sys.exit(1)
        if isinstance(e, ClanCmdError):
            if e.cmd.msg:
                log.error(e.cmd.msg)
                sys.exit(1)

        log.error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
