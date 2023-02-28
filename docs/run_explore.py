from ovids3d.engine import World
from panda3d.core import loadPrcFileData, ConfigVariableBool

x, y = 1920, 1080 # set the shape of the rendering window
path = 'm1_fast_xyzf.fits' # path to your data file in FITS format
cmap = 'afmhot' # colormap for the mapping of brightness values (see: https://matplotlib.org/stable/gallery/color/colormap_reference.html)



loadPrcFileData('', 'win-size {} {}'.format(
    int(x), int(y)))

ConfigVariableBool("fullscreen").setValue(1)


config_params = {
    'title': 'Crab Nebula', # Title of the vizualisation
    'center_name': 'center', # name of the center (e.g. the name of a star)
    'space_unit': 'pc', # space unit
    'spacescale': 1000, # display scale (set it to a lower value if pixels are too small)
    #'overlay': True,
#    'full_overlay':True,
    }

w = World(**config_params)
w.add_map(path, cmap)
w.base.run()
