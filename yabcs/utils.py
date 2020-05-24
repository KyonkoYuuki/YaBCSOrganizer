from pyxenoverse.bcs.part import Part
from pyxenoverse.bcs.color_selector import ColorSelector
from pyxenoverse.bcs.physics import Physics

FIND_ITEM_TYPES = [
    (Part, ['name', "model", "model2", "texture", "emd_name", "emm_name", "ean_name", "dyt_options", "part_hiding"]),
    (Physics, ['name', "texture", "emd_name", "emm_name", "esk_name", "bone_name", "scd_name", "dyt_options", "part_hiding"]),
    (ColorSelector, ['part_colors', 'color']),
]


class ColorDb(list):
    name = ''
    bcs = None
    image_list = None


color_db = ColorDb()
