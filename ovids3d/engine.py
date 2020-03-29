import sys
import numpy as np
import time
import astropy.io.fits as pyfits

from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, VBase4, TransparencyAttrib, Vec3, Point3, NodePath
from panda3d.physics import ActorNode, ForceNode, LinearVectorForce
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import WindowProperties, Fog
from direct.task.Task import Task
from direct.particles.ParticleEffect import ParticleEffect
from direct.interval.IntervalGlobal import Wait, Sequence, Func, ParticleInterval, Parallel

from . import overlay
from . import core
from . import models
from . import utils
import ovids3d.ext.grid3d

import logging
#########################################################
##### class World #######################################
#########################################################

class World(DirectObject):


    def __init__(self, bloom=0.62, blur=0.7, background=False,
                 debug=False, over=True, title=None, spacescale=10,
                 timescale=1, ink=0.4):

        if not debug:
            logging.getLogger().setLevel(logging.INFO)
        else:
            logging.getLogger().setLevel(logging.DEBUG)

        self.config = core.Config()
        self.config['gridsize'] = 10
        self.config['spacescale'] = spacescale # m / 3d space unit
        self.config['timescale'] = timescale # s / real s
        self.config['title'] = str(title)
        self.config['debug'] = debug
        self.config['overlay'] = over
        
        self.base = ShowBase()
        self.base.setBackgroundColor(0,0,0)
                
        filters = CommonFilters(self.base.win, self.base.cam)
        filters.setBloom(blend=np.array([1,1,1,0.]), intensity=bloom, size='large', desat=0.0)
        filters.setBlurSharpen(blur)
        filters.setCartoonInk(separation=ink, color=(0,0,0,1))
        if background:
            self.background = models.Background(scale=100*self.config['spacescale'])
        
        
        self.base.disableMouse()
        self.base.enableParticles()        
        
        self.accept("escape", sys.exit)

                
        self.physics_node = NodePath("physics-node")
        self.physics_node.reparentTo(render)

        an = ActorNode('world-physics')
        self.objects_node = self.physics_node.attachNewNode(an)

        self.ship = Camera(self.base, self.objects_node, self.config)
        self.ship.to_origin()

        gridsize = self.config['gridsize'] * self.config['spacescale']
        grid = ovids3d.ext.grid3d.ThreeAxisGrid(xsize=gridsize,
                                                ysize=gridsize,
                                                zsize=gridsize, subdiv=1)
        gridnodepath = grid.create()
        gridnodepath.reparentTo(self.objects_node)
        
        
    def add_map(self, path, name, cmap, colorscale=(1,1,1,1), ascubes=False, colorpower=1,
                norender=False, perc=99, nocbar=False):

        if '.bam' in path:
            self.pixels = loader.loadModel(path)
            self.pixels.setScale(self.config['spacescale'])
            self.pixels.reparentTo(self.objects_node)
            self.pixels.setTransparency(True)
            self.pixels.setColorScale(colorscale)
            cbar_path = path + '.cbar.png'
            
        elif '.fits' in path:
            map3d = core.Map3d(path, name, cmap, scale=self.config['spacescale'],
                               colorpower=colorpower, colorscale=colorscale, perc=perc)
    
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
                    self.objects_node, self.map3d, cubescale=self.config['spacescale'],
                    ascubes=ascubes)

                if ascubes:
                    self.pixels.node.writeBamFile(path + '.bam')

                render.analyze()
                
        else: raise StandardError('bad extension (must be fits or bam)')

        if not nocbar:
            self.config['cbar_path'] = cbar_path

        
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
        #models.NearStars(self.objects_node, nb, scale=scale * self.config['spacescale'])
        models.NearStars(self.objects_node, radius=radius*self.config['spacescale'])



#########################################################
##### class Camera ######################################
#########################################################

