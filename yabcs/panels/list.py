import wx

from pubsub import pub
from wx.dataview import TreeListCtrl, EVT_TREELIST_SELECTION_CHANGED, EVT_TREELIST_ITEM_CONTEXT_MENU


class ListPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent

        self.append_id = wx.NewId()
        self.insert_id = wx.NewId()
        self.entry_list = TreeListCtrl(self)
        self.entry_list.AppendColumn("Entry")
        self.entry_list.Bind(EVT_TREELIST_ITEM_CONTEXT_MENU, self.on_right_click)
        self.entry_list.Bind(EVT_TREELIST_SELECTION_CHANGED, self.on_select)
        self.cdo = wx.CustomDataObject("BCSEntry")

        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('c'), wx.ID_COPY),
            (wx.ACCEL_CTRL, ord('v'), wx.ID_PASTE),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, wx.ID_DELETE),
        ])
        self.entry_list.SetAcceleratorTable(accelerator_table)

        sizer = wx.BoxSizer()
        sizer.Add(self.entry_list, 1, wx.ALL | wx.EXPAND)

        pub.subscribe(self.on_select, 'on_select')

        self.SetSizer(sizer)
        self.SetAutoLayout(1)

    def on_select(self, _):
        selected = self.entry_list.GetSelections()
        if len(selected) != 1:
            pub.sendMessage('hide_panels')
            return
        entry = self.entry_list.GetItemData(selected[0])
        pub.sendMessage('load_entry', item=selected[0], entry=entry)

    def add_single_selection_items(self, menu):
        selections = self.entry_list.GetSelections()
        item = self.entry_list.GetItemData(selections[0])
        if item:
            item_type = str(item).split('(')[0]
        else:
            item_type = 'BCS' + self.entry_list.GetItemText(selections[0]).replace(' ', '')
        item_name = item_type[3:]

        enabled = item != None
        menu.Append(wx.ID_ADD, f"&Add {item_name}\tCtrl+A", f"Add {item_name} at the end")
        append = menu.Append(self.append_id, f"Append {item_name}", f"Append {item_name} after")
        append.Enable(enabled)
        insert = menu.Append(self.insert_id, f"Insert {item_name}", f"Insert {item_name} before")
        insert.Enable(enabled)

    def on_right_click(self, _):
        selections = self.entry_list.GetSelections()
        if not selections:
            return
        menu = wx.Menu()
        if len(selections) == 1:
            self.add_single_selection_items(menu)

        # copy = menu.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy entry")
        # paste = menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste entry")
        # delete = menu.Append(wx.ID_DELETE, "&Delete\tDelete", "Delete entry(s)")
        # menu.Append(wx.ID_ADD, "Add &New Child\tCtrl+N", "Add child entry")

        # # TODO: replace
        # enabled = selection != self.entry_list.GetFirstItem()
        # copy.Enable(enabled)
        # success = False
        # if enabled and wx.TheClipboard.Open():
        #     success = wx.TheClipboard.IsSupported(wx.DataFormat("BCSEntry"))
        #     wx.TheClipboard.Close()
        # paste.Enable(success)
        # delete.Enable(enabled)
        # append.Enable(enabled)
        # insert.Enable(enabled)
        self.PopupMenu(menu)
        menu.Destroy()
