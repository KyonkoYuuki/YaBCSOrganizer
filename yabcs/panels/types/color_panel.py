from pubsub import pub

from yabcs.panels.types import BasePanel


class ColorPanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['color1'] = self.add_color_picker(self.entry_page, 'Color 1')
        self.controls['color2'] = self.add_color_picker(self.entry_page, 'Color 2')
        self.controls['color3'] = self.add_color_picker(self.entry_page, 'Color 3')
        self.controls['color4'] = self.add_color_picker(self.entry_page, 'Color 4')

        self.controls['f_40'] = self.add_float_entry(self.unknown_page, 'F_40')
        self.controls['f_44'] = self.add_float_entry(self.unknown_page, 'F_44')
        self.controls['f_48'] = self.add_float_entry(self.unknown_page, 'F_48')
        self.controls['f_4c'] = self.add_float_entry(self.unknown_page, 'F_4C')

    def reindex(self, changed):
        if 'color1' in changed or 'color4' in changed:
            pub.sendMessage("reindex_part_colors")