class Camera(DirectObject):

    default_fov = 55

    def __init__(self, base, objects_node, config):

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
            self.overlay = overlay.Overlay(self.base, self.config, self.keysmgr)
            
        self.save = core.Save('.temp.save')
            
        self.config = config

        self.fov = self.default_fov
        self.setFov()
        
        self.colors = core.Colors()
        self.lookatnode = self.objects_node
        
        
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
        x, y, z = self.objects_node.getPos() / self.config['spacescale']
        self.config['pos_xyz'] = x, y, z
        self.config['pos_sph'] = utils.xyz2sph(x, y, z)
        
        self.config['distance'] = np.sqrt(
            np.sum((self.objects_node.getPos() / self.config['spacescale'])**2))
        return Task.cont


    def setPos(self, pos):
        self.objects_node.setPos(pos)

    def getPos(self):
        return self.objects_node.getPos()

    def to_origin(self):
        self.setPos(Vec3(0, 0, 0))
        self.base.camera.setHpr(self.objects_node, 0, 0, 0)
        
        self.base.camera.lookAt(self.objects_node)

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
        SCALE = 0.1
        
        if self.base.mouseWatcherNode.hasMouse():
            if self.mouse1_pressed:
                mpos = self.base.mouseWatcherNode.getMouse()  # get the mouse position
                dx = mpos.getX()
                dy = mpos.getY()
                self.setHpr(-dx, dy, 0)
                
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
            self.base.movie(namePrefix = 'movie_',
                            duration = movepath.duration, fps = 30,
                            format = 'jpg', sd = 4, source = None)

                
    def setDirectionTask(self, task):
        this_pos = self.objects_node.getPos()

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
        
        SCALE = 0.08 * self.config['spacescale']
        SCALEHPR = 1.5

                    
        self.objects_node.node().getPhysical(0).clearLinearForces()


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

        if self.keysmgr.keys.x:
            x, y, z = self.getPos()
            models.Line(self.objects_node, x, y, z)
            if self.overlay is not None:
                self.overlay.terminalout.append('line: {} / {}'.format(
                    (x, y, z), utils.xyz2sph(x, y, z)))
                self.save['line'] = (x, y, z)

        return Task.cont
    

#########################################################
##### class Ship ########################################
#########################################################

class Ship(Camera):

    
    def __init__(self, base, objects_node, config, overlay):
        
        Camera.__init__(self, base, objects_node, config, overlay)
        
        self.BRAKEMAG = 200
            
        self.base.physicsMgr.attachPhysicalNode(self.objects_node.node())
        self.thruster = NodePath("thruster") # make a thruster
        self.thruster.reparentTo(self.objects_node) 
        self.thruster.setPos(0,0,0)
        self.thrusterFN = ForceNode('world-thruster') # Attach a thruster force
        
    def brake(self):
        if self.last_pos is not None:
            deltavec = self.objects_node.getPos() - self.last_pos
        else:
            deltavec = 0
        lvf = LinearVectorForce(-deltavec * self.BRAKEMAG)
        self.thrusterFN.addForce(lvf)
        self.objects_node.node().getPhysical(0).addLinearForce(lvf)
                                
    def get_velocity(self):
        return self.objects_node.node().getPhysicsObject().getVelocity()
        
    def camMoveTask(self, task):

        SCALE = 5 * self.config['spacescale']
        SCALEHPR = 0.1

                    
        self.objects_node.node().getPhysical(0).clearLinearForces()

        
        if self.keysmgr.keys.p:
            self.brake()
            
        if self.keysmgr.keys.w:
            lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,-SCALE,0)))
            self.thrusterFN.addForce(lvf)
            self.objects_node.node().getPhysical(0).addLinearForce(lvf)

        if self.keysmgr.keys.s:
            lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,SCALE,0)))
            self.thrusterFN.addForce(lvf)
            self.objects_node.node().getPhysical(0).addLinearForce(lvf)

        if self.keysmgr.keys.a:
            lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(SCALE,0,0)))
            self.thrusterFN.addForce(lvf)
            self.objects_node.node().getPhysical(0).addLinearForce(lvf)

        if self.keysmgr.keys.d:
            lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(-SCALE,0,0)))
            self.thrusterFN.addForce(lvf)
            self.objects_node.node().getPhysical(0).addLinearForce(lvf)

        if self.keysmgr.keys.r:
            lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,0,-SCALE)))
            self.thrusterFN.addForce(lvf)
            self.objects_node.node().getPhysical(0).addLinearForce(lvf)

        if self.keysmgr.keys.f:
            lvf = LinearVectorForce(self.objects_node.getRelativeVector(self.base.camera, Vec3(0,0,SCALE)))
            self.thrusterFN.addForce(lvf)
            self.objects_node.node().getPhysical(0).addLinearForce(lvf)

        if self.keysmgr.keys.e:
            self.setHpr(0, 0, -SCALEHPR)

        if self.keysmgr.keys.q:
            self.setHpr(0, 0, SCALEHPR)

        if self.keysmgr.keys.k:
            self.to_origin()
                
        return Task.cont
    


#########################################################
##### class Draw ########################################
#########################################################

class Draw(object):

    def __init__(self, save, infos):
        self.save = save

        for ikey in self.save:
            print(self.save[ikey])
