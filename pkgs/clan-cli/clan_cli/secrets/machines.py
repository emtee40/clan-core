import argparse
from pathlib import Path

from ..completions import add_dynamic_completer, complete_machines, complete_secrets
from ..errors import ClanError
from ..git import commit_files
from ..machines.types import machine_name_type, validate_hostname
from . import secrets
from .folders import list_objects, remove_object, sops_machines_folder
from .secrets import update_secrets
from .sops import read_key, write_key
from .types import public_or_private_age_key_type, secret_name_type


def add_machine(flake_dir: Path, name: str, key: str, force: bool) -> None:
    path = sops_machines_folder(flake_dir) / name
    write_key(path, key, force)
    paths = [path]

    def filter_machine_secrets(secret: Path) -> bool:
        return secret.joinpath("machines", name).exists()

    paths.extend(update_secrets(flake_dir, filter_secrets=filter_machine_secrets))
    commit_files(
        paths,
        flake_dir,
        f"Add machine {name} to secrets",
    )


def remove_machine(flake_dir: Path, name: str) -> None:
    removed_paths = remove_object(sops_machines_folder(flake_dir), name)
    commit_files(
        removed_paths,
        flake_dir,
        f"Remove machine {name}",
    )


def get_machine(flake_dir: Path, name: str) -> str:
    return read_key(sops_machines_folder(flake_dir) / name)


def has_machine(flake_dir: Path, name: str) -> bool:
    return (sops_machines_folder(flake_dir) / name / "key.json").exists()


def list_machines(flake_dir: Path) -> list[str]:
    path = sops_machines_folder(flake_dir)

    def validate(name: str) -> bool:
        return validate_hostname(name) and has_machine(flake_dir, name)

    return list_objects(path, validate)


def add_secret(flake_dir: Path, machine: str, secret: str) -> None:
    paths = secrets.allow_member(
        secrets.machines_folder(flake_dir, secret),
        sops_machines_folder(flake_dir),
        machine,
    )
    commit_files(
        paths,
        flake_dir,
        f"Add {machine} to secret",
    )


def remove_secret(flake_dir: Path, machine: str, secret: str) -> None:
    updated_paths = secrets.disallow_member(
        secrets.machines_folder(flake_dir, secret), machine
    )
    commit_files(
        updated_paths,
        flake_dir,
        f"Remove {machine} from secret {secret}",
    )


def list_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    lst = list_machines(Path(args.flake))
    if len(lst) > 0:
        print("\n".join(lst))


def add_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    add_machine(Path(args.flake), args.machine, args.key, args.force)


def get_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    print(get_machine(Path(args.flake), args.machine))


def remove_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    remove_machine(Path(args.flake), args.machine)


def add_secret_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    add_secret(Path(args.flake), args.machine, args.secret)


def remove_secret_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    remove_secret(Path(args.flake), args.machine, args.secret)


def register_machines_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )
    # Parser
    list_parser = subparser.add_parser("list", help="list machines")
    list_parser.set_defaults(func=list_command)

    # Parser
    add_parser = subparser.add_parser("add", help="add a machine")
    add_parser.add_argument(
        "-f",
        "--force",
        help="overwrite existing machine",
        action="store_true",
        default=False,
    )
    add_machine_action = add_parser.add_argument(
        "machine", help="the name of the machine", type=machine_name_type
    )
    add_dynamic_completer(add_machine_action, complete_machines)
    add_parser.add_argument(
        "key",
        help="public key or private key of the user",
        type=public_or_private_age_key_type,
    )
    add_parser.set_defaults(func=add_command)

    # Parser
    get_parser = subparser.add_parser("get", help="get a machine public key")
    get_machine_parser = get_parser.add_argument(
        "machine", help="the name of the machine", type=machine_name_type
    )
    add_dynamic_completer(get_machine_parser, complete_machines)
    get_parser.set_defaults(func=get_command)

    # Parser
    remove_parser = subparser.add_parser("remove", help="remove a machine")
    remove_machine_parser = remove_parser.add_argument(
        "machine", help="the name of the machine", type=machine_name_type
    )
    add_dynamic_completer(remove_machine_parser, complete_machines)
    remove_parser.set_defaults(func=remove_command)

    # Parser
    add_secret_parser = subparser.add_parser(
        "add-secret", help="allow a machine to access a secret"
    )
    machine_add_secret_parser = add_secret_parser.add_argument(
        "machine", help="the name of the machine", type=machine_name_type
    )
    add_dynamic_completer(machine_add_secret_parser, complete_machines)
    add_secret_action = add_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_dynamic_completer(add_secret_action, complete_secrets)
    add_secret_parser.set_defaults(func=add_secret_command)

    # Parser
    remove_secret_parser = subparser.add_parser(
        "remove-secret", help="remove a group's access to a secret"
    )
    machine_remove_parser = remove_secret_parser.add_argument(
        "machine", help="the name of the machine", type=machine_name_type
    )
    add_dynamic_completer(machine_remove_parser, complete_machines)
    remove_secret_action = remove_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_dynamic_completer(remove_secret_action, complete_secrets)
    remove_secret_parser.set_defaults(func=remove_secret_command)
