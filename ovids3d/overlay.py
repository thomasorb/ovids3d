from direct.gui.DirectGui import OnscreenText, OnscreenImage, DirectEntry
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, Vec3
from . import core
import os
import numpy as np


class TerminalOut(object):

    def __init__(self, maxlines=5):

        self.maxlines = int(maxlines)
        self.text = list()

    def append(self, text):

        self.text.append('> {}'.format(text.strip()))
        if len(self.text) > self.maxlines:
            self.text.pop(0)

    def get_text(self):

        return '\n'.join(self.text)

        


class Overlay(DirectObject):


    def __init__(self, base, config, keysmgr, full=True):
        self.base = base
        self.config = config    
        self.full = full
        self.base = base
        self.keysmgr = keysmgr
        
        self.terminalout = TerminalOut()
        self.monofont = loader.loadFont(
            core.ROOT + '/fonts/fantasque-sans-mono/TTF/FantasqueSansMono-Bold.ttf')

        self.title = ''

        self.visor = OnscreenImage(
            image=core.ROOT + '/textures/angle.png', pos=(0, 0, 0), scale=0.95)
        self.visor.setTransparency(True)
        self.visor.setColorScale((1,1,1,0.4))
                
        self.terminalin = DirectEntry(
            scale=.03, command=self.terminalCommand,
            entryFont=self.monofont,
            numLines=1, focus=False,
            width=30,
            pos=(0.1,0,0.2),
            parent=self.base.a2dBottomLeft,
            text_align=TextNode.ALeft,
            frameColor=(0,1,1,0.5),
            text_fg=(1,1,1,1),
            focusInCommand=self.terminalFocusIn,
            focusOutCommand=self.terminalFocusOut)

        taskMgr.remove('overlay-update')
        taskMgr.add(self.update, 'overlay-update')
    
    def terminalCommand(self, text):
        self.terminalout.append('[eval({})]'.format(text))
        
    def terminalFocusIn(self):
        self.keysmgr.disabled = True
        
    def terminalFocusOut(self):
        self.keysmgr.disabled = False
        
    def update(self, task):

        title = self.config.get('title', 'Ovids3d')
        if title != self.title:
            self.title = title
            try:
                self.title_text.destroy()
            except AttributeError: pass
    
            self.title_text = OnscreenText(
                text=title,
                parent=self.base.a2dBottomRight, align=TextNode.A_right,
                style=2, fg=(1, 1, 1, 1), pos=(-0.1, 0.1), scale=.07)

        cbar_path = self.config.get('cbar_path', None)
        if cbar_path is not None:
            if not hasattr(self, 'colorbar'):
                self.colorbar = OnscreenImage(
                    image=cbar_path, pos=(-1.3, 0, 0), scale=0.5)
                self.colorbar.setTransparency(True)
        else:
            try:
                self.colorbar.destroy()
            except Exception as e: pass
            
        try:
            self.coords_text.destroy()
        except AttributeError: pass

        text = "distance to PSR B0531+21 (in pc): {:.3f}".format(
                float(self.config.get('distance', 'nan')))
        if self.full:
            text += "\n > Cartesian: {:.1f} {:.1f} {:.1f}".format(*self.config.get('pos_xyz', (np.nan, np.nan, np.nan)))
            text += "\n > Spherical: {:.1f} {:.1f} {:.1f}".format(*self.config.get('pos_sph', (np.nan, np.nan, np.nan)))

        self.coords_text = OnscreenText(
            text=text,
            parent=self.base.a2dTopLeft,
            align=TextNode.A_left,
            style=3, fg=(1, 1, 1, 1), pos=(0.1, -0.1), scale=.05)

        try:
            self.terminalout_text.destroy()
        except AttributeError: pass

        self.terminalout_text = OnscreenText(
            text=self.terminalout.get_text(),
            parent=self.base.a2dBottomLeft,
            align=TextNode.A_left,
            font=self.monofont,
            style=3, fg=(1, 1, 1, 1), pos=(0.1, +0.15), scale=.03)

        
        
        return task.cont

