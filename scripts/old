from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
import os, sys
from panda3d.core import PointLight, Material
import numpy as np

import ovids3d.core
import ovids3d.models

class World2(ovids3d.core.World):

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
    
    def add_map_cube(self, *args, **kwargs):
        kwargs['ascubes'] = True
        
        ovids3d.core.World.add_map(self, *args, **kwargs)
        
        
w = World()
w.add_map('/home/thomas/data/M1-movie/3dmap_XYZflux.fits', 'map', 'afmhot', colorpower=0.5)

w.base.run()


render.analyze()
        
