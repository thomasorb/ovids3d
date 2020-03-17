from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
import sys
from panda3d.core import PointLight, Material
import numpy as np

import ovids3d.core
import ovids3d.models

class World(DirectObject):

    SPEED = 0.01
    
    def __init__(self):
        self.base = ShowBase()
        #self.base.setBackgroundColor(0,0,0)
        self.base.disableMouse()
        
        #self.base.enableParticles()
        self.accept("escape", sys.exit)
        self.accept("s", self.toggle_rotation)
        
        plight = PointLight('plight')
        plight.setColor((1, 1, 1, 1))
        plnp = render.attachNewNode(plight)
        plnp.setPos(0, 0, 0)
        render.setLight(plnp)
        
        self.objects_node = render.attachNewNode('objectsnode')

        # Add the spinCameraTask procedure to the task manager.
        self.rotate = True
        self.angle = 0
        self.base.taskMgr.add(self.spinCameraTask, "SpinCameraTask")
        
    def toggle_rotation(self):
        if not self.rotate:
            self.rotate = True
        else:
            self.rotate = False

            
    # Define a procedure to move the camera.
    def spinCameraTask(self, task):
        dist = 2.5
        if self.rotate:
            self.angle += self.SPEED
            angleRadians = np.deg2rad(self.angle)
            self.base.camera.setPos(dist * np.sin(angleRadians), -dist * np.cos(angleRadians), 0)
            self.base.camera.setHpr(self.angle, 0, 0)
        return Task.cont
    
    def load_map(self, path, name, cmap):
        self.map3d = ovids3d.core.Map3d(path, name, cmap, scale=1)
        
        self.pixels = ovids3d.models.Pixels(
            self.objects_node, self.map3d)

        self.pixels.node.writeBamFile(path + '.bam')
        
        render.analyze()
        
w = World()
w.load_map('/home/thomas/data/M1-movie/3dmap_flux.fits', 'none', 'hot')

w.base.run()
