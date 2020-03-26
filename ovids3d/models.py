import matplotlib.cm
import numpy as np
import os
import sys
from panda3d.core import TextureStage, Material, TransparencyAttrib, GeomVertexFormat, GeomVertexData, Geom, GeomPoints, GeomVertexWriter, GeomNode, NodePath, RenderModeAttrib, PointLight, VBase4, Vec3, LineSegs, AmbientLight, Vec4
from direct.showbase.DirectObject import DirectObject

from . import core
from . import constants

#########################################################
##### class FarStars ####################################
#########################################################

class FarStars(DirectObject):

    PIXELSIZE = 2.
    PERSPECTIVE = False
    
    def __init__(self, objects_node, radius=80, nb=10000):
        self.node = objects_node.attachNewNode('farstars')
        self.colors = core.Colors()
        self.radius = radius
        self.add_stars(nb//3, self.colors('staryellow', 0.8))
        self.add_stars(nb//3, self.colors('staryellow', 0.5))
        self.add_stars(nb//3, self.colors('staryellow', 0.2))

    def set_pos(self, nb):
        X = np.random.standard_normal(size=nb)
        Y = np.random.standard_normal(size=nb)
        Z = np.random.standard_normal(size=nb)
        R = np.sqrt(X**2+Y**2+Z**2) / self.radius
        return X/R, Y/R, Z/R
                
    def add_stars(self, nb, color):
        
        # create vertices
        format = GeomVertexFormat.getV3c4() # position and texcoord

        vdata = GeomVertexData('vdata', format, Geom.UHStatic)

        vwriter = GeomVertexWriter(vdata, 'vertex')
        colorwriter = GeomVertexWriter(vdata, 'color')

        # GeomPoints primitive
        geompoints = GeomPoints(Geom.UHStatic)
        
        posx, posy, posz = self.set_pos(nb)
        
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
        nodepath.setRenderModePerspective(self.PERSPECTIVE)
        nodepath.setRenderModeThickness(self.PIXELSIZE)
        
        nodepath.reparentTo(self.node)
        nodepath.setLightOff()
        nodepath.clearColor()
        nodepath.setColor(color)
        nodepath.setShaderAuto()
        nodepath.setTransparency(TransparencyAttrib.MAlpha)
        nodepath.setBin('background', 0)


class NearStars(FarStars):

    PIXELSIZE = 2.8
    PERSPECTIVE = True
    
    def set_pos(self, nb):
        posx = np.random.uniform(-self.radius, self.radius, size=nb)
        posy = np.random.uniform(-self.radius, self.radius, size=nb)
        posz = np.random.uniform(-self.radius, self.radius, size=nb)
        return posx, posy, posz

    # model_path = core.ROOT + "/models/cube.x"

    # def __init__(self, objects_node, nb, scale=1):
    #     color = (0.7,1,1,1)
    #     radius = scale * 0.0005
    #     for i in range(100):
    #         ipos = np.random.uniform(-scale * 5, scale * 5, 3)
    #         iradius = np.random.uniform(radius, 2*radius)
    #         sphobj = loader.loadModel(self.model_path)
    #         sphobj.reparentTo(objects_node)
    #         sphobj.setPos(Vec3(*ipos))
    #         sphobj.setScale(iradius)
    #         sphobj.setLightOff()
    #         atmMaterial = Material()
    #         sphobj.setMaterial(atmMaterial)
    #         sphobj.setShaderAuto()
    #         sphobj.clearColor()
    #         sphobj.setColor(color)
    #         sphobj.setTransparency(True)

#########################################################
##### class Pixels ######################################
#########################################################

class Pixels(DirectObject):

    def __init__(self, objects_node, map3d, cubescale=1., ascubes=False, alpha=1):

        self.cubescale = cubescale
        self.node = objects_node.attachNewNode('pixels')
        self.colors = core.Colors()
        self.alpha = alpha
        self.map3d = map3d
        if ascubes:
            self.add_cubes(*self.map3d.xyzc)
        else:
            self.add_pixels(*self.map3d.xyzc)

    def get_colorsRGBA(self, colors):
        colorsRGBA = getattr(matplotlib.cm, self.map3d.cmap)(colors)
        colorsRGBA[:,-1] = self.alpha
        return colorsRGBA
        
    def add_cubes(self, posx, posy, posz, colors):
        colorsRGBA = self.get_colorsRGBA(colors)
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

        colorsRGBA = self.get_colorsRGBA(colors)
        
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
                 glowing=False, atmendcolor=None, cloudy=False):

        
        self.node = objects_node.attachNewNode(
            'sphobj{}'.format(objects_node.countNumDescendants() + 1))
        
        self.node.setPos(pos)
        self.dayscale = dayscale
        self.radius = radius
        self.tex_path = tex_path
        self.atmcolor = core.Colors()(atmcolor, atmalpha)
        if atmendcolor is not None:
            self.atmendcolor = core.Colors()(atmendcolor, atmalpha)
        else:
            self.atmendcolor = None
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
                    
        #self.sphobj.setShaderAuto()
        self.sphobj.setScale(self.radius)
        
        # glow
        if os.path.exists(self.tex_path+'_light.png'):
            self.sphobj_tex_light = loader.loadTexture(self.tex_path+'_light.png')
            ts = TextureStage('glow')
            ts.setMode(TextureStage.MGlow)
            self.sphobj.setTexture(ts, self.sphobj_tex_light)

        self.sphobj.setBin('opaque', 0)

        self.atm_layer_index = 0
        
        if cloudy:
            self.add_clouds()
        if self.atmnb > 0:
            self.add_atmosphere()

        self.rotate()
        

    def add_atmosphere(self):
        a = 0.1
        scaling = np.log(np.linspace(1, a, self.atmnb)) / np.log(a)
        logscaler = lambda xmin, xmax: xmin + scaling * (xmax - xmin)
        linearscaler = lambda xmin, xmax: np.linspace(xmin, xmax, self.atmnb)
        height_scales = logscaler(1.02, self.atmheight)
        if self.atmendcolor is not None:
            rscale = linearscaler(self.atmcolor[0], self.atmendcolor[0])
            gscale = linearscaler(self.atmcolor[1], self.atmendcolor[1])
            bscale = linearscaler(self.atmcolor[2], self.atmendcolor[2])
            
        for i in range(self.atmnb):
            if self.atmendcolor is not None:
                icolor = Vec4(rscale[i], gscale[i], bscale[i], self.atmcolor[3])
            else:
                icolor = self.atmcolor
            self.add_atmosphere_layer(height_scales[i], self.atmalpha/self.atmnb, icolor)

    def add_atmosphere_layer(self, scaling, alpha, color):
        atm = loader.loadModel(self.model_path)
        atm.reparentTo(self.node)
        atm.setScale(self.radius*scaling)
        atm.setTransparency(TransparencyAttrib.MAlpha, True)
        atm.setAlphaScale(alpha)
        atm.setShaderAuto()
        atm.clearColor()
        atm.setColor(color)
        
        atmMaterial = Material()
        #atmMaterial.setTwoside(False)
        atmMaterial.setEmission(color)
        atmMaterial.setSpecular(color)
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
                 atmcolor, atmalpha=0.5, tex_path="textures/sun",
                 intensity=1, atmendcolor=None, atmnb=100):

        
        SphericalObject.__init__(
            self, objects_node, pos, radius, dayscale,
            atmcolor, atm_size, atmalpha, glowing=True, atmnb=atmnb,
            atmendcolor=atmendcolor)

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
        self.sphere.setColorScale(intensity, intensity, intensity, 1)
        taskMgr.add(self.sphereTask, "Sphere Task")
        
    def sphereTask(self, task):
        self.sphere.setPos(base.camera, 0, 0, 0)
        return task.cont

#########################################################
##### class Plane #######################################
#########################################################

class Plane(object):

    def __init__(self, parentnode, scale=0.2, intensity=1, pos=(0,0,55), texrot=90, hpr=(0,0,0)):

        # alight = AmbientLight('plight')
        # INTENSITY = 0.1
        # alight.setColor((INTENSITY, INTENSITY, INTENSITY, 1))
        # alnp = render.attachNewNode(alight)
        # render.setLight(alnp)

        
        self.node = loader.loadModel(core.ROOT + "/models/plane.bam")

        # scale, hpr, position
        self.node.setScale(scale)
        self.node.setHpr(Vec3(hpr))
        self.node.setPos(Vec3(pos))
        
        # material
        #orig_mat = self.node.findMaterial('Material.001')
        #mat = Material()
        #mat.setDiffuse(Vec4(1, 1, 1, 1) *1)
        #mat.setSpecular(Vec4(1, 1, 1, 1) * 0.01)
        #mat.setRoughness(1)
        #mat.setEmission(Vec4(1,1,1,1) * 1000)
        #self.node.replaceMaterial(orig_mat, mat)
        self.node.setLightOff()
        #self.node.clearColor()
        self.node.setTransparency(True)
        self.node.setColorOff()
        self.node.setColorScaleOff()
        #print(intensity, '==================')
        #self.node.setColor(intensity,intensity,intensity,1)
        #self.node.setColor(0,0,0,1)
        self.node.setColorScale(intensity, intensity, intensity, 1)

        
        # texture
        #self.node.setBin('plane', 1)
        #self.node.setDepthWrite(0)
        ts = self.node.findTextureStage('*')
        #ts.setMode(TextureStage.MAdd)
        #tex = self.node.findTexture('*')
        #self.node.setTexture(ts, tex)
        self.node.setTexHpr(ts, 0, 0, 0)
        
        self.node.setTwoSided(True)
        
        # shader
        self.node.setShaderAuto()
        
        self.node.reparentTo(parentnode)
        
        
