import sys

from pubsub import pub
import wx

from pyxenoverse.bcs.part import Part
from pyxenoverse.bcs.color_selector import ColorSelector
from pyxenoverse.bcs.physics import Physics
from pyxenoverse.bcs.part_color import PartColor
from pyxenoverse.bcs.color import Color
from pyxenoverse.bcs.bone_scale import BoneScale
from pyxenoverse.bcs.bone import Bone

from yabcs.panels.types.part_panel import PartPanel
from yabcs.panels.types.color_selector_panel import ColorSelectorPanel
from yabcs.panels.types.physics_panel import PhysicsPanel
from yabcs.panels.types.part_color_panel import PartColorPanel
from yabcs.panels.types.color_panel import ColorPanel
from yabcs.panels.types.bone_scale_panel import BoneScalePanel
from yabcs.panels.types.bone_panel import BonePanel


class SidePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.sizer = wx.BoxSizer()
        self.root = parent
        self.panels = {}
        self.current_panel = None

        self.add_panel(Part)
        self.add_panel(ColorSelector)
        self.add_panel(Physics)
        self.add_panel(PartColor)
        self.add_panel(Color)
        self.add_panel(BoneScale)
        self.add_panel(Bone)

        pub.subscribe(self.load_entry, 'load_entry')
        pub.subscribe(self.hide_panels, 'hide_panels')

        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)

    def add_panel(self, item_type):
        name = item_type.__name__
        panel_class = getattr(sys.modules[__name__], name + 'Panel')
        panel = panel_class(self, self.root, name, item_type)
        panel.Hide()

        self.panels[name] = panel
        self.sizer.Add(panel, 1, wx.ALL | wx.EXPAND, 10)

    def show_panel(self, panel, item, entry):
        if self.current_panel != panel:
            if self.current_panel:
                self.current_panel.Hide()
            self.current_panel = panel
            self.current_panel.Show()
            self.current_panel.Layout()
            self.Layout()
        self.current_panel.load_entry(item, entry)

    def hide_panels(self):
        for panel in self.panels.values():
            panel.Hide()
        pub.sendMessage('clear_focus')
        self.current_panel = None
        self.Layout()

    def load_entry(self, item, entry):
        name = type(entry).__name__
        if name in self.panels:
            self.show_panel(self.panels[name], item, entry)
        else:
            self.hide_panels()
