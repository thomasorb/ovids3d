from direct.gui.DirectGui import *
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, Vec3
from . import core

class Infos(core.SpecialDict):

    def __getitem__(self, key):
        if key not in self: return None
        return core.SpecialDict.__getitem__(self, key)

    __getattr__ = __getitem__

    def get(self, key, default):
        val = self[key]
        if val is None: return default
        else: return val

class Overlay(DirectObject):


    def __init__(self, base):
        self.base = base
        self.infos = Infos()
        self.screen = InfoScreen(self.infos, self.base)

        taskMgr.remove('overlay-update')
        taskMgr.add(self.update, 'overlay-update')


    def update(self, task):
        self.screen.update()
        return task.cont

    

class InfoScreen(DirectObject):

    def __init__(self, infos, base):
        self.base = base
        self.infos = infos
        self.all_texts = list()
        
        self.update()

    def update(self):

        if not hasattr(self, 'title'):
            self.title = OnscreenText(
                text="Ovids3d",
                parent=self.base.a2dBottomRight, align=TextNode.A_right,
                style=1, fg=(1, 1, 1, 1), pos=(-0.1, 0.1), scale=.07)
        
            self.all_texts.append(self.title)

        try:
            self.coords_text.destroy()
        except AttributeError: pass

        text = "{}".format(
                self.infos.get('map', ''))

        self.coords_text = OnscreenText(
            text=text,
            parent=self.base.a2dTopLeft,
            align=TextNode.A_left,
            style=1, fg=(1, 1, 1, 1), pos=(0.1, -0.1), scale=.05)


        
    
