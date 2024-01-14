import multiprocessing as mp
from pathlib import Path

from clan_cli import vms
from clan_cli.errors import ClanError

from clan_vm_manager.errors.show_error import show_error_dialog
from clan_vm_manager.executor import ProcessManager
from clan_vm_manager.models import VMBase

# https://amolenaar.pages.gitlab.gnome.org/pygobject-docs/Adw-1/class-ToolbarView.html
# Will be executed in the context of the child process
def on_except(error: Exception, proc: mp.process.BaseProcess) -> None:
    show_error_dialog(ClanError(str(error)))


class VMS():
    """
    This is a singleton.
    It is initialized with the first call of use()

    Usage: 
    
    VMS.use().get_running_vms()

    VMS.use() can also be called before the data is needed. e.g. to eliminate/reduce waiting time.

    """
    proc_manager: ProcessManager
    _instance: "None | VMS" = None

    # Make sure the VMS class is used as a singleton
    def __init__(self) -> None:
        raise RuntimeError('Call use() instead')

    @classmethod
    def use(cls) -> "VMS":
        if cls._instance is None:
            print('Creating new instance')
            cls._instance = cls.__new__(cls)
            cls.proc_manager = ProcessManager()
            # Init happens here
            
        return cls._instance

    def get_running_vms(self) -> list[str]:
        return self.proc_manager.running_procs()

    def start_vm(self, url: str, attr: str) -> None:
        print(f"start_vm {url}")
        # TODO: We should use VMConfig from the history file
        vm = vms.run.inspect_vm(flake_url=url, flake_attr=attr)
        log_path = Path(".")

        # TODO: We only use the url as the ident. This is not unique as the flake_attr is missing.
        # when we migrate everything to use the ClanURI class we can use the full url as the ident
        self.proc_manager.spawn(
            ident=VMBase.static_get_id(str(vm.flake_url),vm.flake_attr),
            on_except=on_except,
            log_path=log_path,
            func=vms.run.run_vm,
            vm=vm,
        )


    def stop_vm(self, ident: str) -> None:
        self.proc_manager.kill(ident)

    def on_shutdown(self) -> None:
        print("Store: stop all running vms")
        self.proc_manager.kill_all()




