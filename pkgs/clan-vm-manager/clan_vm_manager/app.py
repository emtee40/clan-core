#!/usr/bin/env python3
import argparse
from dataclasses import dataclass
from pathlib import Path

import gi
from clan_cli import vms

from clan_vm_manager.views.list import ClanList

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import multiprocessing as mp

from clan_cli.clan_uri import ClanURI
from gi.repository import Adw, Gdk, Gio, Gtk

from .constants import constants
from .errors.show_error import show_error_dialog
from .executor import ProcessManager


@dataclass
class ClanConfig:
    initial_view: str
    url: ClanURI | None


# https://amolenaar.pages.gitlab.gnome.org/pygobject-docs/Adw-1/class-ToolbarView.html
# Will be executed in the context of the child process
def on_except(error: Exception, proc: mp.process.BaseProcess) -> None:
    show_error_dialog(str(error))


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, config: ClanConfig) -> None:
        super().__init__()
        self.set_title("cLAN Manager")
        self.set_default_size(800, 600)
        view = Adw.ToolbarView()
        self.set_content(view)

        header = Adw.HeaderBar()
        view.add_top_bar(header)

        # Create a navigation view
        self.nav_view = Adw.NavigationView()
        view.set_content(self.nav_view)

        # Create the first page
        self.list_view = Adw.NavigationPage(title="Your cLan")
        self.list_view.set_child(ClanList(app=app))

        # Push the first page to the navigation view
        self.nav_view.push(self.list_view)


class Application(Adw.Application):
    def __init__(self, config: ClanConfig) -> None:
        super().__init__(
            application_id=constants["APPID"], flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        # TODO:
        # self.init_style()
        self.config = config
        # self.window = MainWindow(self.config)
        self.proc_manager = ProcessManager()
        self.connect("shutdown", self.on_shutdown)

    def on_shutdown(self, app: Gtk.Application) -> None:
        print("Shutting down")
        self.proc_manager.kill_all()

    def spawn_vm(self, url: str, attr: str) -> None:
        print(f"spawn_vm {url}")

        # TODO: We should use VMConfig from the history file
        vm = vms.run.inspect_vm(flake_url=url, flake_attr=attr)
        log_path = Path(".")

        # TODO: We only use the url as the ident. This is not unique as the flake_attr is missing.
        # when we migrate everything to use the ClanURI class we can use the full url as the ident
        self.proc_manager.spawn(
            ident=url,
            on_except=on_except,
            log_path=log_path,
            func=vms.run.run_vm,
            vm=vm,
        )

    def stop_vm(self, url: str, attr: str) -> None:
        self.proc_manager.kill(url)

    def running_vms(self) -> list[str]:
        return self.proc_manager.running_procs()

    def do_activate(self) -> None:
        self.init_style()
        window = MainWindow(app=self, config=self.config)
        window.set_application(self)
        window.present()

    # TODO: For css styling
    def init_style(self) -> None:
        resource_path = Path(__file__).parent / "style.css"
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(str(resource_path))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def show_join(args: argparse.Namespace) -> None:
    app = Application(
        config=ClanConfig(url=args.clan_uri, initial_view="join"),
    )
    return app.run()


def register_join_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("clan_uri", type=ClanURI, help="clan URI to join")
    parser.set_defaults(func=show_join)


def show_overview(args: argparse.Namespace) -> None:
    app = Application(
        config=ClanConfig(url=None, initial_view="overview"),
    )
    return app.run()


def register_overview_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=show_overview)
