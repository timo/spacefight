#!/usr/bin/python
from __future__ import with_statement

import pygame
from pygame.locals import *
from OpenGL.GL import *
from with_opengl import glMatrix, glIdentityMatrix, glPrimitive

from time import sleep
from random import random
from math import pi, sin, cos
from socket import *
from sys import argv

from timing import timer
from gamestate import *
import renderers
from font import Text
from network import sendCmd
import network

# don't initialise sound stuff plzkthxbai
pygame.mixer = None

screen = None
screensize = (800, 600)

gsh = None # this will hold a Gamestate History object.
tickinterval = 0

def setres((width, height)):
  """res = tuple
sets the resolution and sets up the projection matrix"""
  if height==0:
    height=1
  glViewport(0, 0, width, height)
  glMatrixMode(GL_PROJECTION)
  glLoadIdentity()
  glOrtho(0, 50, 37, 0, -10, 10) # those are resolution-independent to be fair
  #     x
  #  0---->
  #  |
  # y|
  #  v
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
  glEnable(GL_TEXTURE_2D)
  glClearColor(0.1,0.1,0.0,1.0)

def makePlayerList():
  glEnable(GL_TEXTURE_2D)
  playerlist = [Text("Players:")] + [Text(c.name) for c in network.clients.values()]
  glDisable(GL_TEXTURE_2D)

def rungame():
  global gsh
  global tickinterval

  tickinterval = 50

  try:
    mode = argv[1]
    if mode == "s":
      port = argv[2]
      if len(argv) > 3:
        tickinterval = int(argv[3])
    elif mode == "c":
      addr = argv[2]
      port = argv[3]
      if len(argv) > 4:
        cport = argv[4]
      else:
        cport = port
  except:
    print "usage:"
    print argv[0], "s port [ticksize=50]"
    print argv[0], "c addr port [clientport]"
    print "s is for server mode, c is for client mode."
    sys.exit()

  if mode == "s":
    gs = network.initServer(int(port))
  elif mode == "c":
    gs = network.initClient(addr,int(port), int(cport)) 

  network.setupConn()

  gs.tickinterval = tickinterval

  gsh = StateHistory(gs)
  
  myshipid = network.clients[None].shipid
  localplayer = gs.getById(myshipid).getProxy(gsh)

  # yay! play the game!
  
  # init all stuff
  init()
  running = True
  timer.wantedFrameTime = tickinterval * 0.001
  timer.startTiming()

  timer.gameSpeed = 1

  catchUpAccum = 0

  glEnable(GL_TEXTURE_2D)
  playerlist = []
  glDisable(GL_TEXTURE_2D)

  while running:
    timer.startFrame()
    for event in pygame.event.get():
      if event.type == QUIT:
        running = False

      if event.type == KEYDOWN:
        if event.key == K_ESCAPE:
          running = False

    kp = pygame.key.get_pressed()
    if kp[K_LEFT]:
      sendCmd("l")
    if kp[K_RIGHT]:
      sendCmd("r")
    if kp[K_UP]:
      sendCmd("t")
    if kp[K_SPACE]:
      sendCmd("f")

    catchUpAccum += timer.catchUp
    if catchUpAccum < 2 or network.mode == "s":
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
      with glIdentityMatrix():
        # do stuff
        glTranslatef(25 - localplayer.position[0], 18.5 - localplayer.position[1], 0)
        renderers.renderGameGrid(localplayer)
        renderers.renderWholeState(gsh[-1])

      with glIdentityMatrix():
        glScalef(1./32, 1./32, 1)
        # do gui stuff here
        with glMatrix():
          glScale(3, 3, 1)
          for pli in playerlist:
            pli.draw()
            glTranslate(0, 16, 0)
        glDisable(GL_TEXTURE_2D)

      pygame.display.flip()

    network.pumpEvents()

    if catchUpAccum > 2:
      catchUpAccum = 0
      print "skipped a gamestate update."

    timer.endFrame()

  # exit pygame
  pygame.quit()
