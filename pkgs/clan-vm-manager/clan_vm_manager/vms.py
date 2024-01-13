import multiprocessing as mp
from pathlib import Path

from clan_cli import vms

from clan_vm_manager.errors.show_error import show_error_dialog
from clan_vm_manager.executor import ProcessManager


# https://amolenaar.pages.gitlab.gnome.org/pygobject-docs/Adw-1/class-ToolbarView.html
# Will be executed in the context of the child process
def on_except(error: Exception, proc: mp.process.BaseProcess) -> None:
    show_error_dialog(str(error))


proc_manager = ProcessManager()


def running_vms() -> list[str]:
    return proc_manager.running_procs()


def spawn_vm(url: str, attr: str) -> None:
    print(f"spawn_vm {url}")

    # TODO: We should use VMConfig from the history file
    vm = vms.run.inspect_vm(flake_url=url, flake_attr=attr)
    log_path = Path(".")

    # TODO: We only use the url as the ident. This is not unique as the flake_attr is missing.
    # when we migrate everything to use the ClanURI class we can use the full url as the ident
    proc_manager.spawn(
        ident=url,
        on_except=on_except,
        log_path=log_path,
        func=vms.run.run_vm,
        vm=vm,
    )


def stop_vm(url: str, attr: str) -> None:
    proc_manager.kill(url)
