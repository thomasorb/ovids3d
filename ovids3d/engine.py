import sys
import numpy as np
import time
import astropy.io.fits as pyfits
import scipy.spatial

from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, VBase4, TransparencyAttrib, Vec3, Point3, NodePath
from panda3d.physics import ActorNode, ForceNode, LinearVectorForce
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import WindowProperties, Fog, LineSegs, Material
from direct.task.Task import Task
from direct.particles.ParticleEffect import ParticleEffect
from direct.interval.IntervalGlobal import Wait, Sequence, Func, ParticleInterval, Parallel

from . import overlay
from . import core
from . import models
from . import utils
import ovids3d.ext.grid3d

import logging
logger = logging.getLogger(__name__)

#########################################################
##### class World #######################################
#########################################################

class World(core.DirectCore):


    def __init__(self, bloom=0.62, blur=0.7, gamma=0.5,
                 ink=0.4, add_farstars=False, **kwargs):

        super().__init__()    

        logger.info('starting')
        self.config = core.Config()
        self.config.update(kwargs)
        
        # logging
        if self.config.debug:
            logger.setLevel(logging.DEBUG)
                            
        self.base = ShowBase()
        self.base.setBackgroundColor(0,0,0)
                
        filters = CommonFilters(self.base.win, self.base.cam)
        filters.setBloom(blend=np.array([1,1,1,0.]), intensity=bloom, size='large', desat=0.0)
        filters.setBlurSharpen(blur)
        filters.setCartoonInk(separation=ink, color=(0,0,0,1))
        filters.setGammaAdjust(gamma)
        filters.setHighDynamicRange()
        #filters.setExposureAdjust(0)
        
        self.base.disableMouse()
        self.base.enableParticles()        
        
        self.accept("escape", sys.exit)
                
        self.physics_node = NodePath("physics-node")
        self.physics_node.reparentTo(render)

        an = ActorNode('world-physics')
        self.objects_node = self.physics_node.attachNewNode(an)

        self.ship = Camera(self.base, self.objects_node, self.config, add_farstars=add_farstars)
        self.ship.to_origin()

        if self.config.full_overlay:
            gridsize = self.config['gridsize'] * self.config['spacescale']
            grid = ovids3d.ext.grid3d.ThreeAxisGrid(xsize=gridsize,
                                                    ysize=gridsize,
                                                    zsize=gridsize, subdiv=1)
            gridnodepath = grid.create()
            gridnodepath.reparentTo(self.objects_node)
        

    def add_bammodel(self, path, colorscale=(1,1,1,1)):
         newmod = loader.loadModel(path, noCache=True)
         newmod.setScale(self.config['spacescale'])
         newmod.reparentTo(self.objects_node)
         newmod.setTransparency(True)
         newmod.setRenderModeFilledWireframe(
             (colorscale[0], colorscale[1], colorscale[2], colorscale[3]*3))
         newmod.setColorScale(colorscale)
         
        
    def add_map(self, path, cmap, colorscale=(1,1,1,1), ascubes=False, colorpower=1,
                norender=False, perc=(3,99), nocbar=False, limitnb=None, cubescale=1):

        logger.info('loading {}'.format(path))
        if '.bam' in path:
            self.pixels = loader.loadModel(path, noCache=True)
            self.pixels.setScale(self.config['spacescale'])
            self.pixels.reparentTo(self.objects_node)
            self.pixels.setTransparency(True)
            self.pixels.setColorScale(colorscale)
            cbar_path = path + '.cbar.png'
            
        elif '.fits' in path:
            map3d = core.Map3d(path, cmap, scale=self.config['spacescale'],
                               colorpower=colorpower, colorscale=colorscale, perc=perc,
                               limitnb=limitnb)
    
            if hasattr(self, 'map3d'):
                del self.config['cbar_path']
                if np.any(map3d.posx != self.map3d.posx):
                    raise Exception('posx not the same')
                xyzrgba = map3d.xyzrgba
                new_xyzrgba = np.array(xyzrgba)
                
                new_xyzrgba[3:,:] += np.array(self.map3d.xyzrgba)[3:,:] 
                self.map3d.xyzrgba = new_xyzrgba
                self.nb_of_added_maps += 1
            else:
                self.map3d = map3d
                self.nb_of_added_maps = 1
                
            cbar_path = self.map3d.cbar_path
            if not norender:
                xyzrgba = np.array(self.map3d.xyzrgba)
                xyzrgba[6,:] /= self.nb_of_added_maps
                self.map3d.xyzrgba = list(xyzrgba)
                self.pixels = models.Pixels(
                    self.objects_node, self.map3d,
                    cubescale=self.config['spacescale']*cubescale,
                    ascubes=ascubes)

                if ascubes:
                    if self.config['spacescale'] != 1:
                        logger.warning('space scale != 1. conversion will not have a normal scale.')
                    logger.info('writing converted data to {}. this file can be loaded instead for a much faster loading process (but make sure that the spacescale was set to 1.)'.format(path + '.bam'))
                    self.pixels.node.writeBamFile(path + '.bam')

                render.analyze()
                
        else: raise StandardError('bad extension (must be fits or bam)')

        if not nocbar:
            self.config['cbar_path'] = cbar_path

        logger.info('{} loaded'.format(path))
        

        
    def add_star(self, radius, atm_size, colorintensity=20, pos=(0,0,0),
                 color='white', atmalpha=0.7, endcolor=None, atmnb=100):
        self.star = models.Star(
            self.objects_node, Vec3(pos),
            radius * self.config['spacescale'], atm_size, 
            0, color, intensity=colorintensity, atmalpha=atmalpha,
            atmendcolor=endcolor, atmnb=atmnb)

    def add_plane(self, scale=1, pos=(0,0,0), intensity=1, hpr=(0,90,0), texrot=90):
        models.Plane(self.objects_node, scale=scale*self.config['spacescale'],
                     intensity=intensity, pos=pos, texrot=texrot, hpr=hpr)

    def add_near_stars(self, nb, radius=10):
        models.NearStars(self.objects_node, nb=nb, radius=radius*self.config['spacescale'])

    def add_deep_space_background(self):
        """Add a deep space background for extragalactc objects
        """
        self.background = models.Background(scale=100*self.config['spacescale'])

    def add_milkyway(self, ra, dec, intensity=0.5):
        """Add a milky way background based on NASA Scientific Visualization
        Studio randomized star map. The orientation of the milky way
        should be realistic if the x, y coordinates are respectively
        the ra and dec (SITELLE's cube are oriented such that the x
        axis of the image is following the RA axis.)

        :param ra: RA in degrees 

        :param dec: DEC in degrees

        """
        logger.info('loading Milky Way')
        
        self.background = models.MilkyWay(
            ra, dec, scale=100*self.config['spacescale'], intensity=intensity)
        logger.info('Milky Way loaded')
        
    def add_model(self, path, color=(1,1,1), alpha=1, wireframe=False, transparency_bin=0):
        model = loader.loadModel(path, noCache=True)
        model.setHpr(model, 0, 90, 0)
        model.setHpr(model, 90, 0, 0)
        model.setHpr(model, 0, 180, 0)
        model.flattenLight()
        
        model.setScale(self.config['spacescale'])
        if wireframe:
            model.setColor(core.Colors.get(color) * alpha)
            model.setRenderModeThickness(1)
            model.setRenderModeWireframe()
        else:
            color = core.Colors.get(color, alpha)
        
            model.setTransparency(TransparencyAttrib.MAlpha, True)
            model.setAlphaScale(alpha)
            model.setShaderAuto()
            model.clearColor()
            model.setColor(color)
            
            modelMaterial = Material()
            modelMaterial.setEmission(color)
            modelMaterial.setSpecular(color)
            modelMaterial.setShininess(4)
            model.setMaterial(modelMaterial)
            model.setBin('fixed', transparency_bin)
        
        model.reparentTo(self.objects_node)

    def add_axis(self, rotation=(0,0,0), size=10, color='white'):
        size *= self.config['spacescale']
        segs = LineSegs("lines")
        segs.setColor(core.Colors.get(color))
        segs.setThickness(1)
        
        xyz = Vec3((0,0,size))
        rotation = scipy.spatial.transform.Rotation.from_euler('XYZ', rotation, degrees=True)
        xyz = rotation.apply(xyz)
        xyz = np.array((xyz[1], xyz[2], xyz[0]))
        segs.moveTo(*xyz)
        segs.drawTo(*-xyz)
        
        segsnode = segs.create(False)
        self.objects_node.attachNewNode(segsnode)

    def add_gridplane(self, size, subdiv, color='white', alpha=None, pos=(0,0,0),
                      hpr=(0,0,0)):
        
        gridsize = size * self.config['spacescale']
        grid = ovids3d.ext.grid3d.ThreeAxisGrid(xsize=gridsize,
                                                ysize=0,
                                                zsize=gridsize,
                                                subdiv=subdiv)
        node = grid.create()
        node.setPos(Vec3(pos))
        node.setHpr(Vec3(hpr))
        node.clearColor()
        node.setColor(core.Colors.get(color, alpha))
            
        
        node.reparentTo(self.objects_node)
        
        
        
        
	



