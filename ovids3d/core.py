import warnings
import sys
import os
import numpy as np
import scipy.interpolate
import astropy.io.fits as pyfits
import pylab as pl
import matplotlib.cm
import matplotlib.colors
import xml.etree.ElementTree

from panda3d.core import Vec4, Vec3, VBase4, WindowProperties
from direct.showbase.DirectObject import DirectObject

ROOT = os.path.join(os.path.split(__file__)[0])
CMAP_PATH = '.cmap.png'

import ovids3d.ext.cbar

import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

#########################################################
##### class SpecialDict #################################
#########################################################

class SpecialDict(dict):
    __getattr__ = dict.__getitem__
    __delattr__ = dict.__delitem__
    __setattr__ = dict.__setitem__

#########################################################
##### class Config ######################################
#########################################################

class Config(SpecialDict):

    def __init__(self):
        super().__init__()

        self['overlay'] = True
        self['full_overlay'] = False
        self['gridsize'] = 10
        self['spacescale'] = 1 # m / 3d space unit
        self['timescale'] = 1 # s / real s
        self['movescale'] = 2 # s / real s
        self['debug'] = False
        self['fps'] = 30
        

    def get(self, key, default):
        try:
            val = self[key]
        except KeyError:
            return default
        return val

#########################################################
##### class Keys ########################################
#########################################################

class Keys(SpecialDict): pass
    

#########################################################
##### class KeysMgr #####################################
#########################################################

class KeysMgr(DirectObject):

    all_keys = 'a', 'd', 'w', 's', 'q', 'e', 'r', 'f', 'p', 'k', 'i', 'o' #, 't', 'k', 'x', 'tab', 'o'
    
    def __init__(self):
        self.disabled = False
        self.keys = Keys()
        for key in self.all_keys:
            self.keys[key] = False
            self.accept(key, self.setKey, extraArgs=[key, True])
            self.accept(key + '-up', self.setKey, extraArgs=[key, False])
        
    def setKey(self, key, value):
        if self.disabled: return
        self.keys[key] = value
        
#########################################################
##### class Colors ######################################
#########################################################
    
class Colors(object):

    colors = {
        'skyblue': (0,102,204),
        'skyclearblue': (104,229,255),
        'm1blue': (0,42,255),
        'staryellow': (255,255,204),
        'stars': (76,0,153),
        'sunyellow': (253,160,33),
        'm1green': (0,200,255)
    }
        
    @classmethod
    def get(cls, color, alpha=None):
        logger.info('input color:{}, alpha:{}'.format(color, alpha))
        
        if color in cls.colors:
            color = cls.colors[color]

        if not isinstance(color, str):
            color = np.array(color, dtype=float)
            if np.any(color > 1):
                color /= 255.

        if alpha is not None:
            alpha = np.clip(alpha, 0, 1)

        color = Vec4(matplotlib.colors.to_rgba(color, alpha=alpha))
        logger.info('output color:{}'.format(color))
                        
        return color

#########################################################
##### class Map3d #######################################
#########################################################

