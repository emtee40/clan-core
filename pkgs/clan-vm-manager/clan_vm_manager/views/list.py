from functools import partial

import gi

from ..model.use_vms import VMS

gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from ..models import VMBase, get_initial_vms


class VMListItem(GObject.Object):
    data: VMBase

    def __init__(self, data: VMBase) -> None:
        super().__init__()
        self.data = data


class ClanList(Gtk.Box):
    """
    The ClanList
    Is the composition of
    the ClanListToolbar
    the clanListView
    # ------------------------        #
    # - Tools <Start> <Stop> < Edit>  #
    # ------------------------        #
    # - List Items
    # - <...>
    # ------------------------#
    """

    def __init__(self, *, app: Adw.Application) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.application = app

        boxed_list = Gtk.ListBox()
        boxed_list.set_selection_mode(Gtk.SelectionMode.NONE)
        boxed_list.add_css_class("boxed-list")

        def create_widget(item: VMListItem) -> Gtk.Widget:
            print("Creating", item.data)
            vm = item.data
            row = Adw.ActionRow()
            # Not displayed; Can be used as id.
            row.set_name(vm.url)

            row.set_title(vm.name)
            row.set_title_lines(1)
            row.set_title_selectable(True)

            row.set_subtitle(vm._flake_attr)
            row.set_subtitle_lines(1)

            # TODO: Avatar could also display a GdkPaintable (image)
            avatar = Adw.Avatar()
            avatar.set_custom_image(Gdk.Texture.new_from_filename(vm.icon))
            avatar.set_text(vm.name + " " + vm._flake_attr)
            avatar.set_show_initials(True)
            avatar.set_size(50)

            row.add_prefix(avatar)

            switch = Gtk.Switch()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.set_valign(Gtk.Align.CENTER)
            box.append(switch)

            switch.connect("notify::active", partial(self.on_row_toggle, item.data))
            row.add_suffix(box)

            return row

        list_store = Gio.ListStore.new(VMListItem)
        print(list_store)

        for vm in get_initial_vms(VMS.use().get_running_vms()):
            list_store.append(VMListItem(data=vm.base))

        boxed_list.bind_model(list_store, create_widget_func=create_widget)

        self.append(boxed_list)

    def on_row_toggle(self, data: VMBase, row: Adw.SwitchRow, state: bool) -> None:
        print("Toggled", data, "active:", row.get_active())
        hooks = VMS.use()

        if row.get_active():
            hooks.start_vm(data.url, data._flake_attr)

        if not row.get_active():
            hooks.stop_vm(data.get_id())