#########################################################
##### class Camera ######################################
#########################################################

class Camera(core.DirectCore):

    default_fov = 55

    def __init__(self, base, objects_node, config, add_farstars=True):
        super().__init__()
        
        self.base = base
        self.config = config
        self.objects_node = objects_node
        
        self.node = render.attachNewNode('ship-node')
        self.direction_node = NodePath("direction-node")
        self.direction_node.reparentTo(self.node)

        ## Keys + mouse
        self.keysmgr = core.KeysMgr()
        
        self.overlay = None
        
        if self.config['overlay']:
            self.overlay = overlay.Overlay(self.base, self.config, self.keysmgr, self)

        
            # create console handler and set level to debug
            ch = logging.StreamHandler(stream=self.overlay.terminalout)
            ch.setLevel(logging.DEBUG)

            # create formatter
            formatter = logging.Formatter('%(levelname)s %(message)s')

            # add formatter to ch
            ch.setFormatter(formatter)

            # add ch to logger
            logger.addHandler(ch)

        # 'application' code
        logger.debug('debug message')
        logger.info('info message')
        logger.warning('warn message')
        logger.error('error message')
        logger.critical('critical message')

            
        self.config = config

        self.fov = self.default_fov
        self.setFov()
        
        self.lookatnode = self.objects_node
        
        if add_farstars:
            self.farstars = models.FarStars(self.node, radius=80*self.config['spacescale'])

        
        # To set relative mode and hide the cursor:
        props = WindowProperties()
        #props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_absolute)
        self.base.win.requestProperties(props)

        self.last_pos = None
        self.mouse1_pressed = False
        self.mouse3_pressed = False

        self.accept('mouse1', self.mouse1)
        self.accept('mouse1-up', self.mouse1_up)

        self.accept('mouse3', self.mouse3)
        self.accept('mouse3-up', self.mouse3_up)

        self.accept('wheel_up', self.wheel_up)
        self.accept('wheel_down', self.wheel_down)


        self.stop_looking_at()
        taskMgr.remove('cam-mouseMoveTask')
        taskMgr.add(self.mouseMoveTask, 'cam-mouseMoveTask')
        taskMgr.remove('cam-camMoveTask')
        taskMgr.add(self.camMoveTask, 'cam-camMoveTask')
        taskMgr.remove('cam-setDirection')
        taskMgr.add(self.setDirectionTask, 'cam-setDirection')
        if self.overlay is not None:
            taskMgr.remove('cam-infoTask')
            taskMgr.add(self.infoTask, 'cam-infoTask')

    def infoTask(self, task):
        # minus before getPos because the camera is not moving, only
        # the objects are. i.e. relative camera position is the
        # inverse of objects position (real camera position is always
        # 0,0,0).
        x, y, z = - self.getPos() / self.config['spacescale']
        self.config['pos_xyz'] = x, y, z
        self.config['pos_sph'] = utils.xyz2sph(x, y, z)
        self.config['pos_hpr'] = self.base.camera.getHpr()
        
        self.config['distance'] = np.sqrt(
            np.sum((self.getPos() / self.config['spacescale'])**2))
        return Task.cont


    def command(self, text):

        drawer = models.Drawer(self.objects_node, self.overlay)
        
        text = text.strip().split()
        key = text[0]
        
        if len(key) > 1:
            val = np.array(text[1:], dtype=float)
        else: val = None
        if len(val) == 0: val = None
        
        if key == 'pos':
            self.setPos(Vec3(*val) * self.config['spacescale'])
            
        elif key == 'lookat':
            if val is None:
                self.base.camera.lookAt(self.objects_node)
            else:
                self.base.camera.lookAt(
                    self.objects_node, Vec3(*val) * self.config['spacescale'])
                
        elif key == 'line':
            if val is None:
                retext = drawer.line(self.objects_node, *self.getPos())
            elif len(val) == 3:
                retext = drawer.line(self.objects_node, *val)    
            elif len(val) == 6:
                retext = drawer.line(self.objects_node, *val[:3], to=val[3:])
            else:
                raise Exception('bad number of arguments')
            
        else:
            raise Exception('unknown command')
    
    def setPos(self, pos):
        self.objects_node.setPos(pos)

    def getPos(self):
        """Return position of the objects node. Don't forget that camera is
        never moving. Only the objects are moving.
        """
        return self.objects_node.getPos()

    def to_origin(self):
        #self.setPos(Vec3(0, -5 * self.config['spacescale'], 0))
        self.setPos(Vec3(0, 0, -5 * self.config['spacescale']))
        self.base.camera.lookAt(self.objects_node)
        #self.base.camera.setHpr(self.objects_node, -180, 0, -90)
        
        self.fov = self.default_fov
        self.setFov()
        
    def setFov(self):
        if self.fov <= 0: self.fov = 1
        if self.fov >= 180: self.fov = 179
        self.base.camLens.setFov(self.fov)
                   
    def mouse1(self):
        self.mouse1_pressed = True
        #if self.base.mouseWatcherNode.hasMouse():
        #    mpos = self.base.mouseWatcherNode.getMouse()

    def mouse1_up(self):
        self.mouse1_pressed = False

    def mouse3(self):
        self.mouse3_pressed = True
        #if self.base.mouseWatcherNode.hasMouse():
        #    mpos = self.base.mouseWatcherNode.getMouse()

    def wheel_up(self):
        self.fov += 1
        self.setFov()
        
    def wheel_down(self):
        self.fov -= 1
        self.setFov()
        

    def mouse3_up(self):
        self.mouse3_pressed = False


    def mouseMoveTask(self, task):
        
        if self.base.mouseWatcherNode.hasMouse():
            if self.mouse1_pressed:
                mpos = self.base.mouseWatcherNode.getMouse()  # get the mouse position
                dx = mpos.getX()
                dy = mpos.getY()
                self.setHpr(-dx * self.config['movescale'],
                            dy * self.config['movescale'], 0)
                
            if self.mouse3_pressed:
                pass
                
        return Task.cont
    
    def setHpr(self, h, p, r):
        self.base.camera.setHpr(self.base.camera, h, p, r)

    def posInterval(self, *args):
        return self.objects_node.posInterval(*args)

    def hprInterval(self, *args):
        return self.base.camera.hprInterval(*args)
    
    def autopilot(self, filepath, scale=1, timescale=1, record=False):
        scale *= self.config['spacescale']
        timescale *= self.config['timescale']
        taskMgr.remove('cam-mouseMoveTask')
        taskMgr.remove('cam-camMoveTask')
        
        self.start_looking_at('center')
        movepath = core.Path(filepath)
        possteps = movepath.get_pos_steps(10000)
        self.setPos(Point3(*possteps[0][1:] * scale))
        
        posintervals = list()
        for istep in possteps:
            next_pos = Point3(*(istep[1:] * scale))
            posintervals.append(self.posInterval(istep[0]*timescale, next_pos))
            
        posseq = Sequence(*posintervals)

        def create_other_sequence(steps, func):
            intervals = list()
            for istep in steps:
                intervals.append(Func(func, istep[-1]))
                intervals.append(Wait(istep[0]*timescale))
            return Sequence(*intervals)
        
        def set_fov(fov):
            self.fov = fov
            self.setFov()
            
        lookseq = create_other_sequence(
            movepath.get_look_steps(),
            self.start_looking_at)
        
        fovseq = create_other_sequence(
            movepath.get_fov_steps(),
            set_fov)

        parallel = Parallel(posseq, lookseq, fovseq)
        parallel.loop()

        taskMgr.add(self.camMoveTask, 'cam-camMoveTask')
        taskMgr.add(self.mouseMoveTask, 'cam-mouseMoveTask')

        if record:
            logger.info('recording at {} fps'.format(self.config['fps']))
            self.base.movie(namePrefix='movie_',
                            duration=movepath.duration,
                            fps=self.config['fps'], 
                            format ='jpg',
                            sd=4, source=None)

                
    def setDirectionTask(self, task):
        this_pos = self.getPos()

        if self.last_pos is not None:
            direction_vec = self.last_pos - this_pos
            self.direction_node.setPos(direction_vec)
        
        self.last_pos = this_pos
        return Task.cont
        
    def lookAtTask(self, task):
        self.base.camera.lookAt(self.lookatnode.getPos(), Vec3(0,1,0))
        
        return Task.cont
        
    def start_looking_at(self, direction):
        self.islookingat = True
        if direction == 'center':
            self.lookatnode = self.objects_node
        elif direction == 'front':
            self.lookatnode = self.direction_node
        else:
            raise StandardError('bad direction')
        taskMgr.remove('cam-lookAtTask')
        taskMgr.add(self.lookAtTask, 'cam-lookAtTask')
        
    def stop_looking_at(self):
        self.islookingat = False
        taskMgr.remove('cam-lookAtTask')

    def toggle_looking_at(self, direction):
        if self.islookingat: self.stop_looking_at()
        else: self.start_looking_at(direction)
        
    def camMoveTask(self, task):

        time.sleep(0.05)
        
        SCALE = 0.1 * self.config['spacescale'] * self.config['movescale']
        SCALEHPR = 1.5 * self.config['movescale']

                    
        #self.objects_node.node().getPhysical(0).clearLinearForces()


        vec = Vec3(0,0,0)
        
        if self.keysmgr.keys.p:
            self.toggle_looking_at('center')

        if self.keysmgr.keys.w:
            vec = self.objects_node.getRelativeVector(self.base.camera, Vec3(0,-1,0))
            
        if self.keysmgr.keys.s:
            vec = self.objects_node.getRelativeVector(self.base.camera, Vec3(0,1,0))

        if self.keysmgr.keys.a:
            vec = self.objects_node.getRelativeVector(self.base.camera, Vec3(1,0,0))

        if self.keysmgr.keys.d:
            vec = self.objects_node.getRelativeVector(self.base.camera, Vec3(-1,0,0))

        if self.keysmgr.keys.r:
            vec = self.objects_node.getRelativeVector(self.base.camera, Vec3(0,0,-1))

        if self.keysmgr.keys.f:
            vec = self.objects_node.getRelativeVector(self.base.camera, Vec3(0,0,1))
            
        self.setPos(self.getPos() + vec * SCALE)

        if self.keysmgr.keys.e:
            self.setHpr(0, 0, -SCALEHPR)

        if self.keysmgr.keys.q:
            self.setHpr(0, 0, SCALEHPR)

        if self.keysmgr.keys.k:
            self.to_origin()

        return Task.cont
    

