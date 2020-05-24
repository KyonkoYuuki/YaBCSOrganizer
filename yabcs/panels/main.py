import wx
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
            page = ListPanel(self.notebook, name)
            self.notebook.AddPage(page, name)
            self.pages[name] = page

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed, self.notebook)

        # Use some sizers to see layout options
        sizer = wx.BoxSizer()
        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 10)

        # Layout sizers
        self.SetSizer(sizer)
        self.SetAutoLayout(1)

    def on_page_changed(self, _):
        page = self.notebook.GetCurrentPage()
        page_name = self.notebook.GetPageText(self.notebook.GetSelection())
        name = page_name.replace(' ', '_').lower()
        pub.sendMessage(f"reindex_{name}")

        item_type = page_name[:-1]
        if item_type.endswith('ie'):
            item_type = f'{item_type[:-2]}y'

        pub.sendMessage("change_add_text", text=item_type)

        page.on_select(None)
