import wx
# import pickle
from pubsub import pub

from yabcs.panels.list import ListPanel


class MainPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.current_page = 0
        self.notebook = wx.Notebook(self)
        page_names = [
            'Part Sets',
            'Part Colors',
            'Bodies',
            'Skeletons',
        ]
        self.pages = {}

        for idx, name in enumerate(page_names):
            page = ListPanel(self.notebook)
            self.notebook.AddPage(page, name)
            self.pages[name] = page

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed, self.notebook)

        # self.Bind(wx.EVT_MENU, self.on_delete, id=wx.ID_DELETE)
        # self.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
        # self.Bind(wx.EVT_MENU, self.on_paste, id=wx.ID_PASTE)
        # self.Bind(wx.EVT_MENU, self.on_add_child, id=wx.ID_ADD)
        # self.Bind(wx.EVT_MENU, self.on_append, id=self.append_id)
        # self.Bind(wx.EVT_MENU, self.on_insert, id=self.insert_id)

        # Use some sizers to see layout options
        sizer = wx.BoxSizer()
        # sizer.Add(self.entry_list, 1, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 10)

        # Layout sizers
        self.SetSizer(sizer)
        self.SetAutoLayout(1)

    def on_page_changed(self, _):
        page = self.notebook.GetCurrentPage()
        page_name = self.notebook.GetPageText(self.notebook.GetSelection())
        page_name = page_name.replace(' ', '_').lower()
        pub.sendMessage(f"reindex_{page_name}")

        page.on_select(None)

    # def add_entry(self, parent, previous):
    #     success = False
    #     cdo = wx.CustomDataObject("BCSEntry")
    #     if wx.TheClipboard.Open():
    #         success = wx.TheClipboard.GetData(cdo)
    #     if success:
    #         entries = pickle.loads(cdo.GetData())
    #     else:
    #         entries = [BCSEntry(*(35 * [0]))]
    #     item = self.entry_list.InsertItem(parent, previous, '', data=entries[0])
    #     temp_entry_list = {
    #         entries[0].address: item
    #     }
    #     for entry in entries[1:]:
    #         temp_entry_list[entry.address] = self.entry_list.AppendItem(temp_entry_list[entry.parent], '', data=entry)
    #     self.entry_list.Select(item)
    #     self.reindex()
    #     self.on_select(None)
    #     return len(entries)
    #
    # def readjust_children(self, item):
    #     deleted_entry = self.entry_list.GetItemData(item)
    #     index = address_to_index(deleted_entry.address) + 1
    #     parent = self.entry_list.GetItemParent(item)
    #     parent_address = self.entry_list.GetItemData(parent).address
    #     temp_entry_list = {
    #         parent_address: parent
    #     }
    #     for entry in self.parent.bcs.entries[index:]:
    #         if entry.parent == parent_address:
    #             break
    #         if entry.parent == deleted_entry.address:
    #             entry.parent = deleted_entry.parent
    #         if entry.sibling == deleted_entry.address:
    #             entry.sibling = deleted_entry.sibling
    #         if entry.child == deleted_entry.address:
    #             entry.child = deleted_entry.child
    #         temp_entry_list[entry.address] = self.entry_list.AppendItem(temp_entry_list[entry.parent], '', data=entry)
    #
    # def get_children(self, item):
    #     entry = self.entry_list.GetItemData(item)
    #     index = address_to_index(entry.address)
    #     parent_address = entry.parent
    #     entries = [entry]
    #     for entry in self.parent.bcs.entries[index+1:]:
    #         if entry.parent == parent_address:
    #             break
    #         entries.append(entry)
    #     return entries
    #
    # def on_add_child(self, _):
    #     item = self.entry_list.GetSelection()
    #     if not item:
    #         return
    #     num_entries = self.add_entry(item, TLI_LAST)
    #     pub.sendMessage(
    #         'set_status_bar', text=f'Added {num_entries} entry(s) under {self.entry_list.GetItemText(item)}')
    #
    # def on_append(self, _):
    #     item = self.entry_list.GetSelection()
    #     if not item:
    #         return
    #     if item == self.entry_list.GetFirstItem():
    #         with wx.MessageDialog(self, "Cannot add entry next to root entry, must be a child", "Warning") as dlg:
    #             dlg.ShowModal()
    #             return
    #     parent = self.entry_list.GetItemParent(item)
    #     num_entries = self.add_entry(parent, item)
    #     pub.sendMessage(
    #         'set_status_bar', text=f'Added {num_entries} entry(s) after {self.entry_list.GetItemText(item)}')
    #
    # def on_insert(self, _):
    #     item = self.entry_list.GetSelection()
    #     if not item:
    #         return
    #     if item == self.entry_list.GetFirstItem():
    #         with wx.MessageDialog(self, "Cannot add entry before root entry.", "Warning") as dlg:
    #             dlg.ShowModal()
    #             return
    #     parent = self.entry_list.GetItemParent(item)
    #     previous = self.entry_list.GetFirstChild(parent)
    #     if previous == item:
    #         previous = TLI_FIRST
    #     else:
    #         while previous.IsOk():
    #             if self.entry_list.GetNextSibling(previous) == item:
    #                 break
    #             previous = self.entry_list.GetNextSibling(previous)
    #         if not previous.IsOk():
    #             previous = TLI_LAST
    #     num_entries = self.add_entry(parent, previous)
    #     pub.sendMessage(
    #         'set_status_bar', text=f'Added {num_entries} entry(s) before {self.entry_list.GetItemText(item)}')
    #
    # def on_delete(self, _):
    #     item = self.entry_list.GetSelection()
    #     if not item or item == self.entry_list.GetFirstItem():
    #         return
    #     old_num_entries = len(self.parent.bcs.entries)
    #     if self.entry_list.GetFirstChild(item):
    #         with wx.MessageDialog(self, "Delete child entries as well?", '', wx.YES | wx.NO) as dlg:
    #             if dlg.ShowModal() != wx.ID_YES:
    #                 self.readjust_children(item)
    #
    #     self.entry_list.DeleteItem(item)
    #     self.reindex()
    #     new_num_entries = len(self.parent.bcs.entries)
    #     pub.sendMessage('disable')
    #     pub.sendMessage('set_status_bar', text=f'Deleted {old_num_entries - new_num_entries} entries')
    #
    # def on_copy(self, _):
    #     item = self.entry_list.GetSelection()
    #     if not item or item == self.entry_list.GetFirstItem():
    #         return
    #     entries = self.get_children(item)
    #     if len(entries) > 1:
    #         with wx.MessageDialog(self, 'Copy children entries as well?', '', wx.YES | wx.NO) as dlg:
    #             if dlg.ShowModal() != wx.ID_YES:
    #                 entries = [entries[0]]
    #
    #     self.cdo = wx.CustomDataObject("BCSEntry")
    #     self.cdo.SetData(pickle.dumps(entries))
    #     if wx.TheClipboard.Open():
    #         wx.TheClipboard.SetData(self.cdo)
    #         wx.TheClipboard.Flush()
    #         wx.TheClipboard.Close()
    #     msg = 'Copied ' + self.entry_list.GetItemText(item)
    #     if len(entries) > 1:
    #         msg += f' and {len(entries) - 1} children'
    #     pub.sendMessage('set_status_bar', text=msg)
    #
    # def on_paste(self, _):
    #     item = self.entry_list.GetSelection()
    #     if not item or item == self.entry_list.GetFirstItem():
    #         return
    #
    #     success = False
    #     cdo = wx.CustomDataObject("BCSEntry")
    #     if wx.TheClipboard.Open():
    #         success = wx.TheClipboard.GetData(cdo)
    #         wx.TheClipboard.Close()
    #     if success:
    #         self.entry_list.SetItemData(item, pickle.loads(cdo.GetData())[0])
    #         self.reindex()
    #         pub.sendMessage('load_entry', entry=self.entry_list.GetItemData(item))
    #         pub.sendMessage('set_status_bar', text='Pasted to ' + self.entry_list.GetItemText(item))
    #
    # def reindex(self):
    #     # Set indexes first
    #     item = self.entry_list.GetFirstItem()
    #     index = 0
    #     while item.IsOk():
    #         entry = self.entry_list.GetItemData(item)
    #         entry.address = index_to_address(index)
    #         self.entry_list.SetItemText(item, f'Entry {index}')
    #         item = self.entry_list.GetNextItem(item)
    #         index += 1

    #     # Set parent/child/sibling/root
    #     first_item = item = self.entry_list.GetFirstItem()
    #     root = 0
    #     entries = []
    #     while item.IsOk():
    #         entry = self.entry_list.GetItemData(item)
    #         sibling = self.entry_list.GetNextSibling(item)
    #         child = self.entry_list.GetFirstChild(item)
    #         parent = self.entry_list.GetItemParent(item)
    #         if parent == first_item:
    #             root = entry.address

    #         entry.sibling = self.entry_list.GetItemData(sibling).address if sibling.IsOk() else 0
    #         entry.child = self.entry_list.GetItemData(child).address if child.IsOk() else 0
    #         entry.parent = self.entry_list.GetItemData(parent).address if parent != self.entry_list.GetRootItem() else 0
    #         entry.root = root

    #         entries.append(entry)
    #         item = self.entry_list.GetNextItem(item)
    #     self.parent.bcs.entries = entries



