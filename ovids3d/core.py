import warnings
import sys
import os
import numpy as np
import logging
import scipy.interpolate
import astropy.io.fits as pyfits
import pylab as pl
import matplotlib.cm
import xml.etree.ElementTree

from panda3d.core import Vec4, Vec3, VBase4, WindowProperties
        
# DirectionalLight
from direct.showbase.DirectObject import DirectObject
from direct.task.Task import Task

ROOT = os.path.join(os.path.split(__file__)[0])
CMAP_PATH = '.cmap.png'

import ovids3d.ext.cbar

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

    all_keys = 'a', 'd', 'w', 's', 'q', 'e', 'r', 'f', 'tab', 'p', 'o', 'i', 't', 'k', 'x'
    
    def __init__(self):
        
        self.keys = Keys()
        for key in self.all_keys:
            self.keys[key] = False
            self.accept(key, self.keys.__setitem__, extraArgs=[key, True])
            self.accept(key + '-up', self.keys.__setitem__, extraArgs=[key, False])

    def setKey(self, key, value):
        # https://discourse.panda3d.org/t/accepting-events-and-single-key-presses/3892/9
        self.keys[key] = value
        frame = globalClock.getFrameCount()
        taskMgr.add(self.resetKeys, "resetKeys",
                    extraArgs = [key, frame],
                    appendTask = True)

    def resetKeys(self, key, frame, task):
        if globalClock.getFrameCount() > frame:
            self.keys[key] = 0
            return Task.done
        else:
            return Task.cont

#########################################################
##### class Colors ######################################
#########################################################
    
class Colors(object):

    def __init__(self):
        self.colors = dict()
        self.colors['skyblue'] = self.fromRGB(0,102,204)
        self.colors['skyclearblue'] = self.fromRGB(104,229,255)
        self.colors['m1blue'] = self.fromRGB(0,0,255)#(0,35,255)
        self.colors['white'] = self.fromRGB(255,255,255)
        self.colors['black'] = self.fromRGB(0,0,0)
        self.colors['staryellow'] = self.fromRGB(255,255,204)
        self.colors['stars'] = self.fromRGB(76,0,153)
        self.colors['sunyellow'] = self.fromRGB(253,160,33)
        self.colors['red'] = self.fromRGB(204,0,0)
        self.colors['m1green'] = self.fromRGB(0,42,255)
        
    def fromRGB(self, R, G, B):
        return Vec3(R/255., G/255., B/255.)

    def fromRGBA(self, R, G, B, A):
        return VBase4(R/255., G/255., B/255., A)
    
    def __call__(self, name, alpha):
        if name in self.colors:
            return Vec4(self.colors[name], alpha)
        else:
            logging.debug('unknown color: {}'.format(name))
            try:
                return Vec4(Vec3(name), alpha)
            except:
                raise StandardError('unknown color: {}'.format(name))


#########################################################
##### class Map3d #######################################
#########################################################

class Map3d(object):

    def __init__(self, path, name, cmap, scale=1, colorpower=1, colorscale=(1,1,1,1), perc=99):

        def pixelsort(x, y, z, r, g, b, a):
            _s = np.argsort(z)
            _s2 = np.argsort(y[_s])
            _s3 = np.argsort(x[_s][_s2])
            return (x[_s][_s2][_s3], y[_s][_s2][_s3], z[_s][_s2][_s3],
                    r[_s][_s2][_s3], g[_s][_s2][_s3], b[_s][_s2][_s3], a[_s][_s2][_s3])

        
        self.data = pyfits.open(path)[0].data.T
        self.cmap = cmap
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            X, Y, Z, C = self.data
            self.posx = X * scale  
            self.posy = Y * scale
            self.posz = Z * scale

            colors = C
            vmin = np.nanpercentile(colors, 100-perc)
            vmax = np.nanpercentile(colors, perc)
            
            colors -= vmin
            colors /= (vmax - vmin)
            colors[colors < 0] = 0
            colors[colors > 1] = 1
            colors = colors ** colorpower
            self.colors = colors

            # generate colorbar png
            self.cbar_path = path + '.cbar.png'
            ovids3d.ext.cbar.make_colorbar(self.cbar_path, vmin, vmax, cmap, unit=name,
                                           colorpower=colorpower)

            # compute rgba colors
            RGBA = getattr(matplotlib.cm, cmap)(self.colors)
            RGBA[:,3] = 1
            RGBA *= np.array(colorscale)

            #self.xyzc = (self.posx, self.posy, self.posz, self.colors)
            xyzrgba = (self.posx, self.posy, self.posz,
                       RGBA[:,0], RGBA[:,1],
                       RGBA[:,2], RGBA[:,3])
            self.xyzrgba = np.array(pixelsort(*xyzrgba))
            self.posx = self.xyzrgba[0]
            self.posy = self.xyzrgba[1]
            self.posz = self.xyzrgba[2]
            
            

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
            logging.debug('{} not found, trying in paths directory'.format(filepath))
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
        logging.info('path duration: {}'.format(self.duration))
        
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
                    raise StandardError('first node cannot have any duration (it sets the original value)')
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
##### class Save ########################################
#########################################################

class Save(object):

    def __init__(self, path):

        self.path = str(path)
        self.load()

        self.data = dict()

    def load(self):
        try:
            with open(self.path, 'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.data[line[0]] = np.array(line[1:], dtype=float)
        except Exception as e:
            logging.info('file loading error: {}'.format(e))

    def write(self):
        with open(self.path, 'w') as f:
            for ikey in self.data:
                f.write('{} '.format(ikey) + ' '.join([str(ival) for ival in self.data[ikey]])
                        +'\n')
            
    def __setitem__(self, key, value):
        index = 0
        ikey = key + str(index)
        while ikey in self.data:
            index += 1
            ikey = key + str(index)
            
        self.data[ikey] = value
        self.write()

    def __getitem__(self, key, index=0):
        return self.data[key + str(index)]
        


    
    
