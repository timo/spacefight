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

from timing import timer
from gamestate import *
import renderers
from sys import argv

# don't initialise sound stuff plzkthxbai
pygame.mixer = None

screen = None
screensize = (800, 600)

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
  glEnable(GL_LINE_SMOOTH)
  glEnable(GL_TEXTURE_2D)
  glClearColor(0,0,0.0,1.0)

def rungame():

  # try to connect to the other party

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

  if mode == "s":
    server = socket(AF_INET, SOCK_DGRAM)
    server.bind(("", int(port)))
    print "now waiting for client"
    data = server.recvfrom(4096)
    print data
    conn = socket(AF_INET, SOCK_DGRAM)
    conn.connect(data[1])
    
    conn.send("tickinterval:" + str(tickinterval))

    print "awaiting player ship."

    shipdata = conn.recv(4096)

    remoteship = ShipState(shipdata)

    gs = GameState()
    localplayer = ShipState()
    localplayer.position = [0, 0]
    localplayer.alignment = random()
    gs.spawn(localplayer)
    gs.spawn(remoteship)
    print "transmitting state"
    conn.send(gs.serialize())
  
  elif mode == "c":
    conn = socket(AF_INET, SOCK_DGRAM)
    try:
      conn.bind(("", int(cport)))
    except:
      try:
        conn.bind(("", int(cport) + 1))
      except:
        conn.bind(("", int(cport) + 2))
    

    conn.settimeout(10)
    data = ""
    while not data:
      try:
        conn.sendto("HELLO %s", (addr, int(port)))
        print "hello sent."
        sleep(5)
        data = conn.recvfrom(4096)
      except error:
        pass

    

    print data[0], "gotten as response"
    tickinterval = int(data[0].split(":")[1])
    print "tickinterval is now", tickinterval

    conn.connect(data[1])

    plp = ShipState() # proposed local player state
    plp.position = [random() * 10, random() * 10]
    plp.alignment = random()
    plp.color = (0, 1, 0)
    conn.send(plp.serialize())

    print "awaiting state response..."

    gs = GameState(conn.recv(4096))
    localplayer = gs.objects[1]
  
  conn.setblocking(0)
  gs.tickinterval = tickinterval


  # yay! play the game!
  
  # init all stuff
  init()
  running = True
  timer.wantedFrameTime = tickinterval * 0.001
  timer.startTiming()

  timer.gameSpeed = 1

  catchUpAccum = 0

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
      if mode == "s":
        localplayer.turning = -1
      else:
        conn.send("l")
    if kp[K_RIGHT]:
      if mode == "s":
        localplayer.turning = 1
      else:
       conn.send("r")
    if kp[K_UP]:
      if mode == "s":
        localplayer.thrust = 1
      else:
        conn.send("t")
    if kp[K_SPACE]:
      if mode == "s":
        localplayer.firing = True
      else:
        conn.send("f")

    catchUpAccum += timer.catchUp
    if catchUpAccum < 2 or mode == "s":
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
      with glIdentityMatrix():
        # do stuff
        glTranslatef(25 - localplayer.position[0], 18.5 - localplayer.position[1], 0)
        renderers.renderWholeState(gs)

      with glIdentityMatrix():
        glTranslatef(5, 5, 0)
        glScalef(1./32, 1./32, 1)
        # do gui stuff here

      pygame.display.flip()

      if mode == "s":
        gs.tick()
        conn.send(gs.serialize())
        try:
          while True:
            control = conn.recv(4096)
            if control[0] == "l":
              remoteship.turning = -1
            elif control[0] == "r":
              remoteship.turning = 1
            elif control[0] == "t":
              remoteship.thrust = 1
            elif control[0] == "f":
              remoteship.firing = True
            else:
              print "gor unknown message:", control.__repr__()
        except error:
         pass
      elif mode == "c":
        gsdat = ""
        while not gsdat:
          try:
            gsdat = conn.recv(4096)
          except error:
            pass

        last = False
        while not last:
          try: 
            gsdat = conn.recv(4096)
          except error:
            last = True

        gs.deserialize(gsdat)
        localplayer = gs.objects[1]

    if catchUpAccum > 2:
      catchUpAccum = 0
      print "skipped a gamestate update."

    timer.endFrame()

  # exit pygame
  pygame.quit()
