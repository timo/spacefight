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
screensize = (640, 480)

def setres((width, height)):
  """res = tuple
sets the resolution and sets up the projection matrix"""
  if height==0:
    height=1
  glViewport(0, 0, width, height)
  glMatrixMode(GL_PROJECTION)
  glLoadIdentity()
  glOrtho(0, 1600 / 32, 1200 / 32, 0, -10, 10) # those are resolution-independent to be fair
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
  # init all stuff
  init()

  # try to connect to the other party

  mode = "a"
  
  
  while mode not in "sScC":
    print "please choose from (s)erver or (c)lient"
    mode = raw_input().lower()
  
#  if mode == "c":
#    print "please input the client port"
#    cport = raw_input()
#    print "please input the server address"
#    addr = raw_input()
#
#  print "please input the port"
#  port = raw_input()

  port = cport = 7777
  addr = "127.0.0.1"

  if mode == "s":
    server = socket(AF_INET, SOCK_DGRAM)
    server.bind(("", int(port)))
    print "now waiting for client"
    data = server.recvfrom(4096)
    print data
    conn = socket(AF_INET, SOCK_DGRAM)
    conn.connect(data[1])
    
    conn.send("ack")

    print "awaiting player ship."

    shipdata = conn.recv(4096)

    remoteship = ShipState(shipdata)

    gs = GameState()
    localplayer = ShipState()
    localplayer.position = [0, 0]
    localplayer.alignment = random()
    localplayer.firing = 1
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
    conn.sendto("HELLO %s", (addr, int(port)))
    print "hello sent."

    data = conn.recvfrom(4096)

    print data[0], "gotten as response"

    conn.connect(data[1])

    plp = ShipState() # proposed local player state
    plp.position = [random() * 10, random() * 10]
    plp.alignment = random()
    plp.color = (0, 1, 0)
    conn.send(plp.serialize())

    print "awaiting state response..."

    gs = GameState(conn.recv(4096))

  conn.setblocking(0)

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

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    with glIdentityMatrix():
      # do stuff
      glTranslatef(10, 10, 0)
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
        control = conn.recv(4096)
        if control[0] == "l":
          remoteship.turning = -1
        elif control[0] == "r":
          remoteship.turning = 1
        elif control[0] == "t":
          remoteship.thrust = 1
        else:
          print "gor unknown message:", control.__repr__()
      except error:
       pass
    elif mode == "c":
      conn.setblocking(1)
      gs.deserialize(conn.recv(4096))
      conn.setblocking(0)

    timer.endFrame()

  # exit pygame
  pygame.quit()
