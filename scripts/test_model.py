from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject
from direct.task import Task
import sys
from panda3d.core import AmbientLight, Material, TextureStage, PointLight, Vec4
import numpy as np

class World(DirectObject):

    def __init__(self):
        self.base = ShowBase()
        self.base.setBackgroundColor(0,0,0)
        #self.base.enableParticles()
        self.accept("escape", sys.exit)
        #plight = PointLight('plight')
        #plight.setColor((0.2, 0.2, 0.2, 1))
        #plnp = render.attachNewNode(plight)
        #plnp.setPos(10, 20, 0)
        #render.setLight(plnp)
        alight = AmbientLight('plight')
        INTENSITY = 1
        alight.setColor((INTENSITY, INTENSITY, INTENSITY, 1))
        alnp = render.attachNewNode(alight)
        #alnp.setPos(0, -20, 0)
        render.setLight(alnp)

        mat = Material()
        #mat.setShininess(5.0) #Make this material shiny
        mat.setDiffuse((1, 1, 1, 1))
        mat.setSpecular(Vec4(1, 1, 1, 1) * 0.1)
        mat.setRoughness(1)
        
        #mat.setEmission((1,1,1,1))
        #ts = TextureStage.getDefault()
        #ts.setMode(TextureStage.MBlend)
        #tex = loader.loadTexture('../ovids3d/textures/sun.png')
        
        model = loader.loadModel('../ovids3d/models/plane.bam')
        model.clearColor()
        
        
        #model.setTexture(ts, tex)
        #model.setTexScale(ts, 10000,10000)
        
        #print(model.findTextureStage('*'))
        #ts = model.findTextureStage('*')
        #model.setTexture(ts, tex)
        #model.setTexScale(ts, 1/10000, 1./10000)
        #model.setColor(1,1,1)
        print(model.findAllMaterials())
        orig_mat = model.findMaterial('Material.001')
        model.replaceMaterial(orig_mat, mat)
        print(model.findAllMaterials())

        model.setShaderAuto()
        
        model.reparentTo(render)
        model.setPos(0,0,0)
        model.setTwoSided(True)
        model.setHpr(0,90,0)
        intensity = 2.5
        model.setColorScale(intensity, intensity, intensity, 1)
        print(model.getColorScale())
        #model.setLightOff()
        #model.setTransparency(True)
        self.model = model

        # Add the spinCameraTask procedure to the task manager.
        self.base.taskMgr.add(self.spinCameraTask, "SpinCameraTask")

    # Define a procedure to move the camera.
    def spinCameraTask(self, task):
        angleDegrees = task.time * 40.0
        angleRadians = angleDegrees * (np.pi / 180.0)
        distance = 5
        self.base.camera.setPos(-distance * np.sin(angleRadians), -distance * np.cos(angleRadians), -distance * np.sin(angleRadians))
        self.base.camera.lookAt(self.model)
        return Task.cont
        
w = World()
w.base.run()
