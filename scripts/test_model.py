from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
import sys
from panda3d.core import PointLight, Material
import numpy as np

class World(DirectObject):

    def __init__(self):
        self.base = ShowBase()
        #self.base.setBackgroundColor(0,0,0)
        #self.base.enableParticles()
        self.accept("escape", sys.exit)
        plight = PointLight('plight')
        plight.setColor((1, 1, 1, 1))
        plnp = render.attachNewNode(plight)
        plnp.setPos(10, -20, 0)
        render.setLight(plnp)

        #myMaterial = Material()
        #myMaterial.setShininess(5.0) #Make this material shiny
        #myMaterial.setAmbient((0, 0, 1, 1)) #Make this material blue
        
        model = loader.loadModel('/home/thomas/data/M1-movie/3dmap_flux.fits.bam')
        model.reparentTo(render)
        model.setPos(0,0,0)

        # Add the spinCameraTask procedure to the task manager.
        self.base.taskMgr.add(self.spinCameraTask, "SpinCameraTask")

    # Define a procedure to move the camera.
    def spinCameraTask(self, task):
        angleDegrees = task.time * 40.0
        angleRadians = angleDegrees * (np.pi / 180.0)
        self.base.camera.setPos(20 * np.sin(angleRadians), -20 * np.cos(angleRadians), 0)
        self.base.camera.setHpr(angleDegrees, 0, 0)
        return Task.cont
        
w = World()
w.base.run()
