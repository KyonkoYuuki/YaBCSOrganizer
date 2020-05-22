from collections import defaultdict
from functools import partial
import wx
from wx.lib.dialogs import MultiMessageDialog

from pubsub import pub

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
from pyxenoverse.gui.file_drop_target import FileDropTarget
from pyxenoverse.gui.ctrl.multiple_selection_box import MultipleSelectionBox
from pyxenoverse.gui.ctrl.single_selection_box import SingleSelectionBox
from pyxenoverse.gui.ctrl.unknown_hex_ctrl import UnknownHexCtrl

from yabcs.colordb import color_db


class ListPanel(wx.Panel):
    def __init__(self, parent, name):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.focus = None
        self.name = name
        self.reindex_name = f"reindex_{name.replace(' ', '_').lower()}"

        self.add_ids = defaultdict(lambda: wx.NewId())
        self.insert_ids = defaultdict(lambda: wx.NewId())
        self.append_ids = defaultdict(lambda: wx.NewId())
        self.entry_list = wx.TreeCtrl(self, style=wx.TR_MULTIPLE | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT)
        self.entry_list.Bind(wx.EVT_TREE_ITEM_MENU, self.on_right_click)
        self.entry_list.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
        self.entry_list.SetDropTarget(FileDropTarget(self, "load_bcs"))
        self.cdo = wx.CustomDataObject("BCSEntry")

        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_delete, id=wx.ID_DELETE)

        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('c'), wx.ID_COPY),
            (wx.ACCEL_CTRL, ord('v'), wx.ID_PASTE),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, wx.ID_DELETE),
        ])
        self.entry_list.SetAcceleratorTable(accelerator_table)

        sizer = wx.BoxSizer()
        sizer.Add(self.entry_list, 1, wx.ALL | wx.EXPAND)

        pub.subscribe(self.on_select, 'on_select')
        pub.subscribe(self.set_focus, 'set_focus')
        pub.subscribe(self.clear_focus, 'clear_focus')

        self.SetSizer(sizer)
        self.SetAutoLayout(1)

    def on_open(self, _):
        pub.sendMessage('open_bcs', e=None)

    def on_save(self, _):
        pub.sendMessage('save_bcs', e=None)

    def on_delete(self, _):
        selected = self.entry_list.GetSelections()
        if not selected:
            return
        root = self.entry_list.GetRootItem()

        # Only delete root nodes
        items_to_delete = []
        for item in selected:
            parent = self.entry_list.GetItemParent(item)
            while parent != root and parent.IsOk():
                if parent in selected:
                    break
                parent = self.entry_list.GetItemParent(parent)
            if parent == root:
                items_to_delete.append(item)

        for item in reversed(items_to_delete):
            data = self.entry_list.GetItemData(item)
            text = self.entry_list.GetItemText(item)
            parent = self.entry_list.GetItemParent(item)
            parent_data = self.entry_list.GetItemData(parent)
            index = -1
            # Get Index
            if data:
                index = int(text.split(':')[0])

            # Delete from BCS
            if not data and text == "Physics":
                parent_data.physics.clear()
            elif not data and text == "Color Selectors":
                parent_data.color_selectors.clear()
            elif isinstance(data, PartSet):
                color_db.bcs.part_sets.pop(index)
            elif isinstance(data, ColorSelector):
                part_set_item = self.entry_list.GetItemParent(parent)
                part_set = self.entry_list.GetItemData(part_set_item)
                part_set.color_selectors.pop(index)
            elif isinstance(data, Physics):
                part_set_item = self.entry_list.GetItemParent(parent)
                part_set = self.entry_list.GetItemData(part_set_item)
                part_set.physics.pop(index)
            elif isinstance(data, PartColor):
                conflicts = self.check_color_conflicts(index)
                if conflicts:
                    msg = "\n".join([f"* Part Set {c[0]}, {c[1]}\n" for c in conflicts])
                    with MultiMessageDialog(self, "Cannot delete Part Color.  The following parts are still using it:",
                                            "Warning", msg, wx.OK) as dlg:
                        dlg.ShowModal()
                    return
                color_db.bcs.part_colors.pop(index)
                color_db.pop(index)
                self.delete_colors(index)
            elif isinstance(data, Color):
                parent_text = self.entry_list.GetItemText(parent)
                parent_index = int(parent_text.split(':')[0])
                conflicts = self.check_color_conflicts(parent_index, index)
                if conflicts:
                    msg = "\n".join([f"* Part Set {c[0]}, {c[1]}" for c in conflicts])
                    with MultiMessageDialog(self, "Cannot delete Part Color.  The following parts are still using it:",
                                            "Warning", msg, wx.OK) as dlg:
                        dlg.ShowModal()
                    return
                parent_data.colors.pop(index)
                color_db[parent_index].pop(index)
                self.delete_colors(parent_index, index)
            elif isinstance(data, Body):
                color_db.bcs.bodies.pop(index)
            elif isinstance(data, BoneScale):
                parent_data.bone_scales.pop(index)
            elif isinstance(data, Skeleton):
                color_db.bcs.skeletons.pop(index)
            elif isinstance(data, Bone):
                parent_data.bones.pop(index)

            # Finally Delete from Tree
            self.entry_list.Delete(item)

            pub.sendMessage(self.reindex_name)
            pub.sendMessage('set_status_bar', text="Deleted successfully")

    def check_color_conflicts(self, part_color_index, color_index=-1):
        conflicts = []
        for ps_idx, part_set in enumerate(color_db.bcs.part_sets):
            for part_name, part in part_set.parts.items():
                for cs_idx, color_selector in enumerate(part.color_selectors):
                    if color_selector.part_colors == part_color_index and \
                            (color_index == -1 or color_selector.color == color_index):
                        conflicts.append((ps_idx, part_name))
        return conflicts

    def delete_colors(self, part_color_index, color_index=-1):
        for ps_idx, part_set in enumerate(color_db.bcs.part_sets):
            for part_name, part in part_set.parts.items():
                for cs_idx, color_selector in enumerate(part.color_selectors):
                    # Shift just part colors
                    if color_index == -1:
                        if color_selector.part_colors >= part_color_index:
                            color_selector.part_colors -= 1
                    # Shift colors
                    else:
                        if color_selector.part_colors == part_color_index and color_selector.color >= color_index:
                            color_selector.color -= 1

    def add_part_set(self, _, append=True, entry=None, add_at_end=False):
        self.add_item(append, entry, PartSet, "part_sets", add_at_end)

    def add_part_color(self, _, append=True, entry=None, add_at_end=False):
        self.add_item(append, entry, PartColor, "part_colors", add_at_end)

    def add_body(self, _, append=True, entry=None, add_at_end=False):
        self.add_item(append, entry, Body, "bodies", add_at_end)

    def add_skeleton(self, _, append=True, entry=None, add_at_end=False):
        self.add_item(append, entry, Skeleton, "skeletons", add_at_end)

    def add_item(self, append, entry, item_type, name, add_at_end):
        if not add_at_end:
            if not entry:
                entry = self.entry_list.GetSelections()[0]
            text = self.entry_list.GetItemText(entry)
            data = self.entry_list.GetItemData(entry)
            parent = self.entry_list.GetRootItem()
            if not isinstance(data, item_type):
                return
            index = int(text.split(':')[0])
            if append:
                index += 1
        else:
            parent = self.entry_list.GetRootItem()
            index = len(getattr(color_db.bcs, name))

        # Add Part Set
        new_type = item_type()
        getattr(color_db.bcs, name).insert(index, new_type)

        # Insert into Treelist
        new_item = self.entry_list.InsertItem(parent, index, "", data=new_type)

        # Part Colors only
        if isinstance(new_type, PartColor):
            color_db.insert(index, [])

        # Reindex
        pub.sendMessage(self.reindex_name)
        return new_item, new_type

    def add_part(self, _, part_name, entry=None):
        if not entry:
            entry = self.entry_list.GetSelections()[0]
        data = self.entry_list.GetItemData(entry)
        if not isinstance(data, PartSet) and not isinstance(data, Part):
            return
        if part_name not in BCS_PART_LIST:
            return

        if isinstance(data, PartSet):
            part_set_item = entry
        else:
            part_set_item = self.entry_list.GetItemParent(entry)

        part_set = self.entry_list.GetItemData(part_set_item)
        new_name = color_db.name
        part_item, cookie = self.entry_list.GetFirstChild(part_set_item)
        if part_item.IsOk():
            first_part = self.entry_list.GetItemData(part_item)
            new_name = first_part.name

        if part_name in part_set.parts:
            return

        # Add new part
        new_part = Part()
        new_part.name = new_name
        part_set.parts[part_name] = new_part

        # Insert into Tree List
        index = BCS_PART_LIST.index(part_name)
        name = part_name.replace('_', ' ').capitalize()
        tree_index = 0
        while part_item.IsOk():
            text = self.entry_list.GetItemText(part_item)
            next_index = int(text.split(':')[0])
            if index < next_index:
                break
            part_item, cookie = self.entry_list.GetNextChild(part_set_item, cookie)
            tree_index += 1
        new_item = self.entry_list.InsertItem(part_set_item, tree_index, f"{index}: {name}", data=new_part)

        # Reindex
        pub.sendMessage("reindex_part_sets")
        return new_item, new_part

    def add_color(self, _, append, entry=None):
        self.add_sub_items(append, entry, PartColor, "part_colors", Color, "colors")

    def add_bone_scale(self, _, append, entry=None):
        self.add_sub_items(append, entry, Body, "bodies", BoneScale, "bone_scales")

    def add_bone(self, _, append, entry=None):
        self.add_sub_items(append, entry, Skeleton, "skeletons", Bone, "bones")

    def add_sub_items(self, append, entry, parent_type, parent_name, item_type, name):
        if not entry:
            entry = self.entry_list.GetSelections()[0]
        text = self.entry_list.GetItemText(entry)
        data = self.entry_list.GetItemData(entry)
        if not isinstance(data, item_type) and not isinstance(data, parent_type):
            return

        if isinstance(data, item_type) and append:
            parent = self.entry_list.GetItemParent(entry)
            parent_data = self.entry_list.GetItemData(parent)
            attr_list = getattr(parent_data, name)
            index = int(text.split(':')[0]) + 1
        elif isinstance(data, item_type) and not append:
            parent = self.entry_list.GetItemParent(entry)
            parent_data = self.entry_list.GetItemData(parent)
            attr_list = getattr(parent_data, name)
            index = int(text.split(':')[0])
        elif isinstance(data, parent_type):
            parent = entry
            parent_data = self.entry_list.GetItemData(parent)
            attr_list = getattr(parent_data, name.lower())
            index = len(attr_list)
        else:
            return

        # Add new type
        new_type = item_type()
        attr_list.insert(index, new_type)

        # Insert into Treelist
        new_item = self.entry_list.InsertItem(parent, index, "", data=new_type)

        # Colors only
        if isinstance(new_type, Color):
            bitmap = wx.Bitmap.FromRGBA(16, 16, 0, 0, 0, 255)
            image = color_db.image_list.Add(bitmap)
            parent_text = self.entry_list.GetItemText(parent)
            parent_index = int(parent_text.split(':')[0])
            color_db[parent_index].insert(index, image)
            self.entry_list.SetItemImage(new_item, image)

        # Reindex
        pub.sendMessage(self.reindex_name)
        return new_item, new_type

    def add_color_selector(self, _, append, entry=None):
        self.add_parts_item(append, entry, ColorSelector, "Color Selectors")

    def add_physics(self, _, append, entry=None):
        self.add_parts_item(append, entry, Physics, "Physics")

    def add_parts_item(self, append, entry, item_type, label):
        if not entry:
            entry = self.entry_list.GetSelections()[0]
        text = self.entry_list.GetItemText(entry)
        data = self.entry_list.GetItemData(entry)
        name = label.replace(" ", "_").lower()
        if not isinstance(data, item_type) and not isinstance(data, Part) and text != label:
            return

        if isinstance(data, item_type) and append:
            item_list = self.entry_list.GetItemParent(entry)
            part_item = self.entry_list.GetItemParent(item_list)
            part = self.entry_list.GetItemData(part_item)
            part_attr_list = getattr(part, name)
            index = int(text.split(':')[0]) + 1
        elif isinstance(data, item_type) and not append:
            item_list = self.entry_list.GetItemParent(entry)
            part_item = self.entry_list.GetItemParent(item_list)
            part = self.entry_list.GetItemData(part_item)
            part_attr_list = getattr(part, name)
            index = int(text.split(':')[0])
        elif isinstance(data, Part):
            child, cookie = self.entry_list.GetFirstChild(entry)
            item_list = None
            while child.IsOk():
                text = self.entry_list.GetItemText(child)
                if text == label:
                    item_list = child
                    break
                child, cookie = self.entry_list.GetNextChild(entry, cookie)
            if not item_list:
                if isinstance(item_type, ColorSelector):
                    item_list = self.entry_list.InsertItem(entry, 0, label)
                else:
                    item_list = self.entry_list.AppendItem(entry, label)
            part_item = self.entry_list.GetItemParent(item_list)
            part = self.entry_list.GetItemData(part_item)
            part_attr_list = getattr(part, name)
            index = len(part_attr_list)
        else:
            item_list = entry
            part_item = self.entry_list.GetItemParent(item_list)
            part = self.entry_list.GetItemData(part_item)
            part_attr_list = getattr(part, name)
            index = len(part_attr_list)

        # Add Part Set
        new_type = item_type()
        if isinstance(new_type, Physics):
            new_type.name = part.name
        part_attr_list.insert(index, new_type)

        # Insert into Treelist
        new_item = self.entry_list.InsertItem(item_list, index, "", data=new_type)

        # Reindex
        pub.sendMessage("reindex_part_sets")
        return new_item, new_type

    def on_select(self, _):
        if not self.entry_list:
            return
        selected = self.entry_list.GetSelections()
        if len(selected) != 1:
            pub.sendMessage('hide_panels')
            return
        entry = self.entry_list.GetItemData(selected[0])
        pub.sendMessage('load_entry', item=selected[0], entry=entry)

    def add_menu_items(self, menu, name, add_only=False):
        add_func = getattr(self, f"add_{name.replace(' ', '_').lower()}")
        if add_only:
            add = menu.Append(self.add_ids[name], f"Add {name}", f"Add {name} at the end")
            self.Bind(wx.EVT_MENU, partial(add_func, append=True), add)
        if not add_only:
            append = menu.Append(self.append_ids[name], f"Add {name}", f"Append {name} after")
            self.Bind(wx.EVT_MENU, partial(add_func, append=True), append)
            insert = menu.Append(self.insert_ids[name], f"Insert {name}", f"Insert {name} before")
            self.Bind(wx.EVT_MENU, partial(add_func, append=False), insert)

    def add_part_items(self, menu, part_set):
        sub_menu = wx.Menu()
        for part in BCS_PART_LIST:
            name = part.replace('_', ' ').title()
            add_part = sub_menu.Append(self.add_ids[name], f"Add {name} part", f"Add {name}")
            add_part.Enable(part not in part_set.parts)
            self.Bind(wx.EVT_MENU, partial(self.add_part, part_name=part), add_part)
        menu.AppendSubMenu(sub_menu, "Parts")

    def add_single_selection_items(self, menu, selected):
        data = self.entry_list.GetItemData(selected)
        text = self.entry_list.GetItemText(selected)
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
        elif isinstance(data, ColorSelector) or text == "Color Selectors":
            self.add_menu_items(menu, "Color Selector", data is None)
        elif isinstance(data, Physics) or text == "Physics":
            self.add_menu_items(menu, "Physics", data is None)
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

    def set_focus(self, focus):
        if type(focus.GetParent()) in (wx.SpinCtrlDouble, UnknownHexCtrl, SingleSelectionBox, MultipleSelectionBox):
            self.focus = focus.GetParent()
        elif type(focus.GetParent().GetParent()) in (SingleSelectionBox, MultipleSelectionBox):
            self.focus = focus.GetParent().GetParent()
        else:
            self.focus = focus

    def clear_focus(self):
        self.focus = None
