from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import gi
from clan_cli.history.list import list_history

from .errors.show_error import show_error_dialog

gi.require_version("GdkPixbuf", "2.0")

from clan_cli.errors import ClanError
from gi.repository import GdkPixbuf

from clan_vm_manager import assets


class VMStatus(StrEnum):
    RUNNING = "Running"
    STOPPED = "Stopped"


@dataclass(frozen=True)
class VMBase:
    icon: Path | GdkPixbuf.Pixbuf
    name: str
    url: str
    status: VMStatus
    _flake_attr: str

    @staticmethod
    def name_to_type_map() -> OrderedDict[str, type]:
        return OrderedDict(
            {
                "Icon": GdkPixbuf.Pixbuf,
                "Name": str,
                "URL": str,
                "Status": str,
                "_FlakeAttr": str,
            }
        )
    
    def get_id(self) -> str:
        return self.url + self._flake_attr

    @staticmethod
    def to_idx(name: str) -> int:
        return list(VMBase.name_to_type_map().keys()).index(name)

    def list_data(self) -> OrderedDict[str, Any]:
        return OrderedDict(
            {
                "Icon": str(self.icon),
                "Name": self.name,
                "URL": self.url,
                "Status": self.status,
                "_FlakeAttr": self._flake_attr,
            }
        )


@dataclass(frozen=True)
class VM:
    # Inheritance is bad. Lets use composition
    # Added attributes are separated from base attributes.
    base: VMBase
    autostart: bool = False
    description: str | None = None


# TODO: How to handle incompatible / corrupted history file. Delete it?
# start/end indexes can be used optionally for pagination
def get_initial_vms(
    running_vms: list[str], start: int = 0, end: int | None = None
) -> list[VM]:
    vm_list = []

    try:
        # Execute `clan flakes add <path>` to democlan for this to work
        for entry in list_history():
            icon = assets.loc / "placeholder.jpeg"
            if entry.flake.icon is not None:
                icon = entry.flake.icon

            status = VMStatus.STOPPED
            if entry.flake.flake_url in running_vms:
                status = VMStatus.RUNNING

            base = VMBase(
                icon=icon,
                name=entry.flake.clan_name,
                url=entry.flake.flake_url,
                status=status,
                _flake_attr=entry.flake.flake_attr,
            )
            vm_list.append(VM(base=base))
    except ClanError as e:
        show_error_dialog(e)

    # start/end slices can be used for pagination
    return vm_list[start:end]
