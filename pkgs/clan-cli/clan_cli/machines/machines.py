import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from clan_cli.clan_uri import FlakeId

from ..cmd import run_no_stdout
from ..errors import ClanError
from ..nix import nix_build, nix_config, nix_eval, nix_metadata
from ..ssh import Host, parse_deployment_address

log = logging.getLogger(__name__)


@dataclass
class Machine:
    name: str
    flake: FlakeId
    nix_options: list[str] = field(default_factory=list)
    cached_deployment: None | dict[str, Any] = None

    _eval_cache: dict[str, str] = field(default_factory=dict)
    _build_cache: dict[str, Path] = field(default_factory=dict)

    def flush_caches(self) -> None:
        self.cached_deployment = None
        self._build_cache.clear()
        self._eval_cache.clear()

    def __str__(self) -> str:
        return f"Machine(name={self.name}, flake={self.flake})"

    def __repr__(self) -> str:
        return str(self)

    @property
    def deployment(self) -> dict:
        if self.cached_deployment is not None:
            return self.cached_deployment
        deployment = json.loads(
            self.build_nix("config.system.clan.deployment.file").read_text()
        )
        self.cached_deployment = deployment
        return deployment

    @property
    def target_host_address(self) -> str:
        # deploymentAddress is deprecated.
        val = self.deployment.get("targetHost") or self.deployment.get(
            "deploymentAddress"
        )
        if val is None:
            msg = f"the 'clan.networking.targetHost' nixos option is not set for machine '{self.name}'"
            raise ClanError(msg)
        return val

    @target_host_address.setter
    def target_host_address(self, value: str) -> None:
        self.deployment["targetHost"] = value

    @property
    def secret_facts_module(self) -> str:
        return self.deployment["facts"]["secretModule"]

    @property
    def public_facts_module(self) -> str:
        return self.deployment["facts"]["publicModule"]

    @property
    def secret_vars_module(self) -> str:
        return self.deployment["vars"]["secretModule"]

    @property
    def public_vars_module(self) -> str:
        return self.deployment["vars"]["publicModule"]

    @property
    def facts_data(self) -> dict[str, dict[str, Any]]:
        if self.deployment["facts"]["services"]:
            return self.deployment["facts"]["services"]
        return {}

    @property
    def vars_generators(self) -> dict[str, dict[str, Any]]:
        if self.deployment["vars"]["generators"]:
            return self.deployment["vars"]["generators"]
        return {}

    @property
    def secrets_upload_directory(self) -> str:
        return self.deployment["facts"]["secretUploadDirectory"]

    @property
    def flake_dir(self) -> Path:
        if self.flake.is_local():
            return self.flake.path
        elif self.flake.is_remote():
            return Path(nix_metadata(self.flake.url)["path"])
        else:
            raise ClanError(f"Unsupported flake url: {self.flake}")

    @property
    def target_host(self) -> Host:
        return parse_deployment_address(
            self.name, self.target_host_address, meta={"machine": self}
        )

    @property
    def build_host(self) -> Host:
        """
        The host where the machine is built and deployed from.
        Can be the same as the target host.
        """
        build_host = self.deployment.get("buildHost")
        if build_host is None:
            return self.target_host
        # enable ssh agent forwarding to allow the build host to access the target host
        return parse_deployment_address(
            self.name,
            build_host,
            forward_agent=True,
            meta={"machine": self, "target_host": self.target_host},
        )

    def nix(
        self,
        method: str,
        attr: str,
        extra_config: None | dict = None,
        impure: bool = False,
        nix_options: list[str] = [],
    ) -> str | Path:
        """
        Build the machine and return the path to the result
        accepts a secret store and a facts store # TODO
        """
        config = nix_config()
        system = config["system"]

        file_info = dict()
        with NamedTemporaryFile(mode="w") as config_json:
            if extra_config is not None:
                json.dump(extra_config, config_json, indent=2)
            else:
                json.dump({}, config_json)
            config_json.flush()

            file_info = json.loads(
                run_no_stdout(
                    nix_eval(
                        [
                            "--impure",
                            "--expr",
                            f'let x = (builtins.fetchTree {{ type = "file"; url = "file://{config_json.name}"; }}); in {{ narHash = x.narHash; path = x.outPath; }}',
                        ]
                    )
                ).stdout.strip()
            )

        args = []

        # get git commit from flake
        if extra_config is not None:
            metadata = nix_metadata(self.flake_dir)
            url = metadata["url"]
            if "dirtyRevision" in metadata:
                # if not impure:
                #     raise ClanError(
                #         "The machine has a dirty revision, and impure mode is not allowed"
                #     )
                # else:
                #     args += ["--impure"]
                args += ["--impure"]

            args += [
                "--expr",
                f"""
                    ((builtins.getFlake "{url}").clanInternals.machinesFunc."{system}"."{self.name}" {{
                      extraConfig = builtins.fromJSON (builtins.readFile (builtins.fetchTree {{
                        type = "file";
                        url = if (builtins.compareVersions builtins.nixVersion "2.19") == -1 then "{file_info["path"]}" else "file:{file_info["path"]}";
                        narHash = "{file_info["narHash"]}";
                      }}));
                    }}).{attr}
                """,
            ]
        else:
            if (self.flake_dir / ".git").exists():
                flake = f"git+file://{self.flake_dir}"
            else:
                flake = f"path:{self.flake_dir}"

            args += [f'{flake}#clanInternals.machines."{system}".{self.name}.{attr}']
        args += nix_options + self.nix_options

        if method == "eval":
            output = run_no_stdout(nix_eval(args)).stdout.strip()
            return output
        elif method == "build":
            outpath = run_no_stdout(nix_build(args)).stdout.strip()
            return Path(outpath)
        else:
            raise ValueError(f"Unknown method {method}")

    def eval_nix(
        self,
        attr: str,
        refresh: bool = False,
        extra_config: None | dict = None,
        impure: bool = False,
        nix_options: list[str] = [],
    ) -> str:
        """
        eval a nix attribute of the machine
        @attr: the attribute to get
        """
        if attr in self._eval_cache and not refresh and extra_config is None:
            return self._eval_cache[attr]

        output = self.nix("eval", attr, extra_config, impure, nix_options)
        if isinstance(output, str):
            self._eval_cache[attr] = output
            return output
        else:
            raise ClanError("eval_nix returned not a string")

    def build_nix(
        self,
        attr: str,
        refresh: bool = False,
        extra_config: None | dict = None,
        impure: bool = False,
        nix_options: list[str] = [],
    ) -> Path:
        """
        build a nix attribute of the machine
        @attr: the attribute to get
        """

        if attr in self._build_cache and not refresh and extra_config is None:
            return self._build_cache[attr]

        output = self.nix("build", attr, extra_config, impure, nix_options)
        if isinstance(output, Path):
            self._build_cache[attr] = output
            return output
        else:
            raise ClanError("build_nix returned not a Path")
