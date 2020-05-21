from pubsub import pub

from yabcs.panels.types import BasePanel


class BonePanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['name'] = self.add_text_entry(self.entry_page, 'Name')

        self.controls['u_00'] = self.add_hex_entry(self.unknown_page, 'U_00')
        self.controls['u_04'] = self.add_hex_entry(self.unknown_page, 'U_04')
        self.controls['u_08'] = self.add_hex_entry(self.unknown_page, 'U_08')
        self.controls['u_0c'] = self.add_hex_entry(self.unknown_page, 'U_0C', max=self.MAX_UINT16)
        self.controls['u_0e'] = self.add_hex_entry(self.unknown_page, 'U_0E', max=self.MAX_UINT16)
        self.controls['u_10'] = self.add_hex_entry(self.unknown_page, 'U_10', max=self.MAX_UINT16)
        self.controls['u_12'] = self.add_hex_entry(self.unknown_page, 'U_12', max=self.MAX_UINT16)
        self.controls['u_14'] = self.add_hex_entry(self.unknown_page, 'U_14', max=self.MAX_UINT16)
        self.controls['u_16'] = self.add_hex_entry(self.unknown_page, 'U_16', max=self.MAX_UINT16)
        self.controls['u_18'] = self.add_hex_entry(self.unknown_page, 'U_18', max=self.MAX_UINT16)
        self.controls['u_1a'] = self.add_hex_entry(self.unknown_page, 'U_1A', max=self.MAX_UINT16)
        self.controls['u_1c'] = self.add_hex_entry(self.unknown_page, 'U_1C', max=self.MAX_UINT16)
        self.controls['u_1e'] = self.add_hex_entry(self.unknown_page, 'U_1E', max=self.MAX_UINT16)
        self.controls['u_20'] = self.add_hex_entry(self.unknown_page, 'U_20', max=self.MAX_UINT16)
        self.controls['u_22'] = self.add_hex_entry(self.unknown_page, 'U_22', max=self.MAX_UINT16)
        self.controls['u_24'] = self.add_hex_entry(self.unknown_page, 'U_24', max=self.MAX_UINT16)
        self.controls['u_26'] = self.add_hex_entry(self.unknown_page, 'U_26', max=self.MAX_UINT16)
        self.controls['u_28'] = self.add_hex_entry(self.unknown_page, 'U_28', max=self.MAX_UINT16)
        self.controls['u_2a'] = self.add_hex_entry(self.unknown_page, 'U_2A', max=self.MAX_UINT16)
        self.controls['u_2c'] = self.add_hex_entry(self.unknown_page, 'U_2C', max=self.MAX_UINT16)
        self.controls['u_2e'] = self.add_hex_entry(self.unknown_page, 'U_2E', max=self.MAX_UINT16)

    def reindex(self, changed):
        if 'name' in changed:
            pub.sendMessage("reindex_skeletons")
