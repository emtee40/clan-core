import argparse
import os
from pathlib import Path

from ..errors import ClanError
from . import secrets
from .folders import sops_groups_folder, sops_machines_folder, sops_users_folder
from .types import (
    VALID_USER_NAME,
    group_name_type,
    machine_name_type,
    secret_name_type,
    user_name_type,
    validate_hostname,
)


def machines_folder(group: str) -> Path:
    return sops_groups_folder() / group / "machines"


def users_folder(group: str) -> Path:
    return sops_groups_folder() / group / "users"


class Group:
    def __init__(self, name: str, machines: list[str], users: list[str]) -> None:
        self.name = name
        self.machines = machines
        self.users = users


def list_groups() -> list[Group]:
    groups = []
    folder = sops_groups_folder()
    if not folder.exists():
        return groups

    for name in os.listdir(folder):
        group_folder = folder / name
        if not group_folder.is_dir():
            continue
        machines_path = machines_folder(name)
        machines = []
        if machines_path.is_dir():
            for f in machines_path.iterdir():
                if validate_hostname(f.name):
                    machines.append(f.name)
        users_path = users_folder(name)
        users = []
        if users_path.is_dir():
            for f in users_path.iterdir():
                if VALID_USER_NAME.match(f.name):
                    users.append(f.name)
        groups.append(Group(name, machines, users))
    return groups


def list_command(args: argparse.Namespace) -> None:
    for group in list_groups():
        print(group.name)
        if group.machines:
            print("machines:")
            for machine in group.machines:
                print(f"  {machine}")
        if group.users:
            print("users:")
            for user in group.users:
                print(f"  {user}")
        print()


def list_directory(directory: Path) -> str:
    if not directory.exists():
        return "{directory} does not exist"
    msg = f"\n{directory} contains:"
    for f in directory.iterdir():
        msg += f"\n  {f.name}"
    return msg


def add_member(group_folder: Path, source_folder: Path, name: str) -> None:
    source = source_folder / name
    if not source.exists():
        msg = f"{name} does not exist in {source_folder}"
        msg += list_directory(source_folder)
        raise ClanError(msg)
    group_folder.mkdir(parents=True, exist_ok=True)
    user_target = group_folder / name
    if user_target.exists():
        if not user_target.is_symlink():
            raise ClanError(
                f"Cannot add user {name}. {user_target} exists but is not a symlink"
            )
        os.remove(user_target)
    user_target.symlink_to(os.path.relpath(source, user_target.parent))


def remove_member(group_folder: Path, name: str) -> None:
    target = group_folder / name
    if not target.exists():
        msg = f"{name} does not exist in group in {group_folder}"
        msg += list_directory(group_folder)
        raise ClanError(msg)
    os.remove(target)

    if len(os.listdir(group_folder)) == 0:
        os.rmdir(group_folder)

    if len(os.listdir(group_folder.parent)) == 0:
        os.rmdir(group_folder.parent)


def add_user_command(args: argparse.Namespace) -> None:
    add_member(users_folder(args.group), sops_users_folder(), args.user)


def remove_user_command(args: argparse.Namespace) -> None:
    remove_member(users_folder(args.group), args.user)


def add_machine_command(args: argparse.Namespace) -> None:
    add_member(
        machines_folder(args.group),
        sops_machines_folder(),
        args.machine,
    )


def remove_machine_command(args: argparse.Namespace) -> None:
    remove_member(machines_folder(args.group), args.machine)


def add_group_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("group", help="the name of the secret", type=group_name_type)


def add_secret_command(args: argparse.Namespace) -> None:
    secrets.allow_member(
        secrets.groups_folder(args.secret), sops_groups_folder(), args.group
    )


def remove_secret_command(args: argparse.Namespace) -> None:
    secrets.disallow_member(secrets.groups_folder(args.secret), args.group)


def register_groups_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )
    list_parser = subparser.add_parser("list", help="list groups")
    list_parser.set_defaults(func=list_command)

    add_machine_parser = subparser.add_parser(
        "add-machine", help="add a machine to group"
    )
    add_group_argument(add_machine_parser)
    add_machine_parser.add_argument(
        "machine", help="the name of the machines to add", type=machine_name_type
    )
    add_machine_parser.set_defaults(func=add_machine_command)

    remove_machine_parser = subparser.add_parser(
        "remove-machine", help="remove a machine from group"
    )
    add_group_argument(remove_machine_parser)
    remove_machine_parser.add_argument(
        "machine", help="the name of the machines to remove", type=machine_name_type
    )
    remove_machine_parser.set_defaults(func=remove_machine_command)

    add_user_parser = subparser.add_parser("add-user", help="add a user to group")
    add_group_argument(add_user_parser)
    add_user_parser.add_argument(
        "user", help="the name of the user to add", type=user_name_type
    )
    add_user_parser.set_defaults(func=add_user_command)

    remove_user_parser = subparser.add_parser(
        "remove-user", help="remove a user from group"
    )
    add_group_argument(remove_user_parser)
    remove_user_parser.add_argument(
        "user", help="the name of the user to remove", type=user_name_type
    )
    remove_user_parser.set_defaults(func=remove_user_command)

    add_secret_parser = subparser.add_parser(
        "add-secret", help="allow a user to access a secret"
    )
    add_secret_parser.add_argument(
        "group", help="the name of the user", type=group_name_type
    )
    add_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_secret_parser.set_defaults(func=add_secret_command)

    remove_secret_parser = subparser.add_parser(
        "remove-secret", help="remove a group's access to a secret"
    )
    remove_secret_parser.add_argument(
        "group", help="the name of the group", type=group_name_type
    )
    remove_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    remove_secret_parser.set_defaults(func=remove_secret_command)
