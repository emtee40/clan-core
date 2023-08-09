import argparse
import sys

from . import admin, secrets, ssh, zerotier
from .errors import ClanError

has_argcomplete = True
try:
    import argcomplete
except ImportError:
    has_argcomplete = False


# this will be the entrypoint under /bin/clan (see pyproject.toml config)
def main() -> None:
    parser = argparse.ArgumentParser(description="cLAN tool")
    subparsers = parser.add_subparsers()

    parser_admin = subparsers.add_parser("admin")
    admin.register_parser(parser_admin)

    # Currently broken
    # parser_config = subparsers.add_parser("config")
    # try:
    #    config.register_parser(parser_config)
    # except subprocess.CalledProcessError as e:
    #    warn(f"The config command does not work in the nix sandbox: {e}")

    parser_ssh = subparsers.add_parser("ssh", help="ssh to a remote machine")
    ssh.register_parser(parser_ssh)

    parser_secrets = subparsers.add_parser("secrets", help="manage secrets")
    secrets.register_parser(parser_secrets)

    parser_zerotier = subparsers.add_parser("zerotier", help="create zerotier network")
    zerotier.register_parser(parser_zerotier)

    if has_argcomplete:
        argcomplete.autocomplete(parser)

    if len(sys.argv) == 1:
        parser.print_help()

    args = parser.parse_args()
    if hasattr(args, "func"):
        try:
            args.func(args)
        except ClanError as e:
            print(f"{sys.argv[0]}: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
