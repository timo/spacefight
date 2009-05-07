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
  global playerlist
  # the "playerlist" is actually a list of Text objects that will just be rendered underneith each other.
  glEnable(GL_TEXTURE_2D) # without textures enabled, the texture data cannot be loaded.
  playerlist = [Text("Players:")] + [Text(c.name) for c in network.clients.values()]
  glDisable(GL_TEXTURE_2D)

chatitems = []

def updateChatLog():
  global chatitems
  # similar to the makePlayerList function
  glEnable(GL_TEXTURE_2D)
  chatitems = [Text(txt) for txt in network.chatlog[-10:]]
  glDisable(GL_TEXTURE_2D)

def rungame():
  global gsh
  global tickinterval
  global playerlist
  global chatitems

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
  except:
    print "usage:"
    print argv[0], "s port [ticksize=50]"
    print argv[0], "c addr port"
    print "s is for server mode, c is for client mode."
    sys.exit()

  if mode == "c":
    init()
  
  if mode == "s": # in server mode
    gs = network.initServer(int(port))
  elif mode == "c": # in client mode
    gs = network.initClient(addr,int(port)) 
  else:
    print "specify either 's' or 'c' as mode."
    sys.exit()
  
  # sets some stuff for the network sockets.
  network.setupConn()

  # this is important for the simulation.
  gs.tickinterval = tickinterval

  # in order to be reactive, the state history, which is currently server-side
  # only, has to incorporate input events at the time they actually happened,
  # rather than when they were received. Thus, a number of old gamestates is
  # preserved.
  #
  # on the client, the history simply deals with python-object changes that
  # update proxy objects.
  gsh = StateHistory(gs)

  # since the server is dedicated and headless now, we don't need a ship for it
  if mode == "c":
    # this is used to fix the camera on the ship and display information about
    # his ship to the player.
    myshipid = network.clients[None].shipid
    # a proxy is an object, that will automatically be updated by the gamestate
    # history object to always reflect the current object. This is accomplished
    # with black magic.
    localplayer = gs.getById(myshipid).getProxy(gsh)

  # yay! play the game!
  
  # inits pygame and opengl.
  running = True
  timer.wantedFrameTime = tickinterval * 0.001
  timer.startTiming()

  timer.gameSpeed = 1

  # this variable is used to determine, when it would be wise to skip
  # displaying a single gamestate, to catch up with the time the data
  # from the server is received.
  catchUpAccum = 0

  if mode == "c":
    playerlist = []
    makePlayerList()
    # used for chat.
    sentence = ""
    textthing = Text(sentence)

    def updateTextThing():
      glEnable(GL_TEXTURE_2D)
      textthing.renderText(sentence)
      glDisable(GL_TEXTURE_2D)

  while running:
    timer.startFrame()
    if mode == "c":
      for event in pygame.event.get():
        if event.type == QUIT:
          running = False

        if event.type == KEYDOWN:
          if event.key == K_ESCAPE:
            running = False

          # chat stuff
          elif K_a <= event.key <= K_z:
            sentence += chr(ord('a') + event.key - K_a)
            updateTextThing()
          elif event.key == K_SPACE:
            sentence += " "
            updateTextThing()
          elif event.key == K_BACKSPACE:
            sentence = sentence[:-1]
            updateTextThing()
          elif event.key == K_RETURN:
            if sentence:
              network.sendChat(sentence)
            sentence = ""
            updateTextThing()
          # end chat stuff

      # player control stuff
      kp = pygame.key.get_pressed()
      if kp[K_LEFT]:
        sendCmd("l")
      if kp[K_RIGHT]:
        sendCmd("r")
      if kp[K_UP]:
        sendCmd("t")
      if kp[K_SPACE]:
        sendCmd("f")
      # end player control stuff

      catchUpAccum += timer.catchUp
      # only if the catchUp time is below our patience or we run the server,
      # the gamestate should be rendered and calculated.
      if catchUpAccum < 2:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        with glIdentityMatrix():
          # put the player in the middle of the screen
          glTranslatef(25 - localplayer.position[0], 18.5 - localplayer.position[1], 0)
          # render everything
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
          with glMatrix():
            glScale(2, 2, 1)
            glTranslate(24, 540, 0)
            for msg in [textthing] + chatitems[::-1]:
              msg.draw()
              glTranslate(0, -17, 0)
          glDisable(GL_TEXTURE_2D)

        pygame.display.flip()

    # for the server, this lets new players in, distributes chat messages and
    # reacts to player inputs.
    network.pumpEvents()

    if mode == "c":
      if catchUpAccum > 2:
        print "catchUpAccum is", catchUpAccum
        catchUpAccum = 0

    timer.endFrame()

  # exit pygame
  if mode == "c":
    pygame.quit()
