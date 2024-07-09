from abc import ABC, abstractmethod
from pathlib import Path

from clan_cli.machines.machines import Machine


class SecretStoreBase(ABC):
    @abstractmethod
    def __init__(self, machine: Machine) -> None:
        pass

    @abstractmethod
    def set(
        self, service: str, name: str, value: bytes, groups: list[str]
    ) -> Path | None:
        pass

    @abstractmethod
    def get(self, service: str, name: str) -> bytes:
        pass

    @abstractmethod
    def exists(self, service: str, name: str) -> bool:
        pass

    def update_check(self) -> bool:
        return False

    @abstractmethod
    def upload(self, output_dir: Path) -> None:
        pass
