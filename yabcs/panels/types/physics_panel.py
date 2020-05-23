from yabcs.panels.types import BasePanel


class PhysicsPanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['name'] = self.add_text_entry(self.entry_page, 'Name', maxlen=3)
        self.controls['texture'] = self.add_num_entry(self.entry_page, 'DYT Texture Index')

        self.controls['emd_name'] = self.add_text_entry(self.entry_page, 'EMD')
        self.controls['emm_name'] = self.add_text_entry(self.entry_page, 'EMM')
        self.controls['emb_name'] = self.add_text_entry(self.entry_page, 'EMB')
        self.controls['esk_name'] = self.add_text_entry(self.entry_page, 'ESK')
        self.controls['bone_name'] = self.add_text_entry(self.entry_page, 'Bone')
        self.controls['scd_name'] = self.add_text_entry(self.entry_page, 'SCD')
        self.controls['dyt_options'] = self.add_single_selection_entry(self.entry_page, 'DYT Options', majorDimension=3, choices={
            'Standard': 0x0,
            'Part DYT': 0x1,
            'Physics DYT': 0x2,
            'Accessories': 0x4,
            'Green Scouter Overlay': 0xc,
            'Red Scouter Overlay': 0x14,
            'Blue Scouter Overlay': 0x24,
            'Purple Scouter Overlay': 0x44,
            'Orange Scouter Overlay': 0x204,
        })
        self.controls['part_hiding'] = self.add_multiple_selection_entry(self.entry_page, 'Part Hiding', choices=[
            ('', ['Wrists', 'Boots'], True),
            ('', ['Face_ear', 'Hair', 'Bust', 'Pants'], True),
            ('', ['Face_base', 'Face_forehead', 'Face_eye', 'Face_nose'], True),
        ])

        self.controls['u_20'] = self.add_hex_entry(self.unknown_page, 'U_20')
