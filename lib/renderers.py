from __future__ import with_statement
import gamestate
from OpenGL.GL import *
from with_opengl import glPrimitive, glMatrix
from math import pi, sin, cos

def renderWholeState(state):
  for obj in state.objects:
    for cls, met in methodMap.items():
      if isinstance(obj, cls):
        with glMatrix():
          met(obj)

def renderShip(ship):
  glTranslate(*ship.position + [0])
  glRotatef(ship.alignment * 360, 0, 0, 1)
  with glPrimitive(GL_LINE_LOOP):
    glColor(*ship.color)
    glVertex2f(1, 0)
    glVertex2f(-1, 0.5)
    glVertex2f(-0.5, 0)
    glVertex2f(-1, -0.5)

def renderBullet(bul):
  glTranslate(*bul.position + [0])
  glScale(0.2, 0.2, 0.2)
  with glPrimitive(GL_LINE_LOOP):
    glColor(0, 0, 1)
    for posi in [0, 0.4, 0.8, 0.2, 0.6]:
      glVertex2f(sin(posi * 2 * pi), cos(posi * 2 * pi))

methodMap = {gamestate.ShipState: renderShip,
             gamestate.BulletState: renderBullet}