class Map3d(object):

    def __init__(self, path, cmap, flux_unit='flux', scale=1, colorpower=1, colorscale=(1,1,1,1), perc=(3,99), limitnb=None):

        assert len(perc) == 2, 'perc must be 2-tuple (percmin, percmax) not {}'.format(perc)
        
        def pixelsort(x, y, z, r, g, b, a, c):
            _s = np.argsort(z)
            _s2 = np.argsort(y[_s])
            _s3 = np.argsort(x[_s][_s2])
            return (x[_s][_s2][_s3], y[_s][_s2][_s3], z[_s][_s2][_s3],
                    r[_s][_s2][_s3], g[_s][_s2][_s3], b[_s][_s2][_s3], a[_s][_s2][_s3],
                    c[_s][_s2][_s3])

        
        self.data = pyfits.open(path)[0].data
        logger.info('data shape: {}'.format(self.data.shape))
        if self.data.ndim != 2: raise Exception('Bad data shape - Should be (N, 4)')
        if np.any(self.data.shape == 4): raise Exception('Bad data shape - Should be (N, 4)')
        if self.data.shape[1] == 4:
            self.data = self.data.T
        
        self.cmap = cmap
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            #Z, X, Y, C = self.data
            X, Y, Z, C = self.data
            self.posx = X * scale  
            self.posy = Y * scale
            self.posz = Z * scale

            colors = C
            vmin = np.nanpercentile(colors, perc[0])
            vmax = np.nanpercentile(colors, perc[1])
            
            colors -= vmin
            colors /= (vmax - vmin)
            colors[colors < 0] = np.nan
            colors[colors > 1] = 1
            colors = colors ** colorpower
            self.colors = colors

            nonan = ~np.isnan(self.colors)
            self.posx = self.posx[nonan]
            self.posy = self.posy[nonan]
            self.posz = self.posz[nonan]
            self.colors = self.colors[nonan]
            
            # generate colorbar png
            self.cbar_path = path + '.cbar.png'
            ovids3d.ext.cbar.make_colorbar(self.cbar_path, vmin, vmax, cmap, unit=flux_unit,
                                           colorpower=colorpower)

            # compute rgba colors
            RGBA = getattr(matplotlib.cm, cmap)(self.colors)
            RGBA[:,3] = 1
            RGBA *= np.array(colorscale)

            xyzrgbac = (self.posx, self.posy, self.posz,
                       RGBA[:,0], RGBA[:,1],
                       RGBA[:,2], RGBA[:,3], self.colors)
            
            xyzrgbac = np.array(pixelsort(*xyzrgbac))
            pyfits.writeto('.temp.fits', xyzrgbac, overwrite=True)
            if limitnb is not None:
                randpix = np.arange(xyzrgbac.shape[1])
                np.random.shuffle(randpix)
                randpix = randpix[:limitnb]
                xyzrgbac = xyzrgbac[:,randpix]
        
            self.xyzrgba = xyzrgbac[:-1,:]
            self.colors = np.squeeze(xyzrgbac[-1,:])
                
            self.posx = self.xyzrgba[0]
            self.posy = self.xyzrgba[1]
            self.posz = self.xyzrgba[2]
            
            logger.info('map loaded')
            
            

    def show(self, axis=0, size=10000):
        randpix = np.arange(self.posx.size)
        np.random.shuffle(randpix)
        randpix = randpix[:size]
        ax0, ax1 = np.roll([self.posx, self.posy, self.posz], axis+2)[:2]
        
        pl.scatter(ax0[randpix], ax1[randpix], c=self.colors[randpix],
                   alpha=0.01, cmap=self.cmap)
        
#########################################################
##### class Path ########################################
#########################################################

