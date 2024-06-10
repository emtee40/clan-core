import argparse
import getpass
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from .. import tty
from ..completions import (
    add_dynamic_completer,
    complete_groups,
    complete_machines,
    complete_secrets,
    complete_users,
)
from ..errors import ClanError
from ..git import commit_files
from .folders import (
    list_objects,
    sops_groups_folder,
    sops_machines_folder,
    sops_secrets_folder,
    sops_users_folder,
)
from .sops import decrypt_file, encrypt_file, ensure_sops_key, read_key, update_keys
from .types import VALID_SECRET_NAME, secret_name_type


def update_secrets(
    flake_dir: Path, filter_secrets: Callable[[Path], bool] = lambda _: True
) -> list[Path]:
    changed_files = []
    for name in list_secrets(flake_dir):
        secret_path = sops_secrets_folder(flake_dir) / name
        if not filter_secrets(secret_path):
            continue
        changed_files.extend(
            update_keys(
                secret_path,
                list(sorted(collect_keys_for_path(secret_path))),
            )
        )
    return changed_files


def collect_keys_for_type(folder: Path) -> set[str]:
    if not folder.exists():
        return set()
    keys = set()
    for p in folder.iterdir():
        if not p.is_symlink():
            continue
        try:
            target = p.resolve()
        except FileNotFoundError:
            tty.warn(f"Ignoring broken symlink {p}")
            continue
        kind = target.parent.name
        if folder.name != kind:
            tty.warn(f"Expected {p} to point to {folder} but points to {target.parent}")
            continue
        keys.add(read_key(target))
    return keys


def collect_keys_for_path(path: Path) -> set[str]:
    keys = set([])
    keys.update(collect_keys_for_type(path / "machines"))
    keys.update(collect_keys_for_type(path / "users"))
    groups = path / "groups"
    if not groups.is_dir():
        return keys
    for group in groups.iterdir():
        keys.update(collect_keys_for_type(group / "machines"))
        keys.update(collect_keys_for_type(group / "users"))
    return keys


def encrypt_secret(
    flake_dir: Path,
    secret: Path,
    value: IO[str] | str | bytes | None,
    add_users: list[str] = [],
    add_machines: list[str] = [],
    add_groups: list[str] = [],
) -> None:
    key = ensure_sops_key(flake_dir)
    keys = set([])

    files_to_commit = []
    for user in add_users:
        files_to_commit.extend(
            allow_member(
                users_folder(flake_dir, secret.name),
                sops_users_folder(flake_dir),
                user,
                False,
            )
        )

    for machine in add_machines:
        files_to_commit.extend(
            allow_member(
                machines_folder(flake_dir, secret.name),
                sops_machines_folder(flake_dir),
                machine,
                False,
            )
        )

    for group in add_groups:
        files_to_commit.extend(
            allow_member(
                groups_folder(flake_dir, secret.name),
                sops_groups_folder(flake_dir),
                group,
                False,
            )
        )

    keys = collect_keys_for_path(secret)

    if key.pubkey not in keys:
        keys.add(key.pubkey)
        files_to_commit.extend(
            allow_member(
                users_folder(flake_dir, secret.name),
                sops_users_folder(flake_dir),
                key.username,
                False,
            )
        )

    secret_path = secret / "secret"
    encrypt_file(secret_path, value, list(sorted(keys)))
    files_to_commit.append(secret_path)
    commit_files(
        files_to_commit,
        flake_dir,
        f"Update secret {secret.name}",
    )


def remove_secret(flake_dir: Path, secret: str) -> None:
    path = sops_secrets_folder(flake_dir) / secret
    if not path.exists():
        raise ClanError(f"Secret '{secret}' does not exist")
    shutil.rmtree(path)
    commit_files(
        [path],
        flake_dir,
        f"Remove secret {secret}",
    )


def remove_command(args: argparse.Namespace) -> None:
    remove_secret(Path(args.flake), args.secret)


def add_secret_argument(parser: argparse.ArgumentParser, autocomplete: bool) -> None:
    secrets_parser = parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    if autocomplete:
        add_dynamic_completer(secrets_parser, complete_secrets)


def machines_folder(flake_dir: Path, group: str) -> Path:
    return sops_secrets_folder(flake_dir) / group / "machines"


def users_folder(flake_dir: Path, group: str) -> Path:
    return sops_secrets_folder(flake_dir) / group / "users"


def groups_folder(flake_dir: Path, group: str) -> Path:
    return sops_secrets_folder(flake_dir) / group / "groups"


def list_directory(directory: Path) -> str:
    if not directory.exists():
        return f"{directory} does not exist"
    msg = f"\n{directory} contains:"
    for f in directory.iterdir():
        msg += f"\n  {f.name}"
    return msg


def allow_member(
    group_folder: Path, source_folder: Path, name: str, do_update_keys: bool = True
) -> list[Path]:
    source = source_folder / name
    if not source.exists():
        msg = f"Cannot encrypt {group_folder.parent.name} for '{name}' group. '{name}' group does not exist in {source_folder}: "
        msg += list_directory(source_folder)
        raise ClanError(msg)
    group_folder.mkdir(parents=True, exist_ok=True)
    user_target = group_folder / name
    if user_target.exists():
        if not user_target.is_symlink():
            raise ClanError(
                f"Cannot add user '{name}' to {group_folder.parent.name} secret. {user_target} exists but is not a symlink"
            )
        os.remove(user_target)

    user_target.symlink_to(os.path.relpath(source, user_target.parent))
    changed = [user_target]
    if do_update_keys:
        changed.extend(
            update_keys(
                group_folder.parent,
                list(sorted(collect_keys_for_path(group_folder.parent))),
            )
        )
    return changed


