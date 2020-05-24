from yabcs.panels.types import BasePanel
import wx


class PartPanel(BasePanel):
    def __init__(self, *args):
        BasePanel.__init__(self, *args)

        self.controls['name'] = self.add_text_entry(self.entry_page, 'Name', maxlen=3)
        self.controls['model'] = self.add_num_entry(self.entry_page, 'Model')
        self.controls['model2'] = self.add_num_entry(self.entry_page, 'Model2')
        self.controls['texture'] = self.add_num_entry(self.entry_page, 'Texture')
        self.controls['emd_name'] = self.add_text_entry(self.entry_page, 'EMD Name')
        self.controls['emm_name'] = self.add_text_entry(self.entry_page, 'EMM Name')
        self.controls['emb_name'] = self.add_text_entry(self.entry_page, 'EMB Name')
        self.controls['ean_name'] = self.add_text_entry(self.entry_page, 'EAN Name')
        self.controls['dyt_options'] = self.add_single_selection_entry(self.entry_page, 'DYT Options', majorDimension=2, choices={
            'Standard': 0x0,
            'Model 2 EMB.DYT': 0x2,
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

        self.controls['u_06'] = self.add_hex_entry(self.unknown_page, 'U_06', max=self.MAX_UINT16)
        self.controls['u_08'] = self.add_hex_entry(self.unknown_page, 'U_08', max=self.MAX_UINT16)
        self.controls['u_10'] = self.add_hex_entry(self.unknown_page, 'U_10', max=self.MAX_UINT64)
        self.controls['u_20'] = self.add_hex_entry(self.unknown_page, 'U_20')
        self.controls['f_24'] = self.add_float_entry(self.unknown_page, 'F_24')
        self.controls['f_28'] = self.add_float_entry(self.unknown_page, 'F_28')
        self.controls['u_2c'] = self.add_hex_entry(self.unknown_page, 'U_2C')
        self.controls['u_30'] = self.add_hex_entry(self.unknown_page, 'U_30')
        self.controls['u_48'] = self.add_hex_entry(self.unknown_page, 'U_48', max=self.MAX_UINT16)
        self.controls['u_50'] = self.add_hex_entry(self.unknown_page, 'U_50', max=self.MAX_UINT16)
