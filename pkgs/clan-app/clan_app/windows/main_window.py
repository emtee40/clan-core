import logging
import threading

import gi
from clan_cli.api import API
from clan_cli.history.list import list_history

from clan_app.components.interfaces import ClanConfig
from clan_app.singletons.toast import ToastOverlay
from clan_app.singletons.use_views import ViewStack
from clan_app.singletons.use_vms import ClanStore
from clan_app.views.details import Details
from clan_app.views.list import ClanList
from clan_app.views.logs import Logs
from clan_app.views.webview import WebView, open_file

gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

from clan_app.components.trayicon import TrayIcon

log = logging.getLogger(__name__)


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, config: ClanConfig) -> None:
        super().__init__()
        self.set_title("Clan Manager")
        self.set_default_size(980, 850)

        # Overlay for GTK side exclusive toasts
        overlay = ToastOverlay.use().overlay
        view = Adw.ToolbarView()
        overlay.set_child(view)

        self.set_content(overlay)

        header = Adw.HeaderBar()
        view.add_top_bar(header)

        app = Gio.Application.get_default()
        assert app is not None
        self.tray_icon: TrayIcon = TrayIcon(app)

        # Initialize all ClanStore
        threading.Thread(target=self._populate_vms).start()

        stack_view = ViewStack.use().view
        stack_view.add_named(ClanList(config), "list")
        stack_view.add_named(Details(), "details")
        stack_view.add_named(Logs(), "logs")

        # Override platform specific functions
        API.register(open_file)

        webview = WebView(methods=API._registry)

        stack_view.add_named(webview.get_webview(), "webview")
        stack_view.set_visible_child_name(config.initial_view)

        view.set_content(stack_view)

        self.connect("destroy", self.on_destroy)

    def _set_clan_store_ready(self) -> bool:
        ClanStore.use().emit("is_ready")
        return GLib.SOURCE_REMOVE

    def _populate_vms(self) -> None:
        # Execute `clan flakes add <path>` to democlan for this to work
        # TODO: Make list_history a generator function
        for entry in list_history():
            GLib.idle_add(ClanStore.use().create_vm_task, entry)

        GLib.idle_add(self._set_clan_store_ready)

    def kill_vms(self) -> None:
        log.debug("Killing all VMs")
        ClanStore.use().kill_all()

    def on_destroy(self, source: "Adw.ApplicationWindow") -> None:
        log.info("====Destroying Adw.ApplicationWindow===")
        ClanStore.use().kill_all()
        self.tray_icon.destroy()
