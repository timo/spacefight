#!/usr/bin/python
import random
from timing import timer

from math import pi

import pygame
from pygame.locals import *
from OpenGL.GL import *

from with_opengl import glMatrix, glPrimitive

from time import sleep

# don't initialise sound stuff plzkthxbai
pygame.mixer = None

screen = None
screensize = (1024, 786)

def setres((width, height)):
  """res = tuple
sets the resolution and sets up the projection matrix"""
  if height==0:
    height=1
  glViewport(0, 0, width, height)
  glMatrixMode(GL_PROJECTION)
  glLoadIdentity()
  glOrtho(0, width / 32, height / 32, 0, -10, 10)
  glMatrixMode(GL_MODELVIEW)
  glLoadIdentity()

def init():
  # initialize everything
  pygame.init()
  screen = pygame.display.set_mode(screensize, OPENGL|DOUBLEBUF)
  setres(screensize)

  # some OpenGL magic!
  glEnable(GL_BLEND)
  glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
  glEnable(GL_LINE_SMOOTH)
  glEnable(GL_TEXTURE_2D)
  glClearColor(0,0,0.0,1.0)

def rungame():
  # init all stuff
  init()

  # yay! play the game!
  running = True
  timer.startTiming()

  timer.gameSpeed = 1

  while running:
    timer.startFrame()
    for event in pygame.event.get():
      if event.type == QUIT:
        running = False

      if event.type == KEYDOWN:
        if event.key == K_ESCAPE:
          running = False

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    with glMatrix:
      # do stuff
      lvl.scroller.scroll()
      lvl.draw()
      with glMatrix:
        #lvl.scroller.scroll()
        plr.draw()
      glPopMatrix()

    with glIdentityMatrix:
      glTranslatef(5, 5, 0)
      glScalef(1./32, 1./32, 1)
      # do gui stuff here

    pygame.display.flip()
    timer.endFrame()

  # exit pygame
  pygame.quit()