class Path(object):

    labels = ['x', 'y', 'z']
    
    def __init__(self, filepath):
        
        # load roadmap steps

        if not os.path.exists(filepath):
            logger.debug('{} not found, trying in paths directory'.format(filepath))
            filepath = ROOT + '/paths/' + filepath
        
        nodes_xml = xml.etree.ElementTree.parse(filepath).getroot()
        posnodes = list()
        looknodes = list()
        fovnodes = list()
        timing = 0
        
        for node in nodes_xml:
            if node.tag == 'scale':
                self.scale = float(node.attrib['value'])
            if node.tag == 'timescale':
                self.timescale = float(node.attrib['value'])
            
            if node.tag == 'pos':
                pos = np.array(node.attrib['pos'].strip().split(','), dtype=float)
                duration = float(node.attrib['duration'])
                if 'order' in node.attrib:
                    order = int(node.attrib['order'])
                else:
                    order = 3
                posnodes.append((list([duration]) + list(pos) + list([order])))
                timing += duration
                
            elif node.tag == 'look':
                looknodes.append([timing, node.attrib['at']])
            elif node.tag == 'fov':
                inode = list([timing, node.attrib['fov']])
                if 'duration' in node.attrib:
                    inode.append(float(node.attrib['duration']))
                fovnodes.append(inode)
                            
        self.posnodes = np.array(posnodes)
        self.looknodes = looknodes
        self.fovnodes = fovnodes
        self.duration = np.sum(self.posnodes[:,0]) * self.timescale
        logger.info('path duration: {}'.format(self.duration))
        
    def get_pos_steps(self, step_nb):

        interp_groups = list()
        order = 0
        igroup = list()
        for node in self.posnodes:
            if node[-1] != order:
                if len(igroup) > 0:
                    igroup.append(node[:-1])
                    interp_groups.append((order, igroup))
                igroup = list()
                order = node[-1]
            igroup.append(node[:-1])
            
        if len(igroup) > 0:
            
            interp_groups.append((order, igroup))
                
            
        steps = list()

        for igroup in interp_groups:
            
            iorder, inodes = igroup
            inodes = np.array(inodes)
            if iorder == 1: iorder = 'linear'
            elif iorder == 2: iorder = 'quadratic'
            elif iorder == 3: iorder = 'cubic'
            else: raise Exception('bad order, must be 1,2,3')
            
            distances = np.cumsum(np.sqrt(np.sum(
                np.diff(inodes[:,1:], axis=0)**2, axis=1)))
            distances = np.insert(distances, 0, 0)
            interpolator = scipy.interpolate.interp1d(
                distances, inodes[:,1:], kind=iorder, axis=0)

            for i in range(distances.shape[0] - 1):
                alpha = np.linspace(distances[i], distances[i+1], step_nb//distances.shape[0])
                duration = inodes[i,0] / alpha.size
                isteps = interpolator(alpha)
                for j in range(1, len(isteps)):
                    steps.append(np.insert(isteps[j], 0, duration))

        steps = np.array(steps)
        steps[:,1:] *= self.scale
        steps[:,0] *= self.timescale
        
        return steps
        
    def plot(self, step_nb=1000, scale=1, axis=0):
        steps = self.get_pos_steps(step_nb)
        ax0, ax1 = np.roll(np.arange(3), axis+2)[:2] + 1
        time = np.cumsum(steps[:,0])
        pl.scatter(steps[:,ax0] * scale, steps[:,ax1] * scale, c=time, marker='.')
        pl.colorbar()
        pl.scatter(self.posnodes[:,ax0] * scale * self.scale,
                   self.posnodes[:,ax1] * scale * self.scale,
                   c=np.linspace(0,1,self.posnodes.shape[0]))
        pl.axis('equal')
        pl.xlabel(self.labels[ax0-1])
        pl.ylabel(self.labels[ax1-1])
        


    def _get_other_steps(self, nodes, cast=str):
        steps = list()
        for i in range(len(nodes)):
            istep = list(nodes[i])
            istep[1] = cast(istep[1])
            if len(nodes) >= i+2:
                istep[0] = nodes[i+1][0] - nodes[i][0]
            else:
                istep[0] = 0
            if len(istep) == 3: # microstepping at 1/100s
                microsteps = int(100 * istep[2] * self.timescale)
                deltat = istep[2]/microsteps * self.timescale
                if len(steps) == 0:
                    raise Exception('first node cannot have any duration (it sets the original value)')
                last_value = steps[-1][1]
                vals = np.linspace(last_value, istep[1], microsteps)
                for j in range(microsteps):
                    steps.append([deltat, vals[j]])

                istep[0] *= self.timescale
                istep[0] -= istep[2] * self.timescale
                if istep[0] > 0:
                    steps.append(istep[:2])
            else:
                istep[0] *= self.timescale
                steps.append(istep)
        return steps  
        
        
    def get_look_steps(self):    
        return self._get_other_steps(self.looknodes)

    def get_fov_steps(self):
        return self._get_other_steps(self.fovnodes, cast=float)
    

#########################################################
##### class DirectCore ###############################
#########################################################

class DirectCore(DirectObject):

    def __init__(self):
        super().__init__()
        
        
        
