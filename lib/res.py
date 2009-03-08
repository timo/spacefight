import pygame
from pygame.locals import *
from OpenGL.GL import *

class Texture:
  def __init__(self, texturename):
    self.name = texturename
    self.Surface = pygame.image.load('data/gfx/%s.png' % texturename)

    (self.w, self.h) = self.Surface.get_rect()[2:]

    self.glID = glGenTextures(1)
    self.bind()

    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,     GL_CLAMP)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,     GL_CLAMP)

    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 
                 self.w, self.h,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, 
                 pygame.image.tostring(self.Surface, "RGBA", 0))

  def bind(self):
    glBindTexture(GL_TEXTURE_2D, self.glID)

class dummyTexture(Texture):
  def __init__(self):
    self.Surface = pygame.Surface((64, 64)).convert_alpha()
    for x in range(16):
      for y in range(16):
        if (x + y) % 2:
          col = (x * 16, 0, y * 16, 255)
        else:
          col = (255, 255, 255, 128)
        self.Surface.fill(col, (x * 4, y * 4, 4, 4))

    (self.w, self.h) = (64, 64)

    self.glID = glGenTextures(1)
    self.bind()

    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,     GL_CLAMP)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,     GL_CLAMP)

    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 
                 self.w, self.h,
                 0, GL_RGBA, GL_UNSIGNED_BYTE, 
                 pygame.image.tostring(self.Surface, "RGBA", 0))

textures = {}
def getTexture(texturename):
  global textures
  if texturename not in textures:
    if texturename == "__dummy__":
      textures[texturename] = dummyTexture()
    else:
      textures[texturename] = Texture(texturename)
  return textures[texturename]
