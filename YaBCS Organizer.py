#!/usr/local/bin/python3.6
from functools import partial
import os
import pickle
import sys
import traceback

from pubsub import pub
import wx
from wx.lib.dialogs import ScrolledMessageDialog
from wx.lib.agw.hyperlink import HyperLinkCtrl
from wx.lib.dialogs import MultiMessageDialog

from pyxenoverse.bcs import BCS
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
from pyxenoverse.gui import create_backup
from yabcs.utils import color_db
from yabcs.panels.main import MainPanel
from yabcs.panels.side import SidePanel
from yabcs.dlg.find import FindDialog
from yabcs.dlg.replace import ReplaceDialog
from pyxenoverse.gui import get_next_item
from pyxenoverse.gui.file_drop_target import FileDropTarget

VERSION = '0.1.7'


class MainWindow(wx.Frame):
    def __init__(self, parent, title, dirname, filename):
        sys.excepthook = self.exception_hook
        self.dirname = ''
        self.bcs = None
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)

        # A "-1" in the size parameter instructs wxWidgets to use the default size.
        # In this case, we select 200px width and the default height.
        wx.Frame.__init__(self, parent, title=title, size=(1300, 900))
        self.statusbar = self.CreateStatusBar()  # A Statusbar in the bottom of the window

        # Panels
        self.main_panel = MainPanel(self)
        self.side_panel = SidePanel(self)

        # Setting up the menu.
        file_menu= wx.Menu()
        file_menu.Append(wx.ID_OPEN)
        file_menu.Append(wx.ID_SAVE)
        file_menu.Append(wx.ID_ABOUT)
        file_menu.Append(wx.ID_EXIT)

        edit_menu = wx.Menu()
        edit_menu.Append(wx.ID_FIND)
        edit_menu.Append(wx.ID_REPLACE)

        # Creating the menubar.
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")  # Adding the "filemenu" to the MenuBar
        menu_bar.Append(edit_menu, "&Edit")
        self.SetMenuBar(menu_bar)  # Adding the MenuBar to the Frame content.

        # Publisher
        pub.subscribe(self.open_bcs, 'open_bcs')
        pub.subscribe(self.load_bcs, 'load_bcs')
        pub.subscribe(self.save_bcs, 'save_bcs')
        pub.subscribe(self.load_part_sets, 'load_part_sets')
        pub.subscribe(self.load_parts, 'load_parts')
        pub.subscribe(self.load_color_selectors, 'load_color_selectors')
        pub.subscribe(self.load_physics, 'load_physics')
        pub.subscribe(self.load_part_colors, 'load_part_colors')
        pub.subscribe(self.load_colors, 'load_colors')
        pub.subscribe(self.load_bodies, 'load_bodies')
        pub.subscribe(self.load_bone_scales, 'load_bone_scales')
        pub.subscribe(self.load_skeletons, 'load_skeletons')
        pub.subscribe(self.load_bones, 'load_bones')
        pub.subscribe(self.set_status_bar, 'set_status_bar')
        pub.subscribe(self.reindex_part_sets, 'reindex_part_sets')
        pub.subscribe(self.reindex_part_colors, 'reindex_part_colors')
        pub.subscribe(self.reindex_bodies, 'reindex_bodies')
        pub.subscribe(self.reindex_skeletons, 'reindex_skeletons')
        pub.subscribe(self.change_add_text, 'change_add_text')
        pub.subscribe(self.enable_add_copy, 'enable_add_copy')

        # Events.
        self.Bind(wx.EVT_MENU, self.open_bcs, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.save_bcs, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.on_find, id=wx.ID_FIND)
        self.Bind(wx.EVT_MENU, self.on_replace, id=wx.ID_REPLACE)
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.on_exit, id=wx.ID_EXIT)
        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('o'), wx.ID_OPEN),
            (wx.ACCEL_CTRL, ord('s'), wx.ID_SAVE),
            (wx.ACCEL_CTRL, ord('f'), wx.ID_FIND),
            (wx.ACCEL_CTRL, ord('h'), wx.ID_REPLACE),
        ])
        self.SetAcceleratorTable(accelerator_table)
        self.SetDropTarget(FileDropTarget(self, "load_bcs"))

        # Name
        self.name = wx.StaticText(self, -1, '(No file loaded)')
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.name.SetFont(font)

        # Buttons
        open_button = wx.Button(self, wx.ID_OPEN, "Load", size=(80, -1))
        open_button.Bind(wx.EVT_BUTTON, self.open_bcs)

        self.save_button = wx.Button(self, wx.ID_SAVE, "Save", size=(80, -1))
        self.save_button.Disable()
        self.save_button.Bind(wx.EVT_BUTTON, self.save_bcs)

        self.add_button = wx.Button(self, wx.ID_ADD, "Add Part Set", size=(100, -1))
        self.add_button.Disable()
        self.add_button.Bind(wx.EVT_BUTTON, self.on_add)

        self.add_copy_button = wx.Button(self, wx.ID_ADD, "Add Part Set Copy", size=(120, -1))
        self.add_copy_button.Disable()
        self.add_copy_button.Bind(wx.EVT_BUTTON, partial(self.on_add, paste=True))

        hyperlink = HyperLinkCtrl(self, -1, "What do all these things mean?",
                                  URL="https://docs.google.com/document/d/"
                                      "1df8_Zs3g0YindDNees_CSrWVpMBtwWGrFf2FE8JruUk/edit?usp=sharing")

        # Race/Gender
        self.gender = wx.ComboBox(self, choices=["Male", "Female"], style=wx.CB_READONLY, size=(80, -1))
        self.gender.Disable()

        self.race = wx.ComboBox(self, choices=["Human", "Saiyan", "Namekian", "Frieza", "Majin", "Android (?)"],
                                style=wx.CB_READONLY, size=(80, -1))
        self.race.Disable()

        # Sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer()
        button_sizer.Add(open_button, 0, wx.LEFT, 10)
        button_sizer.Add(self.save_button, 0, wx.LEFT, 10)
        button_sizer.Add(self.add_button, 0, wx.LEFT, 10)
        button_sizer.Add(self.add_copy_button, 0, wx.LEFT, 10)
        button_sizer.Add(hyperlink, 0, wx.LEFT | wx.BOTTOM, 10)

        header_sizer = wx.BoxSizer()
        header_sizer.Add(self.gender, 0, wx.LEFT, 10)
        header_sizer.Add(self.race, 0, wx.LEFT, 10)

        panel_sizer = wx.BoxSizer()
        panel_sizer.Add(self.main_panel, 1, wx.ALL | wx.EXPAND)
        panel_sizer.Add(self.side_panel, 2, wx.ALL | wx.EXPAND)

        sizer.Add(self.name, 0, wx.CENTER)
        sizer.Add(button_sizer, 0, wx.ALL)
        sizer.Add(header_sizer, 0, wx.TOP, 10)
        sizer.Add(panel_sizer, 1, wx.ALL | wx.EXPAND)

        self.SetBackgroundColour('white')
        self.SetSizer(sizer)
        self.SetAutoLayout(1)

        # Lists
        self.part_set_list = self.main_panel.pages["Part Sets"].entry_list
        self.part_color_list = self.main_panel.pages["Part Colors"].entry_list
        self.body_list = self.main_panel.pages["Bodies"].entry_list
        self.skeleton_list = self.main_panel.pages["Skeletons"].entry_list

        color_db.image_list = wx.ImageList(16, 16)
        self.part_set_list.SetImageList(color_db.image_list)
        self.part_color_list.SetImageList(color_db.image_list)

        # Dialogs
        self.find = FindDialog(self, self.main_panel)
        self.replace = ReplaceDialog(self, self.main_panel)

        sizer.Layout()
        self.Show()

        if filename:
            self.load_bcs(dirname, filename)

    def exception_hook(self, etype, value, trace):
        dlg = ScrolledMessageDialog(self, ''.join(traceback.format_exception(etype, value, trace)), "Error")
        dlg.ShowModal()
        dlg.Destroy()

    def on_about(self, _):
        # Create a message dialog box
        dlg = wx.MessageDialog(self, f"Yet Another BCS Organizer v{VERSION} by Kyonko Yuuki",
                               "About BCS Organizer", wx.OK)
        dlg.ShowModal()  # Shows it
        dlg.Destroy()  # finally destroy it when finished.

    def on_exit(self, _):
        self.Disable()
        self.Close(True)  # Close the frame.

    def set_status_bar(self, text):
        self.statusbar.SetStatusText(text)

    def open_bcs(self, e):
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.bcs", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.load_bcs(dlg.GetDirectory(), dlg.GetFilename())
        dlg.Destroy()

    def load_bcs(self, dirname, filename):
        self.dirname = dirname
        path = os.path.join(self.dirname, filename)
        self.statusbar.SetStatusText("Loading...")
        new_bcs = BCS()
        if not new_bcs.load(path):
            dlg = wx.MessageDialog(self, f"{filename} is not a valid BCS", "Warning")
            dlg.ShowModal()
            dlg.Destroy()
            return
        self.bcs = color_db.bcs = new_bcs
        color_db.name = filename[:3]
        self.add_button.Enable()
        self.enable_add_copy()
        self.save_button.Enable()
        self.gender.Enable()
        self.race.Enable()
        pub.sendMessage('hide_panels')

        self.gender.SetSelection(self.bcs.header.gender)
        self.race.SetSelection(self.bcs.header.race)
        self.load_part_colors()  # Need to load this first
        self.load_part_sets()
        self.load_bodies()
        self.load_skeletons()

        self.name.SetLabel(filename)
        self.main_panel.Layout()
        self.statusbar.SetStatusText(f"Loaded {path}")

    def show_invalid_colors(self, invalid_colors):
        if not invalid_colors:
            return
        msg = "\n".join(f" * Part Color ({c.part_colors}, {c.color})"
                        for c in sorted(invalid_colors, key=lambda x: (x.part_colors, x.color)))
        with MultiMessageDialog(self, 'Some color selectors were not added because they referenced invalid Part Colors',
                                'Warning', msg, wx.OK) as dlg:
            dlg.ShowModal()

    def load_part_sets(self):
        self.part_set_list.DeleteAllItems()
        self.part_set_list.Refresh()
        self.part_set_list.AddRoot("Parts")
        invalid_colors = set()
        for i, part_set in enumerate(self.bcs.part_sets):
            part_set_entry = self.part_set_list.AppendItem(
                self.part_set_list.GetRootItem(), f"{i}: Part Set", data=part_set)
            invalid_colors.update(self.load_parts(part_set_entry, part_set))
        self.show_invalid_colors(invalid_colors)

    def load_parts(self, root, part_set, single=False):
        invalid_colors = set()
        for i, part_name in enumerate(BCS_PART_LIST):
            if not part_set or part_name not in part_set.parts:
                continue
            part = part_set.parts[part_name]
            part_entry = self.part_set_list.AppendItem(root, f"{i}: {part_name.replace('_', ' ').title()}", data=part)
            invalid_colors.update(self.load_color_selectors(part_entry, part))
            self.load_physics(part_entry, part)
        if single:
            self.show_invalid_colors(invalid_colors)
        return invalid_colors

    def load_color_selectors(self, root, part, color_selector_entry=None, single=False):
        if not part.color_selectors:
            return []
        invalid_colors = set()
        for i, color_selector in enumerate(part.color_selectors):
            try:
                name = self.bcs.part_colors[color_selector.part_colors].name
                image = color_db[color_selector.part_colors][color_selector.color]
                if not color_selector_entry:
                    color_selector_entry = self.part_set_list.AppendItem(root, "Color Selectors",
                                                                         data=part.color_selectors)
                item = self.part_set_list.AppendItem(
                    color_selector_entry, f"{i}: {name}, {color_selector.color}", data=color_selector)
                self.part_set_list.SetItemImage(item, image)
            except IndexError:
                invalid_colors.add(color_selector)
        if single:
            self.show_invalid_colors(invalid_colors)
        return invalid_colors

    def load_physics(self, root, part, physics_entry=None):
        if not part.physics:
            return
        if not physics_entry:
            physics_entry = self.part_set_list.AppendItem(root, "Physics", data=part.physics)
        for i, physics in enumerate(part.physics):
            self.part_set_list.AppendItem(physics_entry, f"{i}", data=physics)

    def load_part_colors(self):
        self.part_color_list.DeleteAllItems()
        self.part_color_list.Refresh()
        self.part_color_list.AddRoot("Part Colors")
        color_db.clear()
        color_db.image_list.RemoveAll()
        for i, part_color in enumerate(self.bcs.part_colors):
            color_set = []
            color_set_entry = self.part_color_list.AppendItem(
                self.part_color_list.GetRootItem(), f"{i}: {part_color.name}", data=part_color)
            self.load_colors(color_set_entry, part_color, color_set)
            color_db.append(color_set)

    def load_colors(self, root, part_color, color_set):
        if not part_color:
            return
        for i, color in enumerate(part_color.colors):
            # Hack, as eye_ uses Color4
            if part_color.name == "eye_":
                bitmap = wx.Bitmap.FromRGBA(16, 16, *color.color4[:3], 255)
            else:
                bitmap = wx.Bitmap.FromRGBA(16, 16, *color.color1[:3], 255)
            image = color_db.image_list.Add(bitmap)
            color_set.append(image)
            color_item = self.part_color_list.AppendItem(root, f"{i}", data=color)
            self.part_color_list.SetItemImage(color_item, image)

    def load_bodies(self):
        self.body_list.DeleteAllItems()
        self.body_list.Refresh()
        self.body_list.AddRoot("Bodies")
        for i, body in enumerate(self.bcs.bodies):
            body_entry = self.body_list.AppendItem(
                self.body_list.GetRootItem(), f"{i}: Body", data=body)
            self.load_bone_scales(body_entry, body)

    def load_bone_scales(self, root, body):
        if not body:
            return
        for i, bone_scale in enumerate(body.bone_scales):
            self.body_list.AppendItem(root, f"{i}: {bone_scale.name}", data=bone_scale)

    def load_skeletons(self):
        self.skeleton_list.DeleteAllItems()
        self.skeleton_list.Refresh()
        self.skeleton_list.AddRoot("Skeleton")
        for i, skeleton in enumerate(self.bcs.skeletons):
            skeleton_entry = self.skeleton_list.AppendItem(
                self.skeleton_list.GetRootItem(), f"{i}: Skeleton", data=skeleton)
            self.load_bones(skeleton_entry, skeleton)

    def load_bones(self, root, skeleton):
        if not skeleton:
            return
        for i, bone in enumerate(skeleton.bones):
            self.skeleton_list.AppendItem(root, f"{i}: {bone.name}", data=bone)

    def save_bcs(self, e):
        if not self.bcs:
            dlg = wx.MessageDialog(self, " No BCS Loaded", "Warning", wx.OK)
            dlg.ShowModal()  # Shows it
            dlg.Destroy()  # finally destroy it when finished.
            return

        dlg = wx.FileDialog(self, "Save as...", self.dirname, "", "*.bcs", wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.statusbar.SetStatusText("Saving...")
            create_backup(self.dirname, filename)
            path = os.path.join(self.dirname, filename)
            self.bcs.header.gender = self.gender.GetSelection()
            self.bcs.header.race = self.race.GetSelection()
            self.bcs.save(path)
            self.statusbar.SetStatusText(f"Saved {path}")
            saved = wx.MessageDialog(self, f"Saved to {path} successfully", "BCS Saved")
            saved.ShowModal()
            saved.Destroy()
        dlg.Destroy()

    def reindex_part_sets(self, selected=None):
        if not self.bcs:
            return
        if not self.bcs.part_sets:
            return
        item = root = self.part_set_list.GetRootItem()
        part_set_index = 0
        color_selector_index = 0
        physics_index = 0
        while item:
            data = self.part_set_list.GetItemData(item)
            num_children = self.part_set_list.GetChildrenCount(item)
            if isinstance(data, PartSet):
                self.part_set_list.SetItemText(item, f"{part_set_index}: Part Set")
                part_set_index += 1
            elif isinstance(data, Part):
                color_selector_index = 0
                physics_index = 0
            elif isinstance(data, ColorSelector):
                name = self.bcs.part_colors[data.part_colors].name
                try:
                    image = color_db[data.part_colors][data.color]
                    self.part_set_list.SetItemText(item, f"{color_selector_index}: {name}, {data.color}")
                    self.part_set_list.SetItemImage(item, image)
                except IndexError:
                    self.part_set_list.SetItemText(item, f"{color_selector_index}: NULL, -1")
                    self.part_set_list.SetItemImage(item, -1)
                color_selector_index += 1
            elif isinstance(data, Physics):
                self.part_set_list.SetItemText(item, f"{physics_index}")
                physics_index += 1
            elif item != root and num_children == 0:
                self.part_set_list.Delete(item)

            item = get_next_item(self.part_set_list, item)

    def reindex_part_colors(self, selected=None):
        if not self.bcs:
            return
        if not self.bcs.part_colors:
            return
        item = self.part_color_list.GetRootItem()
        part_color_name = ''
        part_color_index = 0
        color_index = 0
        while item:
            data = self.part_color_list.GetItemData(item)
            if isinstance(data, PartColor):
                self.part_color_list.SetItemText(item, f"{part_color_index}: {data.name}")
                part_color_name = data.name
                part_color_index += 1
                color_index = 0
            elif isinstance(data, Color):
                if part_color_index - 1 > len(color_db):
                    data.part_color_index = 0
                    data.color = 0
                image_index = color_db[part_color_index-1][color_index]
                if part_color_name == 'eye_':
                    bitmap = wx.Bitmap.FromRGBA(16, 16, *data.color4[:3], 255)
                else:
                    bitmap = wx.Bitmap.FromRGBA(16, 16, *data.color1[:3], 255)
                color_db.image_list.Replace(image_index, bitmap)
                self.part_color_list.SetItemText(item, f"{color_index}")
                color_index += 1
            item = get_next_item(self.part_color_list, item)

    def reindex_bodies(self, selected=None):
        if not self.bcs:
            return
        if not self.bcs.bodies:
            return
        body_index = 0
        bone_scale_index = 0
        item = self.body_list.GetRootItem()
        while item:
            data = self.body_list.GetItemData(item)
            if isinstance(data, Body):
                self.body_list.SetItemText(item, f"{body_index}: Body")
                body_index += 1
                bone_scale_index = 0
            elif isinstance(data, BoneScale):
                self.body_list.SetItemText(item, f"{bone_scale_index}: {data.name}")
                bone_scale_index += 1
            item = get_next_item(self.body_list, item)

    def reindex_skeletons(self, selected=None):
        if not self.bcs:
            return
        if not self.bcs.skeletons:
            return
        item = self.skeleton_list.GetRootItem()
        skeleton_index = 0
        bone_index = 0
        while item:
            data = self.skeleton_list.GetItemData(item)
            if isinstance(data, Skeleton):
                self.skeleton_list.SetItemText(item, f"{skeleton_index}: Skeleton")
                skeleton_index += 1
                bone_index = 0
            elif isinstance(data, Bone):
                self.skeleton_list.SetItemText(item, f"{bone_index}: {data.name}")
                bone_index += 1
            item = get_next_item(self.skeleton_list, item)

    def on_add(self, _, paste=False):
        text = self.add_button.GetLabelText().replace(" Copy", "")
        if text.endswith('y'):
            page_name = f'{text[4:-1]}ies'
        else:
            page_name = f'{text[4:]}s'

        page = self.main_panel.pages[page_name]
        item_type = text[4:].replace(' ', '_').lower()
        add_item_func = getattr(page, f'add_{item_type}')
        add_item_func(None, add_at_end=True, paste=paste)

    def change_add_text(self, text):
        self.add_button.SetLabelText(f"Add {text}")
        self.add_copy_button.SetLabelText(f"Add {text} Copy")
        self.enable_add_copy()

    def enable_add_copy(self):
        text = self.add_copy_button.GetLabelText().replace(" Copy", "")[4:]
        cdo = wx.CustomDataObject("BCSEntry")
        success = False
        valid = False
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(cdo)
            wx.TheClipboard.Close()
        if success:
            paste_data = pickle.loads(cdo.GetData())
            if not isinstance(paste_data[0], list):
                item_type = type(paste_data[0])
                valid = not isinstance(item_type, list) and item_type.get_readable_name() == text
        self.add_copy_button.Enable(valid)

    def on_find(self, _):
        if not self.replace.IsShown():
            self.find.Show()

    def on_replace(self, _):
        if not self.find.IsShown():
            self.replace.Show()


if __name__ == '__main__':
    app = wx.App(False)
    dirname = filename = None
    if len(sys.argv) > 1:
        dirname, filename = os.path.split(sys.argv[1])
    frame = MainWindow(None, f"YaBCS Organizer v{VERSION}", dirname, filename)
    app.MainLoop()
