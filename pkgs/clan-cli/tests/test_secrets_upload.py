from typing import TYPE_CHECKING

import pytest
from cli import Cli
from fixtures_flakes import FlakeForTest

from clan_cli.ssh import HostGroup

if TYPE_CHECKING:
    from age_keys import KeyPair


@pytest.mark.impure
def test_secrets_upload(
    monkeypatch: pytest.MonkeyPatch,
    test_flake_with_core: FlakeForTest,
    host_group: HostGroup,
    age_keys: list["KeyPair"],
) -> None:
    monkeypatch.chdir(test_flake_with_core.path)
    monkeypatch.setenv("SOPS_AGE_KEY", age_keys[0].privkey)

    cli = Cli()
    cli.run(
        [
            "--flake",
            str(test_flake_with_core.path),
            "secrets",
            "users",
            "add",
            "user1",
            age_keys[0].pubkey,
        ]
    )

    cli.run(
        [
            "--flake",
            str(test_flake_with_core.path),
            "secrets",
            "machines",
            "add",
            "vm1",
            age_keys[1].pubkey,
        ]
    )
    monkeypatch.setenv("SOPS_NIX_SECRET", age_keys[0].privkey)
    cli.run(
        ["--flake", str(test_flake_with_core.path), "secrets", "set", "vm1-age.key"]
    )

    flake = test_flake_with_core.path.joinpath("flake.nix")
    host = host_group.hosts[0]
    addr = f"{host.user}@{host.host}:{host.port}?StrictHostKeyChecking=no&UserKnownHostsFile=/dev/null&IdentityFile={host.key}"
    new_text = flake.read_text().replace("__CLAN_TARGET_ADDRESS__", addr)

    flake.write_text(new_text)
    cli.run(["--flake", str(test_flake_with_core.path), "secrets", "upload", "vm1"])

    # the flake defines this path as the location where the sops key should be installed
    sops_key = test_flake_with_core.path.joinpath("key.txt")
    assert sops_key.exists()
    assert sops_key.read_text() == age_keys[0].privkey
