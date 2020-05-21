from pubsub import pub

from yabcs.panels.types import BasePanel


class PartColorPanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['name'] = self.add_text_entry(self.entry_page, 'Name')

    def save_entry(self, _):
        super().save_entry(_)
        pub.sendMessage('reindex_part_colors')

