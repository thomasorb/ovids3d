'''
https://matplotlib.org/examples/api/colorbar_only.html

====================
Customized colorbars
====================

This example shows how to build colorbars without an attached mappable.
'''

import matplotlib.pyplot as plt
import matplotlib as mpl

def make_colorbar(path, vmin, vmax, cmap, unit='unit', colorpower=1.):
    # Make a figure and axes with dimensions as desired.
    fig = plt.figure(figsize=(4, 4))
    ax1 = fig.add_axes([0.05, 0.05, 0.2/4, 0.9])

    # Set the colormap and norm to correspond to the data for which
    # the colorbar will be used.
    cmap = getattr(mpl.cm, cmap)
    norm = mpl.colors.PowerNorm(colorpower, vmin=vmin, vmax=vmax)

    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    cb = mpl.colorbar.ColorbarBase(ax1, cmap=cmap,
                                   norm=norm,
                                   orientation='vertical')
    cb.set_label(unit, color='white')
    cb.ax.yaxis.set_tick_params(color='white', labelcolor='white')
    
    plt.savefig(path, transparent=True, dpi=300)#, bbox_inches='tight')
    #plt.show()

