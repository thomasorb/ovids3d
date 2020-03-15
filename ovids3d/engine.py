import sys
import numpy as np

import astropy.io.fits as pyfits

from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, VBase4, TransparencyAttrib, Vec3, Point3, NodePath
from panda3d.physics import ActorNode, ForceNode, LinearVectorForce
from direct.filter.CommonFilters import CommonFilters
from panda3d.core import WindowProperties
from direct.task.Task import Task
from direct.particles.ParticleEffect import ParticleEffect
from direct.interval.IntervalGlobal import Wait, Sequence, Func, ParticleInterval, Parallel

from . import overlay
from . import core
from . import models        

#########################################################
##### class World #######################################
#########################################################

class World(DirectObject):


    def __init__(self, bloom=0.62, blur=0.7, record=False):
        self.base = ShowBase()
        self.base.setBackgroundColor(0,0,0)
                
        filters = CommonFilters(self.base.win, self.base.cam)
        filters.setBloom(blend=np.array([1,1,1,0.]), intensity=bloom, size='large', desat=0.0)
        filters.setBlurSharpen(blur)

        self.background = models.Background()
        
        
        self.base.disableMouse()
        self.base.enableParticles()

        if record:
            self.base.movie(namePrefix = 'movie', duration = 60*5, fps = 30,
                            format = 'jpg', sd = 4, source = None)
        
        
        self.accept("escape", sys.exit)

        self.objects_node = render.attachNewNode('objects_node')
        self.objects_node.setPos(0,0,0)

        self.config = core.Config()
        self.config['spacescale'] = 1 # m / 3d space unit
        self.config['timescale'] = 1 # s / real s 
                
        self.physics_node = NodePath("physics-node")
        self.physics_node.reparentTo(render)

        an = ActorNode('world-physics')
        self.objects_node = self.physics_node.attachNewNode(an)
        
        self.overlay = overlay.Overlay(self.base)
        
        self.ship = Ship(self.base, self.objects_node, self.config, self.overlay.infos)
        self.ship.to_origin()

    
    def load_map(self, path, name, cmap):
        self.map3d = core.Map3d(path, name, cmap)
        
        self.pixels = models.Pixels(
            self.objects_node, self.map3d, self.config)

    def add_star(self, radius, atm_size, colorintensity=20, pos=(0,0,0), color='white', atmalpha=0.7):
        self.star = models.Star(
            self.objects_node, Vec3(pos),
            radius, atm_size, 
            0, color, intensity=colorintensity, atmalpha=atmalpha)

        
        

#########################################################
##### class Ship ########################################
#########################################################

class Ship(DirectObject):

    default_fov = 55
    
    def __init__(self, base, objects_node, config, infos):
        self.objects_node = objects_node
        self.node = render.attachNewNode('ship-node')
        self.direction_node = NodePath("direction-node")
        self.direction_node.reparentTo(self.node)


        self.infos = infos
        self.config = config

        self.BRAKEMAG = 200
    
        self.base = base
        self.fov = self.default_fov
        self.setFov()
        
        self.colors = core.Colors()
        self.lookatnode = self.objects_node
        
        
        self.farstars = models.FarStars(self.node)
        
                
        self.base.physicsMgr.attachPhysicalNode(self.objects_node.node())
        
        self.thruster = NodePath("thruster") # make a thruster
        self.thruster.reparentTo(self.objects_node) 
        self.thruster.setPos(0,0,0)
        self.thrusterFN = ForceNode('world-thruster') # Attach a thruster force
        
        self.text = None
        ## Keys + mouse
        self.keysmgr = core.KeysMgr()
        
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

        
        taskMgr.remove('ship-mouseMoveTask')
        taskMgr.add(self.mouseMoveTask, 'ship-mouseMoveTask')
        taskMgr.remove('ship-shipMoveTask')
        taskMgr.add(self.shipMoveTask, 'ship-shipMoveTask')
        taskMgr.remove('ship-setDirection')
        taskMgr.add(self.setDirectionTask, 'ship-setDirection')


    def setPos(self, pos):
        self.objects_node.setPos(pos)

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
        
    def shipMoveTask(self, task):

        SCALE = 500
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
    

    def setHpr(self, h, p, r):
        self.base.camera.setHpr(self.base.camera, h, p, r)

    def posInterval(self, *args):
        return self.objects_node.posInterval(*args)

    def hprInterval(self, *args):
        return self.base.camera.hprInterval(*args)
    
    def autopilot(self, filepath, scale=1, timescale=1):
        taskMgr.remove('ship-mouseMoveTask')
        taskMgr.remove('ship-shipMoveTask')
        
        self.start_looking_at('center')
        path = core.Path(filepath)
        possteps = path.get_pos_steps(30000)
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
            path.get_look_steps(),
            self.start_looking_at)
        
        fovseq = create_other_sequence(
            path.get_fov_steps(),
            set_fov)

        parallel = Parallel(posseq, lookseq, fovseq)
        parallel.loop()

        taskMgr.add(self.shipMoveTask, 'ship-shipMoveTask')
        taskMgr.add(self.mouseMoveTask, 'ship-mouseMoveTask')
                
    def setDirectionTask(self, task):
        this_pos = self.objects_node.getPos()

        if self.last_pos is not None:
            direction_vec = self.last_pos - this_pos
            self.direction_node.setPos(direction_vec)
        
        self.last_pos = this_pos
        return Task.cont
        
    def lookAtTask(self, task):
        self.base.camera.setHpr(self.lookatnode, 0, 0, 0)
        self.base.camera.lookAt(self.lookatnode)        
        return Task.cont
        
    def start_looking_at(self, direction):
        if direction == 'center':
            self.lookatnode = self.objects_node
        elif direction == 'front':
            self.lookatnode = self.direction_node
        else:
            raise StandardError('bad direction')
        taskMgr.remove('ship-lookAtTask')
        taskMgr.add(self.lookAtTask, 'ship-lookAtTask')
        
    def stop_looking_at(self):
        taskMgr.remove('ship-lookAtTask')
        

