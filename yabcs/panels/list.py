from collections import defaultdict
from functools import partial
import pickle
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
        self.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.on_paste, id=wx.ID_PASTE)

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

    def on_copy(self, _):
        items_to_copy = self.get_selected_root_nodes()
        if not items_to_copy:
            return
        # Check to make sure all items are the same
        data = [self.entry_list.GetItemData(item) for item in items_to_copy]
        if ((not isinstance(data[0], list) and not all(isinstance(d, type(data[0])) for d in data)) or
                (isinstance(data[0], list) and not all(isinstance(d[0], type(data[0][0])) for d in data))):
            with wx.MessageDialog(self, 'All copied items must be of the same type') as dlg:
                dlg.ShowModal()
            return

        self.cdo = wx.CustomDataObject('BCS')
        self.cdo.SetData(pickle.dumps(data))
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.cdo)
            wx.TheClipboard.Flush()
            wx.TheClipboard.Close()

        if isinstance(data[0], list):
            item_type = data[0][0].get_readable_name()
            pub.sendMessage('set_status_bar', text=f'Copied {len(data)} {item_type} lists')
        else:
            item_type = data[0].get_readable_name()
            pub.sendMessage('set_status_bar', text=f'Copied {len(data)} {item_type} items')

    def get_paste_data(self):
        cdo = wx.CustomDataObject('BCS')
        success = False
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(cdo)
            wx.TheClipboard.Close()
        if not success:
            return []
        return pickle.loads(cdo.GetData())

    def on_paste(self, _):
        # Get Selected
        selected = self.get_selected_root_nodes()
        if not selected:
            return
        data = [self.entry_list.GetItemData(item) for item in selected]

        if ((not isinstance(data[0], list) and not all(isinstance(d, type(data[0])) for d in data)) or
                (isinstance(data[0], list) and not all(isinstance(d[0], type(data[0][0])) for d in data))):
            with wx.MessageDialog(self, 'All selected items must be of the same type') as dlg:
                dlg.ShowModal()
            return

        paste_data = self.get_paste_data()
        if not paste_data:
            return

        if ((not isinstance(data[0], list) and not all(isinstance(d, type(paste_data[0])) for d in data)) or
                (isinstance(data[0], list) and isinstance(paste_data[0], list) and
                 not all(isinstance(d[0], type(paste_data[0][0])) for d in data))):
            if isinstance(paste_data[0], list):
                item_type = paste_data[0][0].get_readable_name()
                with wx.MessageDialog(self, f'All selected items must be a {item_type} list') as dlg:
                    dlg.ShowModal()
            else:
                item_type = paste_data[0].get_readable_name()
                with wx.MessageDialog(self, f'All selected items must be a {item_type} item') as dlg:
                    dlg.ShowModal()
            return

        # data = self.entry_list.GetItemData(item)
        # text = self.entry_list.GetItemText(item)

        # # Add it to BCS first
        # if isinstance(paste_data, list):
        #     if isinstance(paste_data[0], Physics) and (isinstance(data, Part) or text == "Physics"):
        #         if not data:
        #             parent =

        #     elif isinstance(paste_data[0], ColorSelector) and (isinstance(data, Part) or text == "Color Selectors"):
        #         pass
        #     else:
        #         with wx.MessageDialog(self, f"Unable to paste '{paste_data[0].get_readable_name()}' list "
        #                               f"onto '{text}'") as dlg:
        #             dlg.ShowModal()
        #     return
        # elif type(paste_data) == type(data):
        #     data.paste(paste_data)
        # else:
        #     with wx.MessageDialog(self, f"Unable to paste '{paste_data.get_readable_name()}' type "
        #                           f"onto '{text}'") as dlg:
        #         dlg.ShowModal()
        #     return

        # Now add it to the tree list

    def on_delete(self, _):
        items_to_delete = self.get_selected_root_nodes()
        if not items_to_delete:
            return

        for item in reversed(items_to_delete):
            data = self.entry_list.GetItemData(item)
            text = self.entry_list.GetItemText(item)
            parent = self.entry_list.GetItemParent(item)
            parent_data = self.entry_list.GetItemData(parent)
            index = -1
            # Get Index
            if not isinstance(data, list):
                index = int(text.split(':')[0])

            # Delete from BCS
            if isinstance(data, list) and isinstance(data[0], Physics):
                parent_data.physics.clear()
            elif isinstance(data, list) and isinstance(data[0], ColorSelector):
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

    def expand_parents(self, item):
        root = self.entry_list.GetRootItem()
        parent = self.entry_list.GetItemParent(item)
        while parent != root:
            self.entry_list.Expand(parent)
            parent = self.entry_list.GetItemParent(parent)

    def get_selected_root_nodes(self):
        selected = self.entry_list.GetSelections()
        if not selected:
            return []
        root = self.entry_list.GetRootItem()

        nodes = []
        for item in selected:
            parent = self.entry_list.GetItemParent(item)
            while parent != root and parent.IsOk():
                if parent in selected:
                    break
                parent = self.entry_list.GetItemParent(parent)
            if parent == root:
                nodes.append(item)
        return nodes

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
        new_item = self.add_new_list_item(parent, index, new_type)

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
        new_item = self.add_new_list_item(part_set_item, index, new_part, label=f"{index}: {name}")

        # Reindex
        pub.sendMessage("reindex_part_sets")
        return new_item, new_part

    def add_color(self, _, append, entry=None):
        self.add_sub_items(append, entry, PartColor, Color, "colors")

    def add_bone_scale(self, _, append, entry=None):
        self.add_sub_items(append, entry, Body, BoneScale, "bone_scales")

    def add_bone(self, _, append, entry=None):
        self.add_sub_items(append, entry, Skeleton, Bone, "bones")

    def add_sub_items(self, append, entry, parent_type, item_type, name):
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
        new_item = self.add_new_list_item(parent, index, new_type)

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
        if not isinstance(data, item_type) and not isinstance(data, Part) and text != label:
            return

        if isinstance(data, item_type) and append:
            item_list = self.entry_list.GetItemParent(entry)
            part_attr_list = self.entry_list.GetItemData(item_list)
            index = int(text.split(':')[0]) + 1
        elif isinstance(data, item_type) and not append:
            item_list = self.entry_list.GetItemParent(entry)
            part_attr_list = self.entry_list.GetItemData(item_list)
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
                if item_type == ColorSelector:
                    item_list = self.entry_list.InsertItem(entry, 0, label, data=data.color_selectors)
                    part_attr_list = data.color_selectors
                    print("Color")
                else:
                    item_list = self.entry_list.AppendItem(entry, label, data=data.physics)
                    part_attr_list = data.physics
                    print("Physics")
            else:
                part_attr_list = self.entry_list.GetItemData(item_list)
            print(part_attr_list)
            index = len(part_attr_list)
        else:
            item_list = entry
            part_attr_list = self.entry_list.GetItemData(item_list)
            index = len(part_attr_list)

        # Get Part
        part_item = self.entry_list.GetItemParent(item_list)
        part = self.entry_list.GetItemData(part_item)

        # Add Part Set
        new_type = item_type()
        if isinstance(new_type, Physics):
            new_type.name = part.name
        part_attr_list.insert(index, new_type)

        # Insert into Treelist
        new_item = self.add_new_list_item(item_list, index, new_type)

        # Reindex
        pub.sendMessage("reindex_part_sets")
        pub.sendMessage("set_status_bar", text=f"Added {label} successfully")
        return new_item, new_type

    def add_new_list_item(self, item, index, data, label=""):
        new_item = self.entry_list.InsertItem(item, index, label, data=data)
        self.entry_list.UnselectAll()
        self.expand_parents(new_item)
        self.entry_list.SelectItem(new_item)
        if not self.entry_list.IsVisible(new_item):
            self.entry_list.ScrollTo(new_item)
        return new_item

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
        append = menu.Append(self.append_ids[name], f"Add {name}", f"Add {name} after")
        self.Bind(wx.EVT_MENU, partial(add_func, append=True), append)
        if not add_only:
            insert = menu.Append(self.insert_ids[name], f"Insert {name}", f"Insert {name} before")
            self.Bind(wx.EVT_MENU, partial(add_func, append=False), insert)

    def add_menu_parts_items(self, menu, part_set):
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
            self.add_menu_parts_items(menu, data)
        elif isinstance(data, Part):
            part_set_item = self.entry_list.GetItemParent(selected)
            part_set = self.entry_list.GetItemData(part_set_item)
            self.add_menu_parts_items(menu, part_set)
            menu.AppendSeparator()
            self.add_menu_items(menu, "Color Selector", add_only=True)
            menu.AppendSeparator()
            self.add_menu_items(menu, "Physics", add_only=True)
        elif isinstance(data, ColorSelector) or text == "Color Selectors":
            self.add_menu_items(menu, "Color Selector", add_only=isinstance(data, list))
        elif isinstance(data, Physics) or text == "Physics":
            self.add_menu_items(menu, "Physics", add_only=isinstance(data, list))
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
        menu.AppendSeparator()

        # copy = menu.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy entry")
        # paste = menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste entry")
        menu.Append(wx.ID_DELETE, "&Delete\tDelete", "Delete selected items")
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
