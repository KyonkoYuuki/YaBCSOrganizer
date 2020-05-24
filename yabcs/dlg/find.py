import re

import wx

from pubsub import pub
from pyxenoverse.bac.sub_entry import ITEM_TYPES
from pyxenoverse.gui.ctrl.hex_ctrl import HexCtrl
from pyxenoverse.gui.ctrl.multiple_selection_box import MultipleSelectionBox
from pyxenoverse.gui.ctrl.single_selection_box import SingleSelectionBox
from pyxenoverse.gui.ctrl.unknown_hex_ctrl import UnknownHexCtrl

pattern = re.compile(r'([ \n/_])([a-z0-9]+)')


class FindDialog(wx.Dialog):
    def __init__(self, parent, entry_list, *args, **kw):
        super().__init__(parent, *args, **kw, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        self.root = parent
        self.entry_list = entry_list
        self.SetTitle("Find")
        # self.all_types = '--All Types--'
        self.selected = None
        self.focused = None

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.hsizer = wx.BoxSizer()
        self.sizer.Add(self.hsizer)

        self.items = wx.Choice(self, -1, choices=[item.__name__ for item in ITEM_TYPES.values()])  # + [self.all_types])
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
            data = None
            selected = self.entry_list.GetSelections()
            if len(selected) == 1:
                data = self.entry_list.GetItemData(selected[0])
                self.items.SetSelection(data.type)
                self.on_choice(None)
            ctrl = self.FindFocus()
            if type(ctrl.GetParent()) in (wx.SpinCtrlDouble, UnknownHexCtrl, SingleSelectionBox, MultipleSelectionBox):
                ctrl = ctrl.GetParent()
            elif type(ctrl.GetParent().GetParent()) in (SingleSelectionBox, MultipleSelectionBox):
                ctrl = ctrl.GetParent().GetParent()
            name = pattern.sub(r'_\2', ctrl.GetName().lower())
            try:
                if data:
                    self.entry.SetSelection(data.__fields__.index(name))
                if type(ctrl) in (HexCtrl, UnknownHexCtrl, SingleSelectionBox, MultipleSelectionBox):
                    self.find_ctrl.SetValue(f'0x{ctrl.GetValue():X}')
                else:
                    self.find_ctrl.SetValue(str(ctrl.GetValue()))
            except ValueError:
                pass
        except AttributeError:
            pass

    def on_choice(self, _):
        self.entry.Clear()
        selection = self.items.GetSelection()
        if selection < len(ITEM_TYPES):
            item_type = ITEM_TYPES[self.items.GetSelection()]
            for attr in item_type.bac_record.__fields__:
                self.entry.Append(attr)
        # self.entry.Append(self.all_types)
        self.entry.Select(0)

    def select_found(self, item, entry_type):
        self.entry_list.UnselectAll()
        self.entry_list.Select(item)
        pub.sendMessage('on_select', _=None)
        pub.sendMessage('focus_on', entry=entry_type)
        self.SetFocus()
        self.status_bar.SetStatusText('')

    def find(self, selected, item_type, entry_type, find):
        if not selected.IsOk():
            self.status_bar.SetStatusText('No matches found')
            return
        item = self.entry_list.GetNextItem(selected)
        while item != selected:
            data = self.entry_list.GetItemData(item)
            # if item_type is None and type(data) in ITEM_TYPES and entry_type is None:
            #     for field in data.__fields__:
            #         if data[field] == find:
            #             break
            #     else:
            #         continue
            #     self.select_found(item, field)
            #     break
            # elif type(data) == item_type and entry_type is None:
            #     for field in data.__fields__:
            #         if data[field] == find:
            #             break
            #     else:
            #         continue
            #     self.select_found(item, field)
            #     break
            if type(data) == item_type and (find is None or data[entry_type] == find):
                self.select_found(item, entry_type)
                break

            item = self.entry_list.GetNextItem(item)
            if not item.IsOk():
                item = self.entry_list.GetFirstItem()
        else:
            self.status_bar.SetStatusText('No matches found')

    def on_find(self, _):
        # Get Item Type
        selection = self.items.GetSelection()
        item_type = ITEM_TYPES[selection] if selection < len(ITEM_TYPES) else None

        # Get Entry Type
        if item_type:
            bac_record = item_type.bac_record
            selection = self.entry.GetSelection()
            entry_type = bac_record.__fields__[selection] if selection < len(bac_record.__fields__) else None
        else:
            entry_type = None

        # Get Find value
        value = self.find_ctrl.GetValue()
        if value:
            try:
                find = int(value, 0)
            except ValueError:
                self.status_bar.SetStatusText("Invalid Value")
                return
        else:
            if item_type is None or entry_type is None:
                self.status_bar.SetStatusText("Need a value to search for")
                return
            find = None
        selected = self.entry_list.GetSelections()
        if len(selected) == 1:
            selected = selected[0]
        else:
            selected = self.entry_list.GetFirstItem()
        self.find(selected, item_type, entry_type, find)
