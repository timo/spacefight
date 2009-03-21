import struct
from math import pi, sin, cos
from random import random

def scatter(lis, amount = 1):
  return [random() * amount - amount / 2 + lisi for lisi in lis]

class GameState:
  def __init__(self, data = None):
    self.objects = []
    self.tickinterval = 50 # in miliseconds
    self.clock = 0
    if data:
      self.deserialize(data)

  def tick(self):
    self.clock += self.tickinterval
    for o in self.objects:
      o.tick(self.tickinterval)
      if o.die:
        self.objects.remove(o)

  def spawn(self, object):
    self.objects.append(object.bind(self))

  def serialize(self):
    data = struct.pack("i", self.clock)
    data = data + "".join(obj.typename + obj.serialize() for obj in self.objects)
    return data

  def deserialize(self, data):
    self.objects = []
    self.clock, data = struct.unpack("i", data[:4])[0], data [4:]
    while len(data) > 0:
      type, data = data[:2], data[2:]
      
      if type == "sp":
        obj = ShipState()
      elif type == "bu":
        obj = BulletState()
      
      objlen = struct.calcsize(obj.stateformat)
      objdat, data = data[:objlen], data[objlen:]

      obj.deserialize(objdat)

      self.objects.append(obj)

class StateObject(object):
  typename = "ab"#stract
  def __init__(self):
    self.state = None
    self.statevars = []
    self.stateformat = ""
    self.die = False
  
  def bind(self, state):
    self.state = state
    return self

  def pre_serialize(self):
    pass

  def post_deserialize(self):
    pass

  def serialize(self):
    self.pre_serialize()
    return struct.pack(self.stateformat, *[getattr(self, varname) for varname in self.statevars])

  def deserialize(self, data):
    vals = struct.unpack(self.stateformat, data)
    for k, v in zip(self.statevars, vals):
      setattr(self, k, v)
    self.post_deserialize()

class ShipState(StateObject):
  typename = "sp"
  def __init__(self, data = None):
    StateObject.__init__(self)
    self.color = (1, 0, 0)
    self.position = [0, 0]
    self.speed = [0, 0]        # in units per milisecond
    self.alignment = 0         # from 0 to 1
    self.turning = 0
    self.thrust = 0
    self.timeToReload = 0      # in miliseconds
    self.reloadInterval = 1000
    self.firing = 0
    self.team = 0

    self.statevars = ["r", "g", "b", "x", "y", "sx", "sy", "alignment", "timeToReload", "reloadInterval", "team"]
    self.stateformat = "10f1b"

    if data:
      self.deserialize(data)

  def pre_serialize(self):
    self.x, self.y = self.position
    self.sx, self.sy = self.speed
    self.r, self.g, self.b = self.color

  def post_deserialize(self):
    self.position = [self.x, self.y]
    self.speed = [self.sx, self.sy]
    self.color = (self.r, self.g, self.b)

  def tick(self, dt):
    self.position[0] += self.speed[0] * dt
    self.position[1] += self.speed[1] * dt
    self.speed[0] *= 0.95 ** (dt * 0.01)
    self.speed[1] *= 0.95 ** (dt * 0.01)

    self.alignment += self.turning * dt * 0.0007
    self.turning = 0

    if self.thrust:
      self.speed = [cos(self.alignment * pi * 2) * 0.01, sin(self.alignment * pi * 2) * 0.01]
      self.thrust = 0

    if self.timeToReload > 0:
      self.timeToReload = max(0, self.timeToReload - dt)
    
    if self.firing and self.timeToReload == 0:
      bul = BulletState()
      face = scatter([cos(self.alignment * pi * 2) * 0.02, sin(self.alignment * pi * 2) * 0.02], 0.002)
      bul.position = [self.position[0] + face[0], self.position[1] + face[1]]
      bul.speed = face
      self.state.spawn(bul)
      self.timeToReload = self.reloadInterval
      self.firing = False

class BulletState(StateObject):
  typename = "bu"
  def __init__(self, data = None):
    StateObject.__init__(self)
    self.position = [0, 0]
    self.speed = [0, 0]
    self.team = 0
    self.lifetime = 10000
    self.state = None
   
    self.statevars = ["x", "y", "sx", "sy", "team", "lifetime"]
    self.stateformat = "4fbi"

    if data:
      self.deserialize(data)

  def pre_serialize(self):
    self.x, self.y = self.position
    self.sx, self.sy = self.speed

  def post_deserialize(self):
    self.position = [self.x, self.y]
    self.speed = [self.sx, self.sy]

  def tick(self, dt):
    self.position[0] += self.speed[0] * dt
    self.position[1] += self.speed[1] * dt
    self.lifetime -= dt
    if self.lifetime <= 0:
      self.die = True
