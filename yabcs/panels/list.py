from functools import partial
from itertools import chain
import pickle
import wx
from wx.lib.dialogs import MultiMessageDialog
import pyperclip

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

from yabcs.utils import color_db


class ListPanel(wx.Panel):
    def __init__(self, parent, name):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.focus = None
        self.name = name
        self.reindex_name = f"reindex_{name.replace(' ', '_').lower()}"

        self.entry_list = wx.TreeCtrl(self, style=wx.TR_MULTIPLE | wx.TR_HAS_BUTTONS | wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT)
        self.entry_list.Bind(wx.EVT_TREE_ITEM_MENU, self.on_right_click)
        self.entry_list.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_select)
        self.entry_list.SetDropTarget(FileDropTarget(self, "load_bcs"))
        self.cdo = None
        self.paste_data = None
        self.paste_data_type = None
        self.paste_data_actual_type = None

        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_save, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_delete, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.on_paste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.on_select_all, id=wx.ID_SELECTALL)

        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('a'), wx.ID_SELECTALL),
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

    def on_select_all(self, _):
        root = self.entry_list.GetRootItem()
        self.entry_list.SelectChildren(root)

    def get_item_type_of_item_list(self, selections):
        if not selections:
            return
        data = [self.entry_list.GetItemData(item) for item in selections]
        if not isinstance(data[0], list) and all(isinstance(d, type(data[0])) for d in data):
            return type(data[0]), type(data[0])
        elif isinstance(data[0], list) and all(isinstance(d[0], type(data[0][0])) for d in data):
            return type(data[0][0]), list

    def on_copy(self, _):
        items_to_copy = self.get_selected_root_nodes()
        if not items_to_copy:
            return
        # Check to make sure all items are the same
        data = [self.entry_list.GetItemData(item) for item in items_to_copy]
        item_type, actual_type = self.get_item_type_of_item_list(items_to_copy)
        if not item_type:
            with wx.MessageDialog(self, 'All copied items must be of the same type') as dlg:
                dlg.ShowModal()
            return

        self.cdo = wx.CustomDataObject("BCSEntry")
        self.cdo.SetData(pickle.dumps(data))
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(self.cdo)
            wx.TheClipboard.Flush()
            wx.TheClipboard.Close()

        pub.sendMessage("enable_add_copy")

        if isinstance(data[0], list):
            pub.sendMessage('set_status_bar', text=f'Copied {len(data)} {item_type.get_readable_name()} lists')
        else:
            pub.sendMessage('set_status_bar', text=f'Copied {len(data)} {item_type.get_readable_name()} items')

    def get_paste_data(self):
        cdo = wx.CustomDataObject("BCSEntry")
        success = False
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(cdo)
            wx.TheClipboard.Close()
        if not success:
            self.paste_data = []
            return
        self.paste_data = pickle.loads(cdo.GetData())
        self.paste_data_actual_type = type(self.paste_data[0])
        self.paste_data_type = type(self.paste_data[0][0]) if self.paste_data_actual_type == list else type(self.paste_data[0])

    def on_paste(self, _, use_existing=False):
        # Get Selected
        selected = self.get_selected_root_nodes()
        if not selected:
            return

        if not use_existing:
            self.get_paste_data()
        if not self.paste_data:
            return

        # Cut length to match copied
        paste_length = len(self.paste_data)
        selected_length = len(selected)
        if selected_length > paste_length:
            for item in selected[paste_length:]:
                self.entry_list.UnselectItem(item)
            selected = selected[:paste_length]

        # Make sure currently selected items are all the same length
        selected_item_type, selected_actual_type = self.get_item_type_of_item_list(selected)
        selected_data = [self.entry_list.GetItemData(item) for item in selected]
        if not selected_item_type:
            with wx.MessageDialog(self, 'All selected items must be of the same type') as dlg:
                dlg.ShowModal()
            return

        # Check currently selected to make sure it matches
        if ((not isinstance(selected_data[0], list) and not all(isinstance(d, self.paste_data_actual_type) for d in selected_data)) or
                (isinstance(selected_data[0], list) and self.paste_data_actual_type == list and
                 not all(isinstance(d[0], self.paste_data_type) for d in selected_data))):
            if isinstance(self.paste_data[0], list):
                with wx.MessageDialog(self, f'All selected items must be a {self.paste_data_type.get_readable_name()} list') as dlg:
                    dlg.ShowModal()
            else:
                with wx.MessageDialog(self, f'All selected items must be a {self.paste_data_type.get_readable_name()} item') as dlg:
                    dlg.ShowModal()
            return

        # Increase length to match selected
        if selected_length < paste_length:
            item = selected[-1]
            parent = self.entry_list.GetItemParent(item)
            for n in range(paste_length - selected_length):
                item = self.entry_list.GetNextSibling(item)
                if not item.IsOk():
                    if self.paste_data_type == Part:
                        with wx.MessageDialog(self, f'Not enough entries to paste over. Expected {paste_length} parts') as dlg:
                            dlg.ShowModal()
                            return
                    add_func = getattr(self, f"add_{self.paste_data_type.get_func_name()}")
                    items, item_datas = add_func(None, entry=parent)
                    item = items[0]
                    item_data = item_datas[0]
                else:
                    item_data = self.entry_list.GetItemData(item)
                self.entry_list.SelectItem(item)
                selected.append(item)
                selected_data.append(item_data)

        # Add to BCS first
        for item, paste in zip(selected, self.paste_data):
            data = self.entry_list.GetItemData(item)
            text = self.entry_list.GetItemText(item)
            part = None
            if self.paste_data_actual_type == list:
                parent = self.entry_list.GetItemParent(item)
                part = self.entry_list.GetItemData(parent)
                func_name = f'paste_{self.paste_data_type.get_func_name()}'
                if not func_name.endswith('s'):
                    func_name += 's'
                getattr(part, func_name)(paste, False)
            else:
                data.paste(paste)

            # Delete children and add new ones
            self.entry_list.DeleteChildren(item)
            if self.paste_data_type == PartSet:
                pub.sendMessage('load_parts', root=item, part_set=data, single=True)
            elif self.paste_data_type == Part:
                pub.sendMessage('load_color_selectors', root=item, part=data, single=True)
                pub.sendMessage('load_physics', root=item, part=data)
            elif self.paste_data_actual_type == list and self.paste_data_type == ColorSelector:
                pub.sendMessage('load_color_selectors', root=None, part=part, color_selector_entry=item, single=True)
            elif self.paste_data_actual_type == list and self.paste_data_type == Physics:
                pub.sendMessage('load_physics', root=None, part=part, physics_entry=item)
            elif self.paste_data_type == PartColor:
                color_set = []
                index = int(text.split(':')[0])
                pub.sendMessage('load_colors', root=item, part_color=data, color_set=color_set)
                color_db[index] = color_set
            elif self.paste_data_type == Body:
                pub.sendMessage('load_bone_scales', root=item, body=data)
            elif self.paste_data_type == Skeleton:
                pub.sendMessage('load_bones', root=item, skeleton=data)

        # Reindex
        self.on_select(None)
        pub.sendMessage(self.reindex_name)

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
            conflicts = []
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
            elif isinstance(data, Part):
                name = text.split(':')[1].strip().replace(' ', '_').lower()
                parent_data.parts.pop(name)
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
                    msg = "\n".join([f"* Part Set {c[0]}, {c[1]}" for c in conflicts])
                    with MultiMessageDialog(self, f"Cannot delete Part Color {index}."
                                            "The following parts are still using it:",
                                            "Warning", msg, wx.OK) as dlg:
                        dlg.ShowModal()
                else:
                    color_db.bcs.part_colors.pop(index)
                    color_db.pop(index)
                    self.adjust_colors(index, delete=True)
            elif isinstance(data, Color):
                parent_text = self.entry_list.GetItemText(parent)
                parent_index = int(parent_text.split(':')[0])
                conflicts = self.check_color_conflicts(parent_index, index)
                if conflicts:
                    msg = "\n".join([f"* Part Set {c[0]}, {c[1]}" for c in conflicts])
                    with MultiMessageDialog(self, f"Cannot delete Part Color {parent_index}, Color {index}."
                                            "The following parts are still using it:",
                                            "Warning", msg, wx.OK) as dlg:
                        dlg.ShowModal()
                else:
                    parent_data.colors.pop(index)
                    color_db[parent_index].pop(index)
                    self.adjust_colors(parent_index, index, delete=True)
            elif isinstance(data, Body):
                color_db.bcs.bodies.pop(index)
            elif isinstance(data, BoneScale):
                parent_data.bone_scales.pop(index)
            elif isinstance(data, Skeleton):
                color_db.bcs.skeletons.pop(index)
            elif isinstance(data, Bone):
                parent_data.bones.pop(index)

            # Finally Delete from Tree
            if not conflicts:
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

    def adjust_colors(self, part_color_index, color_index=-1, delete=False):
        modifier = -1 if delete else 1
        for ps_idx, part_set in enumerate(color_db.bcs.part_sets):
            for part_name, part in part_set.parts.items():
                for cs_idx, color_selector in enumerate(part.color_selectors):
                    # Shift just part colors
                    if color_index == -1:
                        if color_selector.part_colors >= part_color_index:
                            color_selector.part_colors += modifier
                    # Shift colors
                    else:
                        if color_selector.part_colors == part_color_index and color_selector.color >= color_index:
                            color_selector.color += modifier

    def select_items(self, items):
        self.entry_list.UnselectAll()
        if not items:
            return
        for item in items:
            self.expand_parents(item)
            self.entry_list.SelectItem(item)

        if not self.entry_list.IsVisible(items[-1]):
            self.entry_list.ScrollTo(items[-1])

    def add_part_set(self, _, append=True, entry=None, add_at_end=False, skip_reindex=False, paste=False):
        return self.add_item(append, entry, PartSet, "part_sets", add_at_end, skip_reindex, paste)

    def add_part_color(self, _, append=True, entry=None, add_at_end=False, skip_reindex=False, paste=False):
        return self.add_item(append, entry, PartColor, "part_colors", add_at_end, skip_reindex, paste)

    def add_body(self, _, append=True, entry=None, add_at_end=False, skip_reindex=False, paste=False):
        return self.add_item(append, entry, Body, "bodies", add_at_end, skip_reindex, paste)

    def add_skeleton(self, _, append=True, entry=None, add_at_end=False, skip_reindex=False, paste=False):
        return self.add_item(append, entry, Skeleton, "skeletons", add_at_end, skip_reindex, paste)

    def add_item(self, append, entry, item_type, name, add_at_end, skip_reindex, paste):
        label = item_type.get_readable_name()
        if paste:
            self.get_paste_data()
        if paste and not item_type == self.paste_data_type:
            return
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

        num_entries = 1
        if paste:
            num_entries = len(self.paste_data)

        new_items = []
        new_types = []
        for n in range(num_entries):
            # Add Part Set
            new_type = item_type()
            getattr(color_db.bcs, name).insert(index, new_type)
            new_types.append(new_type)

            # Insert into Treelist
            new_items.append(self.entry_list.InsertItem(parent, index, "", data=new_type))

            # Part Colors only
            if isinstance(new_type, PartColor):
                color_db.insert(index, [])
                self.adjust_colors(index)

        self.select_items(new_items)

        # Reindex
        if not skip_reindex:
            pub.sendMessage(self.reindex_name)
            pub.sendMessage("set_status_bar", text=f"Added {label} successfully")

        if paste:
            self.on_paste(None, use_existing=True)
        return new_items, new_types

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
        new_item = self.entry_list.InsertItem(part_set_item, index, f"{index}: {name}", data=new_part)
        self.select_items([new_item])

        # Reindex
        pub.sendMessage("reindex_part_sets")
        return new_item, new_part

    def add_color(self, _, append=True, entry=None, skip_reindex=False, paste=False):
        return self.add_sub_items(append, entry, PartColor, Color, skip_reindex, paste)

    def add_bone_scale(self, _, append=True, entry=None, skip_reindex=False, paste=False):
        return self.add_sub_items(append, entry, Body, BoneScale, skip_reindex, paste)

    def add_bone(self, _, append=True, entry=None, skip_reindex=False, paste=False):
        return self.add_sub_items(append, entry, Skeleton, Bone, skip_reindex, paste)

    def add_sub_items(self, append, entry, parent_type, item_type, skip_reindex, paste):
        name = f'{item_type.get_func_name()}s'
        label = f'{item_type.get_func_name()}'
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
            attr_list = getattr(parent_data, name)
            index = len(attr_list)
        else:
            return

        num_entries = 1
        if paste:
            num_entries = len(self.paste_data)

        new_items = []
        new_types = []
        for n in range(num_entries):
            # Add new type
            new_type = item_type()
            attr_list.insert(index, new_type)
            new_types.append(new_type)

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
                self.adjust_colors(parent_index, index)
            new_items.append(new_item)

        self.select_items(new_items)

        # Reindex
        if not skip_reindex:
            pub.sendMessage(self.reindex_name)
            pub.sendMessage("set_status_bar", text=f"Added {label} successfully")

        if paste:
            self.on_paste(None, use_existing=True)
        return new_items, new_types

    def add_color_selector(self, _, append=True, entry=None, skip_reindex=False, paste=False):
        return self.add_parts_item(append, entry, ColorSelector, skip_reindex, paste)

    def add_physics(self, _, append=True, entry=None, skip_reindex=False, paste=False):
        return self.add_parts_item(append, entry, Physics, skip_reindex, paste)

    def add_parts_item(self, append, entry, item_type, skip_reindex, paste):
        if paste and self.paste_data_actual_type == list and len(self.paste_data) > 1:
            with wx.MessageDialog(self, f"Can only add copies of 1 {item_type} list at a time", "Error") as dlg:
                dlg.ShowModal()
            return
        name = item_type.get_func_name()
        label = item_type.get_readable_name()

        if not name.endswith('s'):
            name += "s"
        if not label.endswith('s'):
            label += "s"
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
            item_index = 0
            entry_index = 0
            while child.IsOk():
                text = self.entry_list.GetItemText(child)
                if text == label:
                    item_list = child
                    break
                child, cookie = self.entry_list.GetNextChild(entry, cookie)
                item_index += 1
                if label > text:
                    entry_index = item_index
            if not item_list:
                part_attr_list = getattr(data, name)
                item_list = self.entry_list.InsertItem(entry, entry_index, label, data=part_attr_list)
            else:
                part_attr_list = self.entry_list.GetItemData(item_list)
            index = len(part_attr_list)
        else:
            item_list = entry
            part_attr_list = self.entry_list.GetItemData(item_list)
            index = len(part_attr_list)

        num_entries = 1
        if paste:
            self.paste_data = self.paste_data[0]
            self.paste_data_actual_type = self.paste_data_type
            num_entries = len(self.paste_data)

        new_items = []
        new_types = []
        for n in range(num_entries):
            # Get Part
            part_item = self.entry_list.GetItemParent(item_list)
            part = self.entry_list.GetItemData(part_item)

            # Add Part Set
            new_type = item_type()
            if isinstance(new_type, Physics):
                new_type.name = part.name
            elif isinstance(new_type, ColorSelector):
                for i, part_color in enumerate(color_db):
                    if part_color:
                        new_type.part_colors = i
                        break
            part_attr_list.insert(index, new_type)
            new_types.append(new_type)

            # Insert into Treelist
            new_items.append(self.entry_list.InsertItem(item_list, index, "", data=new_type))

        self.select_items(new_items)

        # Reindex
        if not skip_reindex:
            pub.sendMessage("reindex_part_sets")
            pub.sendMessage("set_status_bar", text=f"Added {label} successfully")
        if paste:
            self.on_paste(None, use_existing=True)
        return new_items, new_types

    def on_select(self, _):
        if not self.entry_list:
            return
        selected = self.entry_list.GetSelections()
        if len(selected) != 1:
            pub.sendMessage('hide_panels')
            return
        entry = self.entry_list.GetItemData(selected[0])
        pub.sendMessage('load_entry', item=selected[0], entry=entry)

    def add_menu_items(self, menu, item_type, add_only=False):
        add_func = getattr(self, f"add_{item_type.get_func_name()}")
        name = item_type.get_readable_name()
        valid = (self.paste_data_type == item_type)
        valid_colors = name != "Color Selector" or len(list(chain.from_iterable(color_db))) > 0

        append = menu.Append(-1, f"Add {name}", f"Add {name} after")
        append.Enable(valid_colors)
        self.Bind(wx.EVT_MENU, partial(add_func, append=True), append)
        if not add_only:
            insert = menu.Append(-1, f"Insert {name}", f"Insert {name} before")
            insert.Enable(valid_colors)
            self.Bind(wx.EVT_MENU, partial(add_func, append=False), insert)
        menu.AppendSeparator()
        append_copy = menu.Append(-1, f"Add {name} Copy", f"Add {name} copy after")
        append_copy.Enable(valid and valid_colors)
        self.Bind(wx.EVT_MENU, partial(add_func, append=True, paste=True), append_copy)
        if not add_only:
            insert_copy = menu.Append(-1, f"Insert {name} Copy", f"Insert {name} copy before")
            insert_copy.Enable(valid and valid_colors)
            self.Bind(wx.EVT_MENU, partial(add_func, append=False, paste=True), insert_copy)

    def add_menu_parts_items(self, menu, part_set):
        sub_menu = wx.Menu()
        for part in BCS_PART_LIST:
            name = part.replace('_', ' ').title()
            add_part = sub_menu.Append(-1, f"Add {name} part", f"Add {name}")
            add_part.Enable(part not in part_set.parts)
            self.Bind(wx.EVT_MENU, partial(self.add_part, part_name=part), add_part)
        menu.AppendSubMenu(sub_menu, "Parts")

    def add_single_selection_items(self, menu, selected):
        data = self.entry_list.GetItemData(selected)
        text = self.entry_list.GetItemText(selected)
        if isinstance(data, PartSet):
            self.add_menu_items(menu, PartSet)
            menu.AppendSeparator()
            self.add_menu_parts_items(menu, data)
            menu.AppendSeparator()
            xml = menu.Append(-1, "Generate part set xml")
            self.Bind(wx.EVT_MENU, partial(self.generate_xml, part_set=data), xml)
        elif isinstance(data, Part):
            part_set_item = self.entry_list.GetItemParent(selected)
            part_set = self.entry_list.GetItemData(part_set_item)
            self.add_menu_parts_items(menu, part_set)
            menu.AppendSeparator()
            self.add_menu_items(menu, ColorSelector, add_only=True)
            menu.AppendSeparator()
            self.add_menu_items(menu, Physics, add_only=True)
        elif isinstance(data, ColorSelector) or text == "Color Selectors":
            self.add_menu_items(menu, ColorSelector, add_only=isinstance(data, list))
        elif isinstance(data, Physics) or text == "Physics":
            self.add_menu_items(menu, Physics, add_only=isinstance(data, list))
        elif isinstance(data, PartColor):
            self.add_menu_items(menu, PartColor)
            menu.AppendSeparator()
            self.add_menu_items(menu, Color)
        elif isinstance(data, Color):
            self.add_menu_items(menu, Color)
        elif isinstance(data, Body):
            self.add_menu_items(menu, Body)
            menu.AppendSeparator()
            self.add_menu_items(menu, BoneScale)
        elif isinstance(data, BoneScale):
            self.add_menu_items(menu, BoneScale)
        elif isinstance(data, Skeleton):
            self.add_menu_items(menu, Skeleton)
            menu.AppendSeparator()
            self.add_menu_items(menu, Bone)
        elif isinstance(data, Bone):
            self.add_menu_items(menu, Bone)

    def on_right_click(self, _):
        selections = self.entry_list.GetSelections()
        if not selections:
            return
        selected_item_type, selected_actual_type = self.get_item_type_of_item_list(selections)
        menu = wx.Menu()
        self.get_paste_data()
        if len(selections) == 1:
            self.add_single_selection_items(menu, selections[0])
            menu.AppendSeparator()

        menu.Append(wx.ID_COPY, "&Copy\tCtrl+C", "Copy entry")
        paste = menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V", "Paste entry")
        menu.Append(wx.ID_DELETE, "&Delete\tDelete", "Delete selected items")

        valid = (self.paste_data_type == selected_item_type and self.paste_data_actual_type == selected_actual_type)
        paste.Enable(valid)
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

    def generate_xml(self, _, part_set):
        xml = part_set.generate_xml(color_db.bcs.part_colors)
        pyperclip.copy(xml)
        with MultiMessageDialog(self, "The generated XML has been copied to the clipboard", "Info", xml, wx.OK) as dlg:
            dlg.ShowModal()
