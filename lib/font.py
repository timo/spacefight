from __future__ import with_statement
from OpenGL.GL import *
from with_opengl import glPrimitive
import pygame
from pygame.locals import *
from math import log, ceil

pygame.font.init()
thefont = pygame.font.SysFont("arial", 26)

class Text:
  def __init__(self, thetext):
    self.glID = None
    self.rgba = (1., 1., 1., 1.)
    self.renderText(thetext)

  def renderText(self, thetext):
    self.thetext = thetext
    text = thefont.render(thetext, True, (255, 255, 255)).convert_alpha()
    npo2 = lambda x: int(2 ** ceil(log(x, 2)))
    (w, h) = (npo2(text.get_width()), npo2(text.get_height()))

    bigSurface = pygame.Surface((w, h)).convert_alpha()
    bigSurface.fill((0, 0, 0, 0), (0, 0, w, h))
    bigSurface.blit(text, (0, 0, text.get_width(), text.get_height()))

    self.texw = bigSurface.get_width()
    self.texh = bigSurface.get_height()

    self.w = text.get_width()
    self.h = text.get_height()

    del text

    if not self.glID:
      self.glID = glGenTextures(1)
    self.bind()

    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,     GL_CLAMP)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,     GL_CLAMP)

    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 
                 self.texw, self.texh,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, 
                 pygame.image.tostring(bigSurface, "RGBA", 0))

  def bind(self):
    glBindTexture(GL_TEXTURE_2D, self.glID)

  def draw(self):
    glEnable(GL_TEXTURE_2D)
    self.bind()
    texw = self.w / float(self.texw)
    texh = self.h / float(self.texh)

    glColor4fv(self.rgba)
    with glPrimitive(GL_QUADS):
      glTexCoord2f(0, 0)
      glVertex2f(0, 0)

      glTexCoord2f(0, texh)
      glVertex2f(0, self.h)

      glTexCoord2f(texw, texh)
      glVertex2f(self.w, self.h)

      glTexCoord2f(texw, 0)
      glVertex2f(self.w, 0)

  def __del__(self):
    glDeleteTextures(self.glID)