#########################################################
##### class Ship ########################################
#########################################################

class Ship(Camera):

    
    def __init__(self, base, objects_node, config, overlay):
        
        super().__init__(base, objects_node, config, overlay)
        
    #     self.BRAKEMAG = 200
            
    #     self.base.physicsMgr.attachPhysicalNode(self.objects_node.node())
    #     self.thruster = NodePath("thruster") # make a thruster
    #     self.thruster.reparentTo(self.objects_node) 
    #     self.thruster.setPos(0,0,0)
    #     self.thrusterFN = ForceNode('world-thruster') # Attach a thruster force
        
    # def brake(self):
    #     if self.last_pos is not None:
    #         deltavec = self.getPos() - self.last_pos
    #     else:
    #         deltavec = 0
    #     lvf = LinearVectorForce(-deltavec * self.BRAKEMAG)
    #     self.thrusterFN.addForce(lvf)
    #     self.objects_node.node().getPhysical(0).addLinearForce(lvf)
                                
    # def get_velocity(self):
    #     return self.objects_node.node().getPhysicsObject().getVelocity()
        
    # def camMoveTask(self, task):

    #     SCALE = 5 * self.config['spacescale']
    #     SCALEHPR = 0.1

                    
    #     self.objects_node.node().getPhysical(0).clearLinearForces()

        
    #     if self.keysmgr.keys.p:
    #         self.brake()
            
    #     if self.keysmgr.keys.w:
    #         lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,-SCALE,0)))
    #         self.thrusterFN.addForce(lvf)
    #         self.objects_node.node().getPhysical(0).addLinearForce(lvf)

    #     if self.keysmgr.keys.s:
    #         lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,SCALE,0)))
    #         self.thrusterFN.addForce(lvf)
    #         self.objects_node.node().getPhysical(0).addLinearForce(lvf)

    #     if self.keysmgr.keys.a:
    #         lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(SCALE,0,0)))
    #         self.thrusterFN.addForce(lvf)
    #         self.objects_node.node().getPhysical(0).addLinearForce(lvf)

    #     if self.keysmgr.keys.d:
    #         lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(-SCALE,0,0)))
    #         self.thrusterFN.addForce(lvf)
    #         self.objects_node.node().getPhysical(0).addLinearForce(lvf)

    #     if self.keysmgr.keys.r:
    #         lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,0,-SCALE)))
    #         self.thrusterFN.addForce(lvf)
    #         self.objects_node.node().getPhysical(0).addLinearForce(lvf)

    #     if self.keysmgr.keys.f:
    #         lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,0,SCALE)))
    #         self.thrusterFN.addForce(lvf)
    #         self.objects_node.node().getPhysical(0).addLinearForce(lvf)

    #     if self.keysmgr.keys.e:
    #         self.setHpr(0, 0, -SCALEHPR)

    #     if self.keysmgr.keys.q:
    #         self.setHpr(0, 0, SCALEHPR)

    #     if self.keysmgr.keys.k:
    #         self.to_origin()
                
    #     return Task.cont
    
