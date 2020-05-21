from collections import defaultdict
import wx

from pubsub import pub
from wx.dataview import TreeListCtrl, TL_MULTIPLE, EVT_TREELIST_SELECTION_CHANGED, EVT_TREELIST_ITEM_CONTEXT_MENU


from pyxenoverse.bcs.part_set import PartSet, BCS_PART_LIST
from pyxenoverse.bcs.part import Part
from pyxenoverse.bcs.color_selector import ColorSelector
from pyxenoverse.bcs.physics import Physics
from pyxenoverse.bcs.body import Body
from pyxenoverse.bcs.part_color import PartColor
from pyxenoverse.bcs.color import Color
from pyxenoverse.bcs.bone_scale import BoneScale
from pyxenoverse.bcs.skeleton import Skeleton
from pyxenoverse.bcs.bone import Bone


class ListPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.parent = parent

        self.add_ids = defaultdict(lambda: wx.NewId())
        self.insert_ids = defaultdict(lambda: wx.NewId())
        self.append_ids = defaultdict(lambda: wx.NewId())
        self.entry_list = wx.TreeCtrl(self, style=wx.TR_MULTIPLE | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT)
        self.entry_list.Bind(wx.EVT_TREE_ITEM_MENU, self.on_right_click)
        self.entry_list.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
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
        if not self.entry_list:
            return
        selected = self.entry_list.GetSelections()
        if len(selected) != 1:
            pub.sendMessage('hide_panels')
            return
        entry = self.entry_list.GetItemData(selected[0])
        pub.sendMessage('load_entry', item=selected[0], entry=entry)

    def add_menu_items(self, menu, name):
        menu.Append(self.add_ids[name], f"Add {name}", f"Add {name} at the end")
        menu.Append(self.append_ids[name], f"Append {name}", f"Append {name} after")
        menu.Append(self.insert_ids[name], f"Insert {name}", f"Insert {name} before")

    def add_part_items(self, menu, part_set):
        sub_menu = wx.Menu()
        for part in BCS_PART_LIST:
            name = part.replace('_', ' ').title()
            add_part = sub_menu.Append(self.add_ids[name], f"Add {name} part", f"Add {name}")
            add_part.Enable(part not in part_set.parts)
        menu.AppendSubMenu(sub_menu, "Parts")

    def add_single_selection_items(self, menu, selected):
        data = self.entry_list.GetItemData(selected)
        if isinstance(data, PartSet):
            self.add_menu_items(menu, "Part Set")
            menu.AppendSeparator()
            self.add_part_items(menu, data)
        elif isinstance(data, Part):
            part_set_item = self.entry_list.GetItemParent(selected)
            part_set = self.entry_list.GetItemData(part_set_item)
            self.add_part_items(menu, part_set)
            menu.AppendSeparator()
            self.add_menu_items(menu, "Color Selector")
            menu.AppendSeparator()
            self.add_menu_items(menu, "Physics")
        elif isinstance(data, ColorSelector):
            self.add_menu_items(menu, "Color Selector")
        elif isinstance(data, Physics):
            self.add_menu_items(menu, "Physics")
        elif isinstance(data, PartColor):
            self.add_menu_items(menu, "Part Color")
            menu.AppendSeparator()
            self.add_menu_items(menu, "Color")
        elif isinstance(data, Color):
            self.add_menu_items(menu, "Color")
        elif isinstance(data, Body):
            self.add_menu_items(menu, "Body")
            menu.AppendSeparator()
            self.add_menu_items(menu, "Bone Scale")
        elif isinstance(data, BoneScale):
            self.add_menu_items(menu, "Bone Scale")
        elif isinstance(data, Skeleton):
            self.add_menu_items(menu, "Skeleton")
            menu.AppendSeparator()
            self.add_menu_items(menu, "Bone")
        elif isinstance(data, Bone):
            self.add_menu_items(menu, "Bone")

    def on_right_click(self, _):
        selections = self.entry_list.GetSelections()
        if not selections:
            return
        menu = wx.Menu()
        if len(selections) == 1:
            self.add_single_selection_items(menu, selections[0])

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
