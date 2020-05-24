import wx
from pubsub import pub

from pyxenoverse.bac.sub_entry import ITEM_TYPES
from yabac.dlg.find import FindDialog


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
        item_type = ITEM_TYPES[self.items.GetSelection()]
        entry_type = item_type.bac_record.__fields__[self.entry.GetSelection()]
        try:
            find = int(self.find_ctrl.GetValue(), 0)
            replace = int(self.replace_ctrl.GetValue(), 0)
        except ValueError:
            self.status_bar.SetStatusText("Invalid Value")
            return None
        selected = self.entry_list.GetSelections()

        # Only do this if we have one selected item
        if len(selected) != 1:
            self.find(self.entry_list.GetFirstItem(), item_type, entry_type, find)
            return
        selected = selected[0]
        data = self.entry_list.GetItemData(selected)

        # Check to see if current entry is not one we're looking for
        if type(data) == item_type and data[entry_type] == find:
            data[entry_type] = replace
            self.select_found(selected, entry_type)
            pub.sendMessage('reindex')
        self.find(selected, item_type, entry_type, find)

    def on_replace_all(self, _):
        item_type = ITEM_TYPES[self.items.GetSelection()]
        entry_type = item_type.bac_record.__fields__[self.entry.GetSelection()]
        try:
            find = int(self.find_ctrl.GetValue(), 0)
            replace = int(self.replace_ctrl.GetValue(), 0)
        except ValueError:
            self.status_bar.SetStatusText("Invalid Value")
            return None
        count = 0
        item = self.entry_list.GetFirstItem()
        while item.IsOk():
            data = self.entry_list.GetItemData(item)
            if type(data) == item_type and data[entry_type] == find:
                data[entry_type] = replace
                count += 1
            item = self.entry_list.GetNextItem(item)

        pub.sendMessage('on_select', _=None)
        pub.sendMessage('reindex')
        self.status_bar.SetStatusText(f'Replaced {count} entry(s)')
