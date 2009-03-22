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

TYPE_STATE = "g"
TYPE_SHAKE = "c"
TYPE_CHAT  = "m"
TYPE_INPUT = "i"

SHAKE_HELLO  = "h"
SHAKE_SHIP   = "s"
SHAKE_YOURID = "i"

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

class Client():
  def __init__(self):
    self.shipid = None
    self.name = ""
    self.socket = None

def rungame():

  # try to connect to the other party

  tickinterval = 50

  clients = {}
  nextTeam = 1

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
    
    gs = GameState()
    localplayer = ShipState()
    localplayer.position = [random() * 100 - 50, random() * 100 - 50]
    localplayer.alignment = random()
    localplayer.team = 0
    gs.spawn(localplayer)
    planet = PlanetState()
    planet.position = [random() * 200 - 100, random() * 200 - 100]
    gs.spawn(planet)

    myshipid = localplayer.id

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
        conn.sendto(struct.pack("cc32s", TYPE_SHAKE, SHAKE_HELLO, gethostname()), (addr, int(port)))
        print "hello sent."
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
    conn.send(TYPE_SHAKE + SHAKE_SHIP + plp.serialize())

    print "awaiting state response..."

    shipid = conn.recv(4096)
    if shipid[1] == TYPE_SHAKE and shipid[2] == TYPE_YOURID:
      myshipid = struct.unpack("i", shipid[2:])
    else:
      print "oops. what?"
      print shipid
      sys.exit()

    gs = GameState()
    localplayer = ShipState()

  try:
    conn.setblocking(0)
  except:
    server.setblocking(0)
  gs.tickinterval = tickinterval

  gsh = StateHistory(gs)

  # yay! play the game!
  
  # init all stuff
  init()
  running = True
  timer.wantedFrameTime = tickinterval * 0.001
  timer.startTiming()

  timer.gameSpeed = 1

  catchUpAccum = 0

  def sendCmd(cmd):
    if mode == "c":
      conn.send(struct.pack("cic", TYPE_INPUT, gsh[-1].clock, cmd))
    else:
      gsh.inject(myshipid, cmd)

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
    if catchUpAccum < 2 or mode == "s":
      glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
      with glIdentityMatrix():
        # do stuff
        glTranslatef(25 - localplayer.position[0], 18.5 - localplayer.position[1], 0)
        renderers.renderGameGrid(localplayer)
        renderers.renderWholeState(gsh[-1])

      with glIdentityMatrix():
        glTranslatef(5, 5, 0)
        glScalef(1./32, 1./32, 1)
        # do gui stuff here

      pygame.display.flip()

      if mode == "s":
        try:
          while True:
            msg, sender = server.recvfrom(4096)
            type = msg[0]
            if type == TYPE_INPUT:
              clk, cmd = struct.unpack("ic", msg[1:])

              gsh.inject(clients[sender].shipid, cmd, clk)
            
            elif type == TYPE_SHAKE:
              # HANDSHAKE CODE BEGIN
              if sender in clients:
                if msg[1] == SHAKE_SHIP:
                  remoteship = ShipState(msg[2:])
                  remoteship.team = nextTeam
                  nextTeam += 1
                  gsh[-1].spawn(remoteship)
                  clients[sender].shipid = remoteship.id
                  clients[sender].send(TYPE_SHAKE + TYPE_YOURID + struct.pack("i", clients[sender].shipid))

              else:
                if msg[1] == SHAKE_HELLO:
                  nc = Client()
                  client.name = msg[2:]
                  nc.socket = socket(AF_INET, SOCK_DGRAM)
                  nc.socket.connect(sender)

                  nc.socket.send(TYPE_SHAKE + "tickinterval:" + str(tickinterval))
                  clients[sender] = nc

        except error:
          pass

        gsh.apply()
        localplayer = gsh[-1].getById(myshipid)
        msg = TYPE_STATE + gsh[-1].serialize()
        for c in clients:
          c.socket.send(msg)

      elif mode == "c":
        gsdat = ""
        while not gsdat:
          try:
            data = conn.recv(4096)
            if data[0] == "g":
              gsdat = data
            elif data[0] == "m":
              print data[1:]
          except error:
            pass

        last = False
        while not last:
          try: 
            gsdat = conn.recv(4096)
          except error:
            last = True

        gsh[-1].deserialize(gsdat)
        localplayer = gsh[-1].getById(myshipid)

    if catchUpAccum > 2:
      catchUpAccum = 0
      print "skipped a gamestate update."

    timer.endFrame()

  # exit pygame
  pygame.quit()
