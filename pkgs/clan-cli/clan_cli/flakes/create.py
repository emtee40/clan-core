# !/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Dict

from pydantic import AnyUrl
from pydantic.tools import parse_obj_as

from ..async_cmd import CmdOut, run, runforcli
from ..dirs import clan_flakes_dir
from ..nix import nix_command, nix_shell

DEFAULT_URL: AnyUrl = parse_obj_as(
    AnyUrl, "git+https://git.clan.lol/clan/clan-core#new-clan"
)


async def create_flake(directory: Path, url: AnyUrl) -> Dict[str, CmdOut]:
    if not directory.exists():
        directory.mkdir()
    response = {}
    command = nix_command(
        [
            "flake",
            "init",
            "-t",
            url,
        ]
    )
    out = await run(command, directory)
    response["flake init"] = out

    command = nix_shell(["git"], ["git", "init"])
    out = await run(command, directory)
    response["git init"] = out

    command = nix_shell(["git"], ["git", "add", "."])
    out = await run(command, directory)
    response["git add"] = out

    command = nix_shell(["git"], ["git", "config", "user.name", "clan-tool"])
    out = await run(command, directory)
    response["git config"] = out

    command = nix_shell(["git"], ["git", "config", "user.email", "clan@example.com"])
    out = await run(command, directory)
    response["git config"] = out

    command = nix_shell(["git"], ["git", "commit", "-a", "-m", "Initial commit"])
    out = await run(command, directory)
    response["git commit"] = out

    return response


def create_flake_command(args: argparse.Namespace) -> None:
    flake_dir = clan_flakes_dir() / args.name
    runforcli(create_flake, flake_dir, args.url)


# takes a (sub)parser and configures it
def register_create_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "name",
        type=str,
        help="name for the flake",
    )
    parser.add_argument(
        "--url",
        type=AnyUrl,
        help="url for the flake",
        default=DEFAULT_URL,
    )
    # parser.add_argument("name", type=str, help="name of the flake")
    parser.set_defaults(func=create_flake_command)
