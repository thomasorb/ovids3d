import numpy as np
import os
import sys
import logging
logger = logging.getLogger(__name__)

from panda3d.core import TextureStage, Material, TransparencyAttrib, GeomVertexFormat, GeomVertexData, Geom, GeomPoints, GeomVertexWriter, GeomNode, NodePath, RenderModeAttrib, PointLight, VBase4, Vec3, LineSegs, AmbientLight, Vec4

from . import core
from . import constants
from . import utils

#########################################################
##### class FarStars ####################################
#########################################################

class FarStars(core.DirectCore):

    PIXELSIZE = 2.
    PERSPECTIVE = False
    
    def __init__(self, objects_node, radius=80, nb=10000, intensity=0.45):
        super().__init__()
        
        self.node = objects_node.attachNewNode('farstars')
        self.radius = radius
        self.add_stars(nb//3, core.Colors.get('staryellow', 0.8), intensity=intensity)
        self.add_stars(nb//3, core.Colors.get('staryellow', 0.5), intensity=intensity)
        self.add_stars(nb//3, core.Colors.get('staryellow', 0.2), intensity=intensity)

    def set_pos(self, nb):
        X = np.random.standard_normal(size=nb)
        Y = np.random.standard_normal(size=nb)
        Z = np.random.standard_normal(size=nb)
        R = np.sqrt(X**2+Y**2+Z**2) / self.radius
        return X/R, Y/R, Z/R
                
    def add_stars(self, nb, color, intensity=1.):
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
        nodepath.setColorScale(intensity, intensity, intensity, 1)
        


class NearStars(FarStars):

    PIXELSIZE = 2.8
    PERSPECTIVE = True
    
    def set_pos(self, nb):
        posx = np.random.uniform(-self.radius, self.radius, size=nb)
        posy = np.random.uniform(-self.radius, self.radius, size=nb)
        posz = np.random.uniform(-self.radius, self.radius, size=nb)
        return posx, posy, posz


#########################################################
##### class Pixels ######################################
#########################################################

class Pixels(core.DirectCore):

    def __init__(self, objects_node, map3d, cubescale=1., ascubes=False, alpha=1):
        super().__init__()
        
        self.cubescale = cubescale
        self.node = objects_node.attachNewNode('pixels')
        self.alpha = alpha
        self.map3d = map3d
            
        if ascubes:
            self.add_cubes(*self.map3d.xyzrgba)
        else:
            self.add_pixels(*self.map3d.xyzrgba)
    
    def add_cubes(self, posx, posy, posz, r, g, b, a):
        model_path = core.ROOT + "/models/cube.x"

        logger.info('creating map model')
        logger.info('> you can skip this step by giving an already computed bam file instead of a fits file (see documentation)')
        for i in range(posx.size):
            if not i%100:
                sys.stdout.write('{}/{}\r'.format(i, posx.size))
        
            model = loader.loadModel(model_path, noCache=False)
            model.setPos(posx[i], posy[i], posz[i])
            model.setColor(r[i], g[i], b[i], a[i] * self.alpha)
            model.reparentTo(self.node)
            model.setLightOff()
            model.setScale(0.002 * self.cubescale)
            sys.stdout.flush()

        logger.info('clearing nodes')
        self.node.clear_model_nodes()
        logger.info('flattening nodes (this can take a long time)')
        self.node.flattenStrong()
        
    def add_pixels(self, posx, posy, posz, r, g, b, a):

        
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
            colorwriter.addData4f(r[i], g[i], b[i], a[i] * self.alpha)

            # add to GeomPoints
            geompoints.addVertex(index)
            geompoints.closePrimitive()
            index += 1

        logger.info('number of pixels rendered: {}'.format(index))

        # create GeomNode and put it in NodePath
        geom = Geom(vdata)
        geom.addPrimitive(geompoints)
        gnode = GeomNode('starfield')
        gnode.addGeom(geom)
        self.nodepath = NodePath(gnode)
        
        self.nodepath.setRenderModePerspective(True)
        self.nodepath.setRenderModeThickness(3.8)
        
        self.nodepath.reparentTo(self.node)
        self.nodepath.setLightOff()
        self.nodepath.setShaderAuto()
        self.nodepath.setTransparency(True)
        self.nodepath.setBin('background', 0)
        
        
    def destroy(self):
        for m in self.nodepath.getChildren():
            m.destroy()
        self.nodepath.removeNode()




#########################################################
##### class SphericalObject #############################
#########################################################

class SphericalObject(core.DirectCore):

    model_path = core.ROOT + "/models/sphere.egg"

    def __init__(self, objects_node, pos, radius, dayscale,
                 atmcolor, atmheight, atmalpha, atmnb=10, tex_path= core.ROOT + "/textures/sun",
                 glowing=False, atmendcolor=None, cloudy=False):

        super().__init__()
        
        self.node = objects_node.attachNewNode(
            'sphobj{}'.format(objects_node.countNumDescendants() + 1))
        
        self.node.setPos(pos)
        self.dayscale = dayscale
        self.radius = radius
        self.tex_path = tex_path
        self.atmcolor = core.Colors.get(atmcolor, alpha=atmalpha)
        if atmendcolor is not None:
            self.atmendcolor = core.Colors.get(atmendcolor, alpha=atmalpha)
        else:
            self.atmendcolor = None
        self.atmheight = atmheight
        self.atmalpha = atmalpha
        self.atmnb = atmnb
        
        # base
        self.sphobj = loader.loadModel(self.model_path, noCache=True)
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
        atm = loader.loadModel(self.model_path, noCache=True)
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
        atm = loader.loadModel(self.model_path, noCache=True)
        atm.reparentTo(self.node)
        atm.setScale(self.radius * scaling)
        
        atm.setTransparency(TransparencyAttrib.MAlpha)
        atm.setShaderAuto()
        atm.setAlphaScale(alpha)
        
        atmMaterial = Material()
        atmMaterial.setSpecular(core.Colors.get('white', alpha))
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

        
        super().__init__(
            objects_node, pos, radius, dayscale,
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

class Background(core.DirectCore):

    def __init__(self, scale=100, intensity=0.5):
        super().__init__()
        
        self.sphere = loader.loadModel(core.ROOT + "/models/mw.bam", noCache=True)
        self.sphere.reparentTo(render)        
        self.sphere.setScale(scale)
        self.sphere.setBin('background', 1)
        self.sphere.setDepthWrite(0)
        self.sphere.setColorScale(intensity, intensity, intensity, 1)
        self.sphere.setTexScale(TextureStage.getDefault(), -1, 1)
        self.sphere.setHpr(self.sphere, 0, -90, 0)
        # multiple trials and errors were necessary to find this strange value of
        # 78.75. Texture on the model is like that...
        self.sphere.setHpr(self.sphere, 78.75, 0, 0) 
        self.sphere.flattenLight() # reset original hpr to 0 keeping model in place
        # with z up wrt to viewer axis (along y axis of data)
        # y axis is along (z axis of data)
        # pitch = up down (confirmed)
        # heading = rotation (confirmed)
        # roll = left right (confirmed)
        taskMgr.add(self.sphereTask, "Sphere Task")
        
    def sphereTask(self, task):
        self.sphere.setPos(base.camera, 0, 0, 0)
        return task.cont


#########################################################
##### class MilkyWay ####################################
#########################################################

class MilkyWay(Background):

    def __init__(self, ra, dec, **kwargs):

        super().__init__(**kwargs)

        self.sphere.setHpr(self.sphere, *utils.compute_milky_way_hpr(
            ra, dec))

        
    

#########################################################
##### class Line ########################################
#########################################################

class Drawer(core.DirectCore):

    # def __init__(self, parentnode, r, theta, phi, color=(1,1,1,1), thickness=4):
    #     segs = LineSegs("lines")
    #     segs.setColor(Vec4(color))
    #     segs.setThickness(thickness)
    #     xyz = np.array(utils.sph2xyz(r, theta, phi))
    #     segs.moveTo(*xyz)
    #     segs.drawTo(*(-xyz))
    #     segsnode = segs.create(False)
    #     parentnode.attachNewNode(segsnode)

    def __init__(self, parentnode, color=(1,1,1,1), thickness=4):
        super().__init__()
        
        self.parentnode = parentnode
        self.color = color
        self.thickness = thickness
        
    def line(self, x, y, z, to=None):
        segs = LineSegs("lines")
        segs.setColor(Vec4(self.color))
        segs.setThickness(self.thickness)
        xyz = Vec3((x, y, z))
        segs.moveTo(*xyz)
        if to is None:
            to = -xyz
            
        segs.drawTo(*Vec3(to))
        segsnode = segs.create(False)
        self.parentnode.attachNewNode(segsnode)
        logger.info('line {} {} {} {} {} {}'.format(list(xyz) + list(to)))
    
#########################################################
##### class Plane #######################################
#########################################################

class Plane(core.DirectCore):

    def __init__(self, parentnode, scale=1, color='white', alpha=1, pos=(0,0,0), hpr=(0,0,0),
                 wireframe=False, transparency_bin=0):
        super().__init__()
        
        self.node = loader.loadModel(core.ROOT + "/models/plane.dae", noCache=True)

        # scale, hpr, position
        self.node.setScale(scale)
        self.node.setHpr(Vec3(hpr))
        self.node.setPos(Vec3(pos))
        
        # material
        #self.node.setLightOff()
        #self.node.setTransparency(True)
        
        # texture
        self.node.setTwoSided(True)
        
        # shader
        self.node.setShaderAuto()

        if wireframe:
            self.node.setColor(core.Colors.get(color) * alpha)
            self.node.setRenderModeThickness(1)
            self.node.setRenderModeWireframe()
        else:
            color = core.Colors.get(color, alpha)
        
            self.node.setTransparency(TransparencyAttrib.MAlpha, True)
            self.node.setAlphaScale(alpha)
            self.node.setShaderAuto()
            self.node.clearColor()
            self.node.setColor(color)
            
            modelMaterial = Material()
            modelMaterial.setEmission(color)
            modelMaterial.setSpecular(color)
            modelMaterial.setShininess(4)
            self.node.setMaterial(modelMaterial)
            self.node.setBin('fixed', transparency_bin)
        
        
        self.node.reparentTo(parentnode)
        
        
