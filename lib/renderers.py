from __future__ import with_statement
import gamestate
from OpenGL.GL import *
from with_opengl import glPrimitive, glMatrix
from math import pi, sin, cos, sqrt, log

def frange(start, end, step):
  curr = start
  while curr < end:
    yield curr
    curr += step

def renderGameGrid(player):
  with glPrimitive(GL_LINES):
    for x in range(int(player.position[0] - 30), int(player.position[0] + 30), 1):
      if x % 10 == 0:
        glColor(0.3, 0.3, 0, 1)
      elif x % 10 == 5:
        glColor(0.15, 0.15, 0, 1)
      else:
        glColor(0.05, 0.05, 0, 1)
      glVertex2f(x, -100)
      glVertex2f(x, 100)
    for y in range(int(player.position[1] - 30), int(player.position[1] + 30), 1):
      if y % 10 == 0:
        glColor(0.3, 0.3, 0)
      elif y % 10 == 5:
        glColor(0.15, 0.15, 0)
      else:
        glColor(0.05, 0.05, 0)
      glVertex2f(-100, y)
      glVertex2f(100, y)


def renderWholeState(state):
  for obj in state.objects:
    for cls, met in methodMap.items():
      if isinstance(obj, cls):
        with glMatrix():
          met(obj)

def renderShip(ship):
  glTranslate(*ship.position + [0])
  glRotatef(ship.alignment * 360, 0, 0, 1)
  with glPrimitive(GL_POLYGON):
    glColor(*ship.color)
    glVertex2f(1, 0)
    glVertex2f(-1, 0.5)
    glVertex2f(-0.5, 0)
    glVertex2f(-1, -0.5)

  with glPrimitive(GL_LINE_LOOP):
    for i in frange(0, ship.hull / 10000., 0.05):
      glVertex2f(sin(i * 2 * pi) * 2.1, cos(i * 2 * pi) * 2.1)

  if ship.shield < ship.maxShield and ship.shield > 0:
    amount = 1.0 * ship.shield / ship.maxShield
    with glPrimitive(GL_LINE_LOOP):
      glColor(1.0 - amount, amount, 0, sqrt(1 + log((amount + 0.1) * 0.9, 10) / 2.5))
      for i in range(0, 360, 36):
        glVertex2f(sin(i / 180. * pi) * 2, cos(i / 180. * pi) * 2)

def renderBullet(bul):
  glTranslate(*bul.position + [0])
  glScale(0.2, 0.2, 0.2)
  with glPrimitive(GL_POLYGON):
    glColor(0, 0, 1)
    for posi in [0, 0.4, 0.8, 0.2, 0.6]:
      glVertex2f(sin(posi * 2 * pi), cos(posi * 2 * pi))

def renderPlanet(pla):
  glTranslate(*pla.position + [0])
  with glPrimitive(GL_POLYGON):
    glColor(0, 0, 0.7)
    for i in range(0, 360, 36):
      glVertex2f(sin(i / 180. * pi) * pla.size, cos(i / 180. * pi) * pla.size)

methodMap = {gamestate.ShipState: renderShip,
             gamestate.BulletState: renderBullet,
             gamestate.PlanetState: renderPlanet}
