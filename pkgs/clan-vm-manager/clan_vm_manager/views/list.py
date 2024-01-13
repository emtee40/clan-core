import gi

gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GObject, Gtk

from ..models import VMBase, get_initial_vms


class VMListItem(GObject.Object):
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
            # Not displayed; Can be used as id.
            row = Adw.SwitchRow()
            row.set_name(vm.url)

            row.set_title(vm.name)
            row.set_title_lines(1)

            row.set_subtitle(vm.url)
            row.set_subtitle_lines(1)

            # TODO: Avatar could also display a GdkPaintable (image)
            avatar = Adw.Avatar()
            avatar.set_text(vm.name)
            avatar.set_show_initials(True)
            avatar.set_size(50)

            row.add_prefix(avatar)

            row.connect("notify::active", self.on_row_toggle)

            return row

        list_store = Gio.ListStore()
        print(list_store)

        for vm in get_initial_vms(app.running_vms()):
            list_store.append(VMListItem(data=vm.base))

        boxed_list.bind_model(list_store, create_widget_func=create_widget)

        self.append(boxed_list)

    def on_row_toggle(self, row: Adw.SwitchRow, state: bool) -> None:
        print("Toggled", row.get_name(), "active:", row.get_active())
        # TODO: start VM here
        # question: Should we disable the switch
        # for the time until we got a response for this VM?
