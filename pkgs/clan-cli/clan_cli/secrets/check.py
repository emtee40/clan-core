import argparse
import importlib
import logging

from ..machines.machines import Machine

log = logging.getLogger(__name__)


def check_secrets(machine: Machine, service: None | str = None) -> bool:
    secrets_module = importlib.import_module(machine.secrets_module)
    secret_store = secrets_module.SecretStore(machine=machine)
    facts_module = importlib.import_module(machine.facts_module)
    fact_store = facts_module.FactStore(machine=machine)

    missing_secrets = []
    missing_facts = []
    if service:
        services = [service]
    else:
        services = list(machine.secrets_data.keys())
    for service in services:
        for secret in machine.secrets_data[service]["secrets"]:
            if isinstance(secret, str):
                secret_name = secret
            else:
                secret_name = secret["name"]
            if not secret_store.exists(service, secret_name):
                log.info(f"Secret {secret} for service {service} is missing")
                missing_secrets.append((service, secret_name))

        for fact in machine.secrets_data[service]["facts"]:
            if not fact_store.exists(service, fact):
                log.info(f"Fact {fact} for service {service} is missing")
                missing_facts.append((service, fact))

    log.debug(f"missing_secrets: {missing_secrets}")
    log.debug(f"missing_facts: {missing_facts}")
    if missing_secrets or missing_facts:
        return False
    return True


def check_command(args: argparse.Namespace) -> None:
    machine = Machine(
        name=args.machine,
        flake=args.flake,
    )
    check_secrets(machine, service=args.service)


def register_check_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "machine",
        help="The machine to check secrets for",
    )
    parser.add_argument(
        "--service",
        help="the service to check",
    )
    parser.set_defaults(func=check_command)
