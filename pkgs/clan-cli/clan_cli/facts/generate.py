import argparse
import importlib
import logging
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import run

from ..completions import (
    add_dynamic_completer,
    complete_machines,
    complete_services_for_machine,
)
from ..errors import ClanError
from ..git import commit_files
from ..machines.inventory import get_all_machines, get_selected_machines
from ..machines.machines import Machine
from ..nix import nix_shell
from .check import check_secrets
from .public_modules import FactStoreBase
from .secret_modules import SecretStoreBase

log = logging.getLogger(__name__)


def read_multiline_input(prompt: str = "Finish with Ctrl-D") -> str:
    """
    Read multi-line input from stdin.
    """
    print(prompt, flush=True)
    proc = subprocess.run(["cat"], stdout=subprocess.PIPE, text=True)
    log.info("Input received. Processing...")
    return proc.stdout


def generate_service_facts(
    machine: Machine,
    service: str,
    regenerate: bool,
    secret_facts_store: SecretStoreBase,
    public_facts_store: FactStoreBase,
    tmpdir: Path,
    prompt: Callable[[str], str],
) -> bool:
    service_dir = tmpdir / service
    # check if all secrets exist and generate them if at least one is missing
    needs_regeneration = not check_secrets(machine, service=service)
    log.debug(f"{service} needs_regeneration: {needs_regeneration}")
    if not (needs_regeneration or regenerate):
        return False
    if not isinstance(machine.flake, Path):
        msg = f"flake is not a Path: {machine.flake}"
        msg += "fact/secret generation is only supported for local flakes"

    env = os.environ.copy()
    facts_dir = service_dir / "facts"
    facts_dir.mkdir(parents=True)
    env["facts"] = str(facts_dir)
    secrets_dir = service_dir / "secrets"
    secrets_dir.mkdir(parents=True)
    env["secrets"] = str(secrets_dir)
    # compatibility for old outputs.nix users
    if isinstance(machine.facts_data[service]["generator"], str):
        generator = machine.facts_data[service]["generator"]
    else:
        generator = machine.facts_data[service]["generator"]["finalScript"]
        if machine.facts_data[service]["generator"]["prompt"]:
            prompt_value = prompt(machine.facts_data[service]["generator"]["prompt"])
            env["prompt_value"] = prompt_value
    # fmt: off
    cmd = nix_shell(
        [
            "nixpkgs#bash",
            "nixpkgs#bubblewrap",
        ],
        [
            "bwrap",
            "--ro-bind", "/nix/store", "/nix/store",
            "--tmpfs",  "/usr/lib/systemd",
            "--dev", "/dev",
            "--bind", str(facts_dir), str(facts_dir),
            "--bind", str(secrets_dir), str(secrets_dir),
            "--unshare-all",
            "--unshare-user",
            "--uid", "1000",
            "--",
            "bash", "-c", generator
        ],
    )
    # fmt: on
    run(
        cmd,
        env=env,
    )
    files_to_commit = []
    # store secrets
    for secret in machine.facts_data[service]["secret"]:
        if isinstance(secret, str):
            # TODO: This is the old NixOS module, can be dropped everyone has updated.
            secret_name = secret
            groups = []
        else:
            secret_name = secret["name"]
            groups = secret.get("groups", [])

        secret_file = secrets_dir / secret_name
        if not secret_file.is_file():
            msg = f"did not generate a file for '{secret_name}' when running the following command:\n"
            msg += generator
            raise ClanError(msg)
        secret_path = secret_facts_store.set(
            service, secret_name, secret_file.read_bytes(), groups
        )
        if secret_path:
            files_to_commit.append(secret_path)

    # store facts
    for name in machine.facts_data[service]["public"]:
        fact_file = facts_dir / name
        if not fact_file.is_file():
            msg = f"did not generate a file for '{name}' when running the following command:\n"
            msg += machine.facts_data[service]["generator"]
            raise ClanError(msg)
        fact_file = public_facts_store.set(service, name, fact_file.read_bytes())
        if fact_file:
            files_to_commit.append(fact_file)
    commit_files(
        files_to_commit,
        machine.flake_dir,
        f"Update facts/secrets for service {service} in machine {machine.name}",
    )
    return True


def prompt_func(text: str) -> str:
    print(f"{text}: ")
    return read_multiline_input()


def _generate_facts_for_machine(
    machine: Machine,
    service: str | None,
    regenerate: bool,
    tmpdir: Path,
    prompt: Callable[[str], str] = prompt_func,
) -> bool:
    local_temp = tmpdir / machine.name
    local_temp.mkdir()
    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    secret_facts_store = secret_facts_module.SecretStore(machine=machine)

    public_facts_module = importlib.import_module(machine.public_facts_module)
    public_facts_store = public_facts_module.FactStore(machine=machine)

    machine_updated = False

    if service and service not in machine.facts_data:
        services = list(machine.facts_data.keys())
        raise ClanError(
            f"Could not find service with name: {service}. The following services are available: {services}"
        )

    if service:
        machine_service_facts = {service: machine.facts_data[service]}
    else:
        machine_service_facts = machine.facts_data

    for service in machine_service_facts:
        machine_updated |= generate_service_facts(
            machine=machine,
            service=service,
            regenerate=regenerate,
            secret_facts_store=secret_facts_store,
            public_facts_store=public_facts_store,
            tmpdir=local_temp,
            prompt=prompt,
        )
    if machine_updated:
        # flush caches to make sure the new secrets are available in evaluation
        machine.flush_caches()
    return machine_updated


def generate_facts(
    machines: list[Machine],
    service: str | None,
    regenerate: bool,
    prompt: Callable[[str], str] = prompt_func,
) -> bool:
    was_regenerated = False
    with TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        for machine in machines:
            errors = 0
            try:
                was_regenerated |= _generate_facts_for_machine(
                    machine, service, regenerate, tmpdir, prompt
                )
            except Exception as exc:
                log.error(f"Failed to generate facts for {machine.name}: {exc}")
                errors += 1
            if errors > 0:
                raise ClanError(
                    f"Failed to generate facts for {errors} hosts. Check the logs above"
                )

    if not was_regenerated:
        print("All secrets and facts are already up to date")
    return was_regenerated


def generate_command(args: argparse.Namespace) -> None:
    if len(args.machines) == 0:
        machines = get_all_machines(args.flake, args.option)
    else:
        machines = get_selected_machines(args.flake, args.option, args.machines)
    generate_facts(machines, args.service, args.regenerate)


def register_generate_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machines",
        type=str,
        help="machine to generate facts for. if empty, generate facts for all machines",
        nargs="*",
        default=[],
    )
    add_dynamic_completer(machines_parser, complete_machines)

    service_parser = parser.add_argument(
        "--service",
        type=str,
        help="service to generate facts for, if empty, generate facts for every service",
        default=None,
    )
    add_dynamic_completer(service_parser, complete_services_for_machine)

    parser.add_argument(
        "--regenerate",
        type=bool,
        action=argparse.BooleanOptionalAction,
        help="whether to regenerate facts for the specified machine",
        default=None,
    )
    parser.set_defaults(func=generate_command)
