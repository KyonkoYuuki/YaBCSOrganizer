from pubsub import pub

from yabcs.panels.types import BasePanel


class BoneScalePanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['name'] = self.add_text_entry(self.entry_page, 'Name')
        self.controls['x'] = self.add_float_entry(self.entry_page, 'X Scale')
        self.controls['y'] = self.add_float_entry(self.entry_page, 'Y Scale')
        self.controls['z'] = self.add_float_entry(self.entry_page, 'Z Scale')

    def save_entry(self, _):
        super().save_entry(_)
        pub.sendMessage('reindex_bodies')

