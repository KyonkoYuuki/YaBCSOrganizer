import wx

from pubsub import pub
from wx.dataview import TreeListCtrl, EVT_TREELIST_SELECTION_CHANGED


class ListPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent

        self.entry_list = TreeListCtrl(self)
        self.entry_list.AppendColumn("Entry")
        # self.entry_list.Bind(EVT_TREELIST_ITEM_CONTEXT_MENU, self.on_right_click)
        self.entry_list.Bind(EVT_TREELIST_SELECTION_CHANGED, self.on_select)

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
