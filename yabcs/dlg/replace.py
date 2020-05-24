from enum import Enum

import wx
from wx.lib.dialogs import MultiMessageDialog
from pubsub import pub

from pyxenoverse.gui import get_first_item, get_next_item
from pyxenoverse.bcs.color_selector import ColorSelector
from yabcs.dlg.find import FindDialog
from yabcs.utils import FIND_ITEM_TYPES, color_db


class Replace(Enum):
    NOT_REPLACED = 0
    REPLACED = 1
    SKIPPED = 2


class ReplaceDialog(FindDialog):
    def __init__(self, parent, entry_list, *args, **kw):
        super().__init__(parent, entry_list, *args, **kw)
        self.SetTitle("Replace")

        self.replace_ctrl = wx.TextCtrl(self, -1, '', style=wx.TE_PROCESS_ENTER)
        self.replace_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_replace)
        self.replace_ctrl.MoveAfterInTabOrder(self.find_ctrl)

        self.grid_sizer.Add(wx.StaticText(self, -1, 'Replace: '))
        self.grid_sizer.Add(self.replace_ctrl, 0, wx.EXPAND)

        self.replace_button = wx.Button(self, -1, "Replace")
        self.replace_button.Bind(wx.EVT_BUTTON, self.on_replace)
        self.replace_button.MoveAfterInTabOrder(self.find_button)
        self.replace_all_button = wx.Button(self, -1, "Replace All")
        self.replace_all_button.Bind(wx.EVT_BUTTON, self.on_replace_all)
        self.replace_all_button.MoveAfterInTabOrder(self.replace_button)

        self.button_sizer.Insert(1, self.replace_button, 0, wx.ALL, 2)
        self.button_sizer.Insert(2, self.replace_all_button, 0, wx.ALL, 2)

        self.sizer.Fit(self)
        self.Layout()

    def on_replace(self, _):
        if not color_db.bcs:
            self.status_bar.SetStatusText("BCS Not Loaded")
            return
        item_type, fields = FIND_ITEM_TYPES[self.items.GetSelection()]
        entry_type = fields[self.entry.GetSelection()]
        find = self.find_ctrl.GetValue()
        replace = self.replace_ctrl.GetValue()
        if "name" not in entry_type:
            try:
                find = int(find, 0)
                replace = int(replace, 0)
            except ValueError:
                self.status_bar.SetStatusText("Invalid Value")
                return
        selected = self.part_sets_list.GetSelections()

        # Only do this if we have don't have one selected item
        if len(selected) != 1:
            item, _ = get_first_item(self.part_sets_list)
            self.find(item, item_type, entry_type, find)
            return
        selected = selected[0]
        data = self.part_sets_list.GetItemData(selected)

        # Check to see if current entry is not one we're looking for
        res = self.replace_item(data, item_type, entry_type, find, replace)

        # Reload if replaced
        if res == Replace.REPLACED:
            self.main_panel.pages["Part Sets"].on_select(None)

        # Find next item to replace
        self.find(selected, item_type, entry_type, find)
        if res == Replace.REPLACED:
            self.status_bar.SetStatusText(f"Replaced 1 entry")
        elif res == Replace.SKIPPED:
            self.status_bar.SetStatusText(f"Skipped 1 entry. Check your part colors")

    def on_replace_all(self, _):
        if not color_db.bcs:
            self.status_bar.SetStatusText("BCS Not Loaded")
            return
        item_type, fields = FIND_ITEM_TYPES[self.items.GetSelection()]
        entry_type = fields[self.entry.GetSelection()]
        find = self.find_ctrl.GetValue()
        replace = self.replace_ctrl.GetValue()
        if "name" not in entry_type:
            try:
                find = int(self.find_ctrl.GetValue(), 0)
                replace = int(self.replace_ctrl.GetValue(), 0)
            except ValueError:
                self.status_bar.SetStatusText("Invalid Value")
                return
        count = 0
        skipped = 0
        skipped_entries = set()
        item, _ = get_first_item(self.part_sets_list)
        while item.IsOk():
            data = self.part_sets_list.GetItemData(item)
            res = self.replace_item(data, item_type, entry_type, find, replace, skipped_entries)
            if res == Replace.REPLACED:
                count += 1
            elif res == Replace.SKIPPED:
                skipped += 1
            item = get_next_item(self.part_sets_list, item)

        self.main_panel.pages["Part Sets"].on_select(None)
        pub.sendMessage('reindex_part_sets')
        msg = f'Replaced {count} entry(s) (skipped {skipped}). '
        if skipped:
            msg += "Check your part colors"
        self.status_bar.SetStatusText(msg)

        if item_type == ColorSelector and skipped_entries:
            if entry_type == "part_colors":
                msg = "\n".join(f" * Color Selector ({cs[0]}, {cs[1]}) -> ({replace}, {cs[1]})"
                                for cs in sorted(skipped_entries))
            else:
                msg = "\n".join(f" * Color Selector ({cs[0]}, {cs[1]}) -> ({cs[0]}, {replace})"
                                for cs in sorted(skipped_entries))
            with MultiMessageDialog(self, f"The following Color Selectors were skipped.\n"
                                          f"Please check your part colors.", "Warning", msg, wx.OK) as dlg:
                dlg.ShowModal()

    @staticmethod
    def get_color_selector_indexes(data, entry_type, replace):
        if entry_type == "part_colors":
            part_colors_index = replace
            color_index = data.color
        else:
            part_colors_index = data.part_colors
            color_index = replace
        return part_colors_index, color_index

    def replace_item(self, data, item_type, entry_type, find, replace, skipped=None):
        if type(data) == item_type:
            if item_type == ColorSelector and data[entry_type] == find:
                part_colors_index, color_index = self.get_color_selector_indexes(data, entry_type, replace)
                try:
                    value = color_db[part_colors_index][color_index]
                    data[entry_type] = replace
                except IndexError:
                    if skipped is not None:
                        skipped.add((data.part_colors, data.color))
                    return Replace.SKIPPED
            else:
                if isinstance(find, int) and data[entry_type] == find:
                    data[entry_type] = replace
                    return Replace.REPLACED
                elif isinstance(find, str) and find in data[entry_type]:
                    data[entry_type] = data[entry_type].replace(find, replace)
                    return Replace.REPLACED
        return Replace.NOT_REPLACED
