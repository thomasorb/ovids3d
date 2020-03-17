import matplotlib.cm
import numpy as np
import os
import sys
from panda3d.core import TextureStage, Material, TransparencyAttrib, GeomVertexFormat, GeomVertexData, Geom, GeomPoints, GeomVertexWriter, GeomNode, NodePath, RenderModeAttrib, PointLight, VBase4, Vec3, LineSegs
from direct.showbase.DirectObject import DirectObject

from . import core
from . import constants

#########################################################
##### class FarStars ####################################
#########################################################

class FarStars(DirectObject):

    def __init__(self, objects_node, radius=80, nb=10000):
        self.node = objects_node.attachNewNode('farstars')
        self.colors = core.Colors()
        self.radius = radius
        self.add_stars(nb//3, self.colors('staryellow', 0.8))
        self.add_stars(nb//3, self.colors('staryellow', 0.5))
        self.add_stars(nb//3, self.colors('staryellow', 0.2))
        
    def add_stars(self, nb, color):
        
        # create vertices
        format = GeomVertexFormat.getV3c4() # position and texcoord

        vdata = GeomVertexData('vdata', format, Geom.UHStatic)

        vwriter = GeomVertexWriter(vdata, 'vertex')
        colorwriter = GeomVertexWriter(vdata, 'color')

        # GeomPoints primitive
        geompoints = GeomPoints(Geom.UHStatic)

        theta = np.random.uniform(0, np.pi, nb)
        phi = np.random.uniform(0, 2 * np.pi, nb)
        posx = self.radius * np.sin(theta) * np.cos(phi)
        posy = self.radius * np.sin(theta) * np.sin(phi)
        posz = self.radius * np.cos(theta)

        index = 0
        for i in range(nb):
            # random angle positions
            vwriter.addData3f(posx[i], posy[i], posz[i])
            
            # random UVs
            colorwriter.addData4f(1,1,1,1)

            # add to GeomPoints
            geompoints.addVertex(index)
            geompoints.closePrimitive()
            index += 1

        # create GeomNode and put it in NodePath
        geom = Geom(vdata)
        geom.addPrimitive(geompoints)
        gnode = GeomNode('starfield')
        gnode.addGeom(geom)
        nodepath = NodePath(gnode)
        nodepath.setRenderMode(RenderModeAttrib.MPoint, 2.5)
        nodepath.reparentTo(self.node)
        nodepath.setLightOff()
        nodepath.clearColor()
        nodepath.setColor(color)
        nodepath.setShaderAuto()
        nodepath.setTransparency(TransparencyAttrib.MAlpha)
        nodepath.setBin('background', 0)
         
#########################################################
##### class Pixels ######################################
#########################################################

class Pixels(DirectObject):

    def __init__(self, objects_node, map3d, cubescale=1.):

        self.cubescale = cubescale
        self.node = objects_node.attachNewNode('pixels')
        self.colors = core.Colors()
        self.map3d = map3d
        #self.add_pixels(*self.map3d.xyzc)
        self.add_cubes(*self.map3d.xyzc)
        
    def add_cubes(self, posx, posy, posz, colors):
        colorsRGBA = getattr(matplotlib.cm, self.map3d.cmap)(colors)
        colorsRGBA[:,-1] = 0.8

        model_path = core.ROOT + "/models/cube.x"

        print('creating map model')
        for i in range(posx.size):
            if not i%100:
                sys.stdout.write('{}/{}\r'.format(i, posx.size))
        
            model = loader.loadModel(model_path)
            model.setPos(posx[i], posy[i], posz[i])
            model.setColor(*colorsRGBA[i,:])
            model.reparentTo(self.node)
            model.setLightOff()
            model.setScale(0.002 * self.cubescale)
            sys.stdout.flush()

        print('clearing nodes')
        self.node.clear_model_nodes()
        print('flattening node')
        self.node.flattenStrong()
        
    def add_pixels(self, posx, posy, posz, colors):

        colorsRGBA = getattr(matplotlib.cm, self.map3d.cmap)(colors)
        colorsRGBA[:,-1] = 0.8
        
        # create vertices
        format = GeomVertexFormat.getV3c4() # position and texcoord

        vdata = GeomVertexData('vdata', format, Geom.UHStatic)

        vwriter = GeomVertexWriter(vdata, 'vertex')
        colorwriter = GeomVertexWriter(vdata, 'color')

        # GeomPoints primitive
        geompoints = GeomPoints(Geom.UHStatic)

        index = 0
        for i in range(posx.size):
            # random angle positions
            vwriter.addData3f(posx[i], posy[i], posz[i])
            
            # random UVs
            colorwriter.addData4f(*colorsRGBA[i,:])

            # add to GeomPoints
            geompoints.addVertex(index)
            geompoints.closePrimitive()
            index += 1

        print('number of pixels rendered: {}'.format(index))

        # create GeomNode and put it in NodePath
        geom = Geom(vdata)
        geom.addPrimitive(geompoints)
        gnode = GeomNode('starfield')
        gnode.addGeom(geom)
        self.nodepath = NodePath(gnode)

        #self.nodepath.setRenderMode(RenderModeAttrib.MPoint, 3.8)
        self.nodepath.setRenderModePerspective(True)
        self.nodepath.setRenderModeThickness(3.8)
        
        self.nodepath.reparentTo(self.node)
        self.nodepath.setLightOff()
        #self.nodepath.clearColor()
        #self.nodepath.setColor(color)
        self.nodepath.setShaderAuto()
        self.nodepath.setTransparency(TransparencyAttrib.MAlpha)
        self.nodepath.setBin('background', 0)
        
        self.rotate = self.nodepath.hprInterval(
            (30), (0, 0, 360))
        self.rotate.loop()
        self.rotate.pause()

        
    def destroy(self):
        for m in self.nodepath.getChildren():
            m.destroy()
        self.nodepath.removeNode()


#########################################################
##### class SphericalObject #############################
#########################################################

class SphericalObject(DirectObject):

    model_path = core.ROOT + "/models/sphere.egg"

    def __init__(self, objects_node, pos, radius, dayscale,
                 atmcolor, atmheight, atmalpha, atmnb=10, tex_path= core.ROOT + "/textures/sun",
                 glowing=False):
        
        self.node = objects_node.attachNewNode(
            'sphobj{}'.format(objects_node.countNumDescendants() + 1))
        
        self.node.setPos(pos)
        self.dayscale = dayscale
        self.radius = radius
        self.tex_path = tex_path
        self.atmcolor = core.Colors()(atmcolor, atmalpha*2)
        self.atmheight = atmheight
        self.atmalpha = atmalpha
        self.atmnb = atmnb
        
        # base
        self.sphobj = loader.loadModel(self.model_path)        
        self.sphobj.reparentTo(self.node)
        self.sphobj_tex = loader.loadTexture(self.tex_path + '.png')
        self.sphobj.setTexture(self.sphobj_tex, 1)
        
        if glowing:
            ts = TextureStage('ts')
            ts.setMode(TextureStage.MModulateGlow)
            self.sphobj.setTexture(ts, self.sphobj_tex)
                    
        self.sphobj.setShaderAuto()
        self.sphobj.setScale(self.radius)
        
        # glow
        if os.path.exists(self.tex_path+'_light.png'):
            self.sphobj_tex_light = loader.loadTexture(self.tex_path+'_light.png')
            ts = TextureStage('glow')
            ts.setMode(TextureStage.MGlow)
            self.sphobj.setTexture(ts, self.sphobj_tex_light)

        self.sphobj.setBin('opaque', 0)

        self.atm_layer_index = 0
        
        self.add_clouds()
        self.add_atmosphere()

        self.rotate()
        

    def add_atmosphere(self):
        scales = np.linspace(1.02, self.atmheight, self.atmnb)
        for iscale in scales:
           self.add_atmosphere_layer(iscale, self.atmalpha/self.atmnb)

    def add_atmosphere_layer(self, scaling, alpha):
        atm = loader.loadModel(self.model_path)
        atm.reparentTo(self.node)
        atm.setScale(self.radius*scaling)
        atm.setTransparency(TransparencyAttrib.MAlpha, True)
        atm.setAlphaScale(alpha)
        atm.setShaderAuto()
        atm.clearColor()
        atm.setColor(self.atmcolor)
        
        atmMaterial = Material()
        #atmMaterial.setTwoside(False)
        atmMaterial.setEmission(self.atmcolor)
        atmMaterial.setSpecular(self.atmcolor)
        atmMaterial.setShininess(4)
        atm.setMaterial(atmMaterial)
        atm.setBin('fixed', self.atm_layer_index)
        self.atm_layer_index += 1        
        
    def rotate(self):
        self.day_period = self.sphobj.hprInterval(
            (self.dayscale), (360, 0, 0))
        self.day_period.loop()

    def add_clouds(self):
        if os.path.exists(self.tex_path + '_clouds.png'):
            self._add_cloud_layer(1.01552, 0.5)
        
    def _add_cloud_layer(self, scaling, alpha):
        atm = loader.loadModel(self.model_path)
        atm.reparentTo(self.node)
        atm.setScale(self.radius * scaling)
        
        atm.setTransparency(TransparencyAttrib.MAlpha)
        atm.setShaderAuto()
        atm.setAlphaScale(alpha)
        
        atmMaterial = Material()
        atmMaterial.setSpecular(core.Colors()('white', alpha))
        atmMaterial.setShininess(6)
        atm.setMaterial(atmMaterial)
        
        atm_tex = loader.loadTexture(self.tex_path + '_clouds.png')
        atm.setTexture(atm_tex, 1)
        atm.setBin('fixed', self.atm_layer_index)
        day_period = atm.hprInterval(
           (0.7 * self.dayscale), (360, 0, 0))
        day_period.loop()
        self.atm_layer_index += 1

        
#########################################################
##### class Star ########################################
#########################################################
        
class Star(SphericalObject):

    def __init__(self,  objects_node, pos, radius, atm_size, dayscale,
                 atmcolor, atmalpha=0.5, tex_path="textures/sun", intensity=1):
        
        SphericalObject.__init__(
            self, objects_node, pos, radius, dayscale,
            atmcolor, atm_size, atmalpha, glowing=True, atmnb=100)

        self.node.setColorScale(intensity,intensity,intensity,1)
        
        plight = PointLight('plight')
        plight.setColor(VBase4(10, 10, 10, 0))
        plnp = self.node.attachNewNode(plight)
        render.setLight(plnp)


#########################################################
##### class Background ##################################
#########################################################

class Background(object):

    def __init__(self, scale=100, intensity=0.5):
        self.sphere = loader.loadModel(core.ROOT + "/models/mw.bam")
        self.sphere.reparentTo(render)        
        self.sphere.setScale(scale)
        self.sphere.setBin('background', 1)
        self.sphere.setDepthWrite(0)
        self.sphere.setColorScale(intensity, intensity, intensity, 0)
        taskMgr.add(self.sphereTask, "Sphere Task")
        
    def sphereTask(self, task):
        self.sphere.setPos(base.camera, 0, 0, 0)
        return task.cont
