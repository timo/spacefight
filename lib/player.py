from __future__ import with_statement
from OpenGL.GL import *
from with_opengl import glPrimitive
from math import pi

class Ship:
  def __init__(self, color = (1, 0, 0)):
    self.color = color
    self.position = [0, 0]
    self.speed = [0, 1]
    self.alignment = 0

  def render(self):
    glTranslate(*self.position + [0])
    glRotatef(self.alignment * 360, 0, 0, 1)
    with glPrimitive(GL_LINE_LOOP):
      glColor(*self.color)
      glVertex2f(0, -1)
      glVertex2f(0.5, 1)
      glVertex2f(0, 0.5)
      glVertex2f(-0.5, 1)

  def turn(self, amount):
    self.alignment = (self.alignment + amount) % 1.0

  def heartbeat(self, dt):
    self.position[0] += self.speed[0] * dt
    self.position[1] += self.speed[1] * dt
    self.speed[0] *= 1.0 - (0.1 * dt)
    self.speed[1] *= 1.0 - (0.1 * dt)

