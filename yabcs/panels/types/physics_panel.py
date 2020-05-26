from yabcs.panels.types import BasePanel


class PhysicsPanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['name'] = self.add_text_entry(self.entry_page, 'Name', maxlen=3)
        self.controls['texture'] = self.add_num_entry(self.entry_page, 'Texture')

        self.controls['emd_name'] = self.add_text_entry(self.entry_page, 'EMD Name')
        self.controls['emm_name'] = self.add_text_entry(self.entry_page, 'EMM Name')
        self.controls['emb_name'] = self.add_text_entry(self.entry_page, 'EMB Name')
        self.controls['esk_name'] = self.add_text_entry(self.entry_page, 'ESK Name')
        self.controls['bone_name'] = self.add_text_entry(self.entry_page, 'Bone Name')
        self.controls['scd_name'] = self.add_text_entry(self.entry_page, 'SCD Name')
        self.controls['dyt_options'] = self.add_unknown_hex_entry(self.entry_page, 'DYT Options', showKnown=True, cols=3, knownValues={
            0x0: 'Standard',
            0x1: 'Part DYT',
            0x2: 'Physics DYT',
            0x4: 'Accessories',
            0xc: 'Green Scouter Overlay',
            0x14: 'Red Scouter Overlay',
            0x24: 'Blue Scouter Overlay',
            0x44: 'Purple Scouter Overlay',
            0x204: 'Orange Scouter Overlay',
        })
        self.controls['part_hiding'] = self.add_multiple_selection_entry(self.entry_page, 'Part Hiding', choices=[
            ('', ['Wrists', 'Boots'], True),
            ('', ['Face_ear', 'Hair', 'Bust', 'Pants'], True),
            ('', ['Face_base', 'Face_forehead', 'Face_eye', 'Face_nose'], True),
        ])

        self.controls['u_20'] = self.add_hex_entry(self.unknown_page, 'U_20')