def disallow_member(group_folder: Path, name: str) -> list[Path]:
    target = group_folder / name
    if not target.exists():
        msg = f"{name} does not exist in group in {group_folder}: "
        msg += list_directory(group_folder)
        raise ClanError(msg)

    keys = collect_keys_for_path(group_folder.parent)

    if len(keys) < 2:
        raise ClanError(
            f"Cannot remove {name} from {group_folder.parent.name}. No keys left. Use 'clan secrets remove {name}' to remove the secret."
        )
    os.remove(target)

    if len(os.listdir(group_folder)) == 0:
        os.rmdir(group_folder)

    if len(os.listdir(group_folder.parent)) == 0:
        os.rmdir(group_folder.parent)

    return update_keys(
        target.parent.parent, list(sorted(collect_keys_for_path(group_folder.parent)))
    )


def has_secret(flake_dir: Path, secret: str) -> bool:
    return (sops_secrets_folder(flake_dir) / secret / "secret").exists()


def list_secrets(flake_dir: Path, pattern: str | None = None) -> list[str]:
    path = sops_secrets_folder(flake_dir)

    def validate(name: str) -> bool:
        return (
            VALID_SECRET_NAME.match(name) is not None
            and has_secret(flake_dir, name)
            and (pattern is None or pattern in name)
        )

    return list_objects(path, validate)


@dataclass
class ListSecretsOptions:
    flake: Path
    pattern: str | None


def list_command(args: argparse.Namespace) -> None:
    options = ListSecretsOptions(
        flake=args.flake,
        pattern=args.pattern,
    )
    lst = list_secrets(options.flake, options.pattern)
    if len(lst) > 0:
        print("\n".join(lst))


def decrypt_secret(flake_dir: Path, secret: str) -> str:
    ensure_sops_key(flake_dir)
    secret_path = sops_secrets_folder(flake_dir) / secret / "secret"
    if not secret_path.exists():
        raise ClanError(f"Secret '{secret}' does not exist")
    return decrypt_file(secret_path)


def get_command(args: argparse.Namespace) -> None:
    print(decrypt_secret(Path(args.flake), args.secret), end="")


def set_command(args: argparse.Namespace) -> None:
    env_value = os.environ.get("SOPS_NIX_SECRET")
    secret_value: str | IO[str] | None = sys.stdin
    if args.edit:
        secret_value = None
    elif env_value:
        secret_value = env_value
    elif tty.is_interactive():
        secret_value = getpass.getpass(prompt="Paste your secret: ")
    encrypt_secret(
        Path(args.flake),
        sops_secrets_folder(Path(args.flake)) / args.secret,
        secret_value,
        args.user,
        args.machine,
        args.group,
    )


def rename_command(args: argparse.Namespace) -> None:
    flake_dir = Path(args.flake)
    old_path = sops_secrets_folder(flake_dir) / args.secret
    new_path = sops_secrets_folder(flake_dir) / args.new_name
    if not old_path.exists():
        raise ClanError(f"Secret '{args.secret}' does not exist")
    if new_path.exists():
        raise ClanError(f"Secret '{args.new_name}' already exists")
    os.rename(old_path, new_path)
    commit_files(
        [old_path, new_path],
        flake_dir,
        f"Rename secret {args.secret} to {args.new_name}",
    )


def register_secrets_parser(subparser: argparse._SubParsersAction) -> None:
    parser_list = subparser.add_parser("list", help="list secrets")
    parser_list.add_argument(
        "pattern",
        nargs="?",
        help="a pattern to filter the secrets. All secrets containing the pattern will be listed.",
    )
    parser_list.set_defaults(func=list_command)

    parser_get = subparser.add_parser("get", help="get a secret")
    add_secret_argument(parser_get, True)
    parser_get.set_defaults(func=get_command)

    parser_set = subparser.add_parser("set", help="set a secret")
    add_secret_argument(parser_set, False)
    set_group_action = parser_set.add_argument(
        "--group",
        type=str,
        action="append",
        default=[],
        help="the group to import the secrets to (can be repeated)",
    )
    add_dynamic_completer(set_group_action, complete_groups)
    machine_parser = parser_set.add_argument(
        "--machine",
        type=str,
        action="append",
        default=[],
        help="the machine to import the secrets to (can be repeated)",
    )
    add_dynamic_completer(machine_parser, complete_machines)
    set_user_action = parser_set.add_argument(
        "--user",
        type=str,
        action="append",
        default=[],
        help="the user to import the secrets to (can be repeated)",
    )
    add_dynamic_completer(set_user_action, complete_users)
    parser_set.add_argument(
        "-e",
        "--edit",
        action="store_true",
        default=False,
        help="edit the secret with $EDITOR instead of pasting it",
    )
    parser_set.set_defaults(func=set_command)

    parser_rename = subparser.add_parser("rename", help="rename a secret")
    add_secret_argument(parser_rename, True)
    parser_rename.add_argument("new_name", type=str, help="the new name of the secret")
    parser_rename.set_defaults(func=rename_command)

    parser_remove = subparser.add_parser("remove", help="remove a secret")
    add_secret_argument(parser_remove, True)
    parser_remove.set_defaults(func=remove_command)
