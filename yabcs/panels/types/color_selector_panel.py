from pubsub import pub
import wx
import wx.adv

from pyxenoverse.gui import add_entry

from yabcs.panels.types import BasePanel
from yabcs.colordb import color_db


class ColorSelectorPanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)
        self.current_part_color = 0

        self.controls['part_colors'] = self.add_combo_box(self.entry_page, 'Part Colors')
        self.controls['part_colors'].Bind(wx.EVT_TEXT, self.skip_evt_text)
        self.controls['color'] = self.add_bitmap_combo_box(self.entry_page, 'Color')
        self.controls['color'].Bind(wx.EVT_TEXT, self.skip_evt_text)

    @add_entry
    def add_combo_box(self, panel, _, *args, **kwargs):
        kwargs['style'] = wx.CB_READONLY
        return wx.ComboBox(panel, *args, **kwargs)

    @add_entry
    def add_bitmap_combo_box(self, panel, _, *args, **kwargs):
        kwargs['style'] = wx.CB_READONLY
        return wx.adv.BitmapComboBox(panel, *args, **kwargs)

    def load_entry(self, item, entry):
        self.item = item
        self.saved_values = {}
        self.entry = entry
        # Populate comboboxes first
        self.controls['part_colors'].Clear()
        self.controls['part_colors'].AppendItems(
            [f'{i}: {part_color.name}' for i, part_color in enumerate(color_db.bcs.part_colors)])

        self.fill_color_combo_box()

        # Load values
        self.controls['part_colors'].SetSelection(self.entry.part_colors)
        self.controls['color'].SetSelection(self.entry.color)

    def save_entry(self, _):
        self.edit_thread = None
        if self.entry is None:
            return

        self.entry.part_colors = self.controls['part_colors'].GetSelection()
        self.entry.color = self.controls['color'].GetSelection()

        if self.entry.part_colors != self.current_part_color:
            self.fill_color_combo_box()
            if self.entry.color > len(color_db[self.current_part_color]) or self.entry.color == -1:
                self.entry.color = 0
        self.controls['color'].SetSelection(self.entry.color)
        self.reindex(None)

    def reindex(self, changed):
        pub.sendMessage("reindex_part_sets")

    def fill_color_combo_box(self):
        self.controls['color'].Clear()
        self.current_part_color = self.entry.part_colors
        for i, image in enumerate(color_db[self.current_part_color]):
            self.controls['color'].Append(str(i), color_db.image_list.GetBitmap(image))

    def skip_evt_text(self, _):
        pass

