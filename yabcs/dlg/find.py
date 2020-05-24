import re

import wx

from pubsub import pub
from pyxenoverse.gui import get_first_item, get_next_item
from pyxenoverse.gui.ctrl.hex_ctrl import HexCtrl
from pyxenoverse.gui.ctrl.multiple_selection_box import MultipleSelectionBox
from pyxenoverse.gui.ctrl.single_selection_box import SingleSelectionBox
from pyxenoverse.gui.ctrl.unknown_hex_ctrl import UnknownHexCtrl

from yabcs.utils import FIND_ITEM_TYPES, color_db

pattern = re.compile(r'([ \n/_])([a-z0-9]+)')


class FindDialog(wx.Dialog):
    def __init__(self, parent, main_panel, *args, **kw):
        super().__init__(parent, *args, **kw, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        self.root = parent
        self.main_panel = main_panel
        self.part_sets_list = self.main_panel.pages["Part Sets"].entry_list

        self.SetTitle("Find")
        self.selected = None
        self.focused = None

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.hsizer = wx.BoxSizer()
        self.sizer.Add(self.hsizer)

        self.items = wx.Choice(self, -1, choices=[item[0].get_readable_name() for item in FIND_ITEM_TYPES])
        self.items.Bind(wx.EVT_CHOICE, self.on_choice)

        self.entry = wx.Choice(self, -1)

        # Setup Selections
        self.items.SetSelection(0)
        self.on_choice(None)

        self.find_ctrl = wx.TextCtrl(self, -1, '', size=(150, -1), style=wx.TE_PROCESS_ENTER)
        self.find_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_find)
        self.find_ctrl.SetFocus()

        self.grid_sizer = wx.FlexGridSizer(rows=4, cols=2, hgap=10, vgap=10)
        self.grid_sizer.Add(wx.StaticText(self, -1, 'Type: '))
        self.grid_sizer.Add(self.items, 0, wx.EXPAND)
        self.grid_sizer.Add(wx.StaticText(self, -1, 'Entry: '))
        self.grid_sizer.Add(self.entry, 0, wx.EXPAND)
        self.grid_sizer.Add(wx.StaticText(self, -1, 'Find: '))
        self.grid_sizer.Add(self.find_ctrl, 0, wx.EXPAND)
        self.hsizer.Add(self.grid_sizer, 0, wx.ALL, 10)

        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.find_button = wx.Button(self, -1, "Find Next")
        self.find_button.Bind(wx.EVT_BUTTON, self.on_find)

        self.button_sizer.Add(self.find_button, 0, wx.ALL, 2)
        self.button_sizer.Add(wx.Button(self, wx.ID_CANCEL, "Cancel"), 0, wx.ALL, 2)
        self.hsizer.Add(self.button_sizer, 0, wx.ALL, 8)

        self.status_bar = wx.StatusBar(self)
        self.sizer.Add(self.status_bar, 0, wx.EXPAND)

        self.Bind(wx.EVT_SHOW, self.on_show)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        self.SetAutoLayout(0)

    def on_show(self, e):
        if not e.IsShown():
            return
        try:
            selected = self.part_sets_list.GetSelections()
            item_types, fields = zip(*FIND_ITEM_TYPES)
            # Only set value if one item is selected
            if not len(selected) == 1:
                return
            data = self.part_sets_list.GetItemData(selected[0])
            try:
                item_index = item_types.index(type(data))
                self.items.SetSelection(item_index)
                self.on_choice(None)
            except ValueError:
                return

            # Find control focus
            ctrl = self.FindFocus()
            if type(ctrl.GetParent()) in (wx.SpinCtrlDouble, UnknownHexCtrl, SingleSelectionBox, MultipleSelectionBox):
                ctrl = ctrl.GetParent()
            elif type(ctrl.GetParent().GetParent()) in (SingleSelectionBox, MultipleSelectionBox):
                ctrl = ctrl.GetParent().GetParent()
            name = pattern.sub(r'_\2', ctrl.GetName().lower())
            try:
                if data and not isinstance(data, list):
                    self.entry.SetSelection(fields[item_index].index(name))

                # Set hex value if needed
                if type(ctrl) in (HexCtrl, UnknownHexCtrl, SingleSelectionBox, MultipleSelectionBox):
                    self.find_ctrl.SetValue(f'0x{ctrl.GetValue():X}')
                else:
                    self.find_ctrl.SetValue(str(ctrl.GetValue()).split(":")[0])
            except ValueError:
                pass
        except AttributeError:
            pass

    def on_choice(self, _):
        self.entry.Clear()
        selection = self.items.GetSelection()
        if selection < len(FIND_ITEM_TYPES):
            item_type, attrs = FIND_ITEM_TYPES[self.items.GetSelection()]
            for attr in attrs:
                self.entry.Append(attr)
        self.entry.Select(0)

    def select_found(self, item, entry_type):
        # Set page if not on correct page
        if self.main_panel.notebook.GetSelection() != 0:
            self.main_panel.notebook.SetSelection(0)

        # Select found item
        self.part_sets_list.UnselectAll()
        self.part_sets_list.SelectItem(item)

        # Expand item and scroll to it
        self.main_panel.pages["Part Sets"].expand_parents(item)
        if not self.part_sets_list.IsVisible(item):
            self.part_sets_list.ScrollTo(item)

        # Focus on entry
        pub.sendMessage('focus_on', entry=entry_type)
        self.SetFocus()
        self.status_bar.SetStatusText('')

    def find(self, selected, item_type, entry_type, find):
        if not selected.IsOk():
            self.status_bar.SetStatusText('No matches found')
            return
        # Get next item
        item = get_next_item(self.part_sets_list, selected)
        if not item.IsOk():
            item, _ = get_first_item(self.part_sets_list)

        # Loop over
        while item != selected:
            data = self.part_sets_list.GetItemData(item)
            if (type(data) == item_type and
                    (find is None or
                     (isinstance(find, int) and data[entry_type] == find) or
                     (isinstance(find, str) and find.lower() in data[entry_type].lower()))):
                self.select_found(item, entry_type)
                break

            item = get_next_item(self.part_sets_list, item)
            if not item.IsOk():
                item, _ = get_first_item(self.part_sets_list)
        else:
            self.status_bar.SetStatusText('No matches found')

    def on_find(self, _):
        if not color_db.bcs:
            self.status_bar.SetStatusText("BCS not loaded")
            return
        # Get Item Type
        selection = self.items.GetSelection()
        item_type, fields = FIND_ITEM_TYPES[selection]

        # Get Entry Type
        selection = self.entry.GetSelection()
        entry_type = fields[selection]

        # Get Find value
        find = self.find_ctrl.GetValue()
        if "name" not in entry_type:
            try:
                find = int(find, 0)
            except ValueError:
                self.status_bar.SetStatusText("Invalid Value")
                return
        selected = self.part_sets_list.GetSelections()
        if len(selected) == 1:
            selected = selected[0]
        else:
            selected, _ = get_first_item(self.part_sets_list)
        self.find(selected, item_type, entry_type, find)
