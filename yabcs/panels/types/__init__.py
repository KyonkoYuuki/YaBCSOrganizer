import wx
import wx.adv
from pubsub import pub
from threading import Thread
import time
from wx.lib.scrolledpanel import ScrolledPanel

from pyxenoverse.gui import add_entry, EVT_RESULT, EditThread
from pyxenoverse.gui.ctrl.colour_picker_alpha_ctrl import ColourPickerAlphaCtrl
from pyxenoverse.gui.ctrl.hex_ctrl import HexCtrl
from pyxenoverse.gui.ctrl.multiple_selection_box import MultipleSelectionBox
from pyxenoverse.gui.ctrl.single_selection_box import SingleSelectionBox
from pyxenoverse.gui.ctrl.text_ctrl import TextCtrl
from pyxenoverse.gui.ctrl.unknown_hex_ctrl import UnknownHexCtrl


class Page(ScrolledPanel):
    def __init__(self, parent, rows=32):
        ScrolledPanel.__init__(self, parent)
        self.sizer = wx.FlexGridSizer(rows=rows, cols=2, hgap=10, vgap=10)
        self.SetSizer(self.sizer)
        self.SetupScrolling()


class BasePanel(wx.Panel):
    MAX_UINT16 = 0xFFFF
    MAX_UINT32 = 0xFFFFFFFF
    MAX_UINT64 = 0xFFFFFFFFFFFFFFFF

    def __init__(self, parent, root, name, item_type):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.root = root
        self.item = None
        self.entry = None
        self.edit_thread = None
        self.controls = {}
        self.saved_values = {}
        self.item_type = item_type

        self.notebook = wx.Notebook(self)
        self.entry_page = Page(self.notebook)
        self.unknown_page = Page(self.notebook)

        self.notebook.AddPage(self.entry_page, name)
        self.notebook.AddPage(self.unknown_page, 'Unknown')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 10)

        self.Bind(wx.EVT_TEXT, self.on_edit)
        self.Bind(wx.EVT_COMBOBOX, self.save_entry)
        self.Bind(wx.EVT_CHECKBOX, self.save_entry)
        self.Bind(wx.EVT_RADIOBOX, self.save_entry)
        self.Bind(wx.EVT_SLIDER, self.save_entry)
        self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.save_entry)
        EVT_RESULT(self, self.save_entry)

        pub.subscribe(self.focus_on, 'focus_on')

        self.SetSizer(sizer)
        self.SetAutoLayout(1)

    @add_entry
    def add_hex_entry(self, panel, _, *args, **kwargs):
        return HexCtrl(panel, *args, **kwargs)

    @add_entry
    def add_num_entry(self, panel, _, *args, **kwargs):
        kwargs['min'], kwargs['max'] = 0, self.MAX_UINT16
        return wx.SpinCtrl(panel, *args, **kwargs)

    @add_entry
    def add_single_selection_entry(self, panel, _, *args, **kwargs):
        return SingleSelectionBox(panel, *args, **kwargs)

    @add_entry
    def add_multiple_selection_entry(self, panel, _, *args, **kwargs):
        return MultipleSelectionBox(panel, *args, **kwargs)

    @add_entry
    def add_unknown_hex_entry(self, panel, _, *args, **kwargs):
        return UnknownHexCtrl(panel, *args, **kwargs)

    @add_entry
    def add_float_entry(self, panel, _, *args, **kwargs):
        if 'min' not in kwargs:
            kwargs['min'] = -3.402823466e38
        if 'max' not in kwargs:
            kwargs['max'] = 3.402823466e38

        return wx.SpinCtrlDouble(panel, *args, **kwargs)

    @add_entry
    def add_text_entry(self, panel, _, *args, **kwargs):
        return TextCtrl(panel, *args, **kwargs)

    @add_entry
    def add_color_picker(self, panel, _, *args, **kwargs):
        return ColourPickerAlphaCtrl(panel, *args, **kwargs)

    def add_nameable_float_entry(self, panel, *args, **kwargs):
        label = wx.StaticText(panel, -1, '')
        panel.sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        control = self.add_float_entry(panel, None, *args, **kwargs)
        return label, control

    def on_edit(self, _):
        if not self.edit_thread:
            self.edit_thread = EditThread(self)
        else:
            self.edit_thread.new_sig()

    def hide_entry(self, name):
        try:
            label = self.__getattribute__(name + '_label')
            label.SetLabelText('')
        except AttributeError:
            pass
        control = self.__getattribute__(name)
        if control.IsEnabled():
            control.Disable()
            self.saved_values[name] = control.GetValue()
            control.SetValue(0.0)

    def show_entry(self, name, text, default=None):
        try:
            label = self.__getattribute__(name + '_label')
            label.SetLabelText(text)
        except AttributeError:
            pass
        control = self.__getattribute__(name)
        if not control.IsEnabled():
            control.Enable()
            control.SetValue(self.saved_values.get(name, default))

    def load_entry(self, item, entry):
        self.item = item
        self.saved_values = {}
        self.entry = entry
        for name, control in self.controls.items():
            control.SetValue(getattr(entry, name))

    def save_entry(self, _):
        self.edit_thread = None
        if self.entry is None:
            return
        changed = []
        for name, control in self.controls.items():
            # SpinCtrlDoubles suck
            old_value = getattr(self.entry, name)
            if isinstance(control, wx.SpinCtrlDouble):
                try:
                    new_value = float(control.Children[0].GetValue())
                    setattr(self.entry, name, float(control.Children[0].GetValue()))
                except ValueError:
                    new_value = old_value
                    pass
            else:
                new_value = control.GetValue()
            if old_value != new_value:
                changed.append(name)
                setattr(self.entry, name, new_value)
        if changed:
            self.reindex(changed)

    def focus_on(self, entry):
        if not self.IsShown():
            return
        page = self.notebook.FindPage(self.controls[entry].GetParent())
        self.controls[entry].SetFocus()
        self.notebook.ChangeSelection(page)

    def reindex(self, changed):
        pass
