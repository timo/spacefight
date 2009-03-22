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
    self.nextNewId = 0
    if data:
      self.deserialize(data)

  def tick(self):
    self.clock += self.tickinterval
    for o in self.objects:
      o.tick(self.tickinterval)
      if o.die:
        self.objects.remove(o)

    self.doGravity(self.tickinterval)
    self.doCollisions(self.tickinterval)

  def spawn(self, object):
    object.id = self.nextNewId
    self.nextNewId += 1
    self.objects.append(object.bind(self))

  def serialize(self):
    data = struct.pack("i", self.clock)
    data = data + "".join(obj.typename + obj.serialize() for obj in self.objects)
    return data

  def deserialize(self, data):
    self.objects = []
    odata = data
    self.clock, data = struct.unpack("i", data[:4])[0], data [4:]
    while len(data) > 0:
      type, data = data[:2], data[2:]
      
      if type == "sp":
        obj = ShipState()
      elif type == "bu":
        obj = BulletState()
      elif type == "ps":
        obj = PlanetState()

      objlen = struct.calcsize(obj.stateformat)
      objdat, data = data[:objlen], data[objlen:]

      try:
        obj.deserialize(objdat)
      except:
        print "could not deserialize", odata.__repr__(), "- chunk:", objdat.__repr__()
        raise

      self.objects.append(obj)

  def getById(self, id):
    return [obj for obj in self.objects if obj.id == id][0]

  def doGravity(self, dt):
    for a in self.objects:
      for b in self.objects:
        if b == a: continue

        dv = [a.position[i] - b.position[i] for i in range(2)]
        lns = dv[0] * dv[0] + dv[1] * dv[1]
        con = -0.000001 * a.mass * b.mass / lns

        a.speed[0] += con * dv[0] * dt
        a.speed[1] += con * dv[1] * dt
        b.speed[0] -= con * dv[0] * dt
        b.speed[1] -= con * dv[1] * dt

  def doCollisions(self, dt):
    for a in self.objects:
      for b in self.objects:
        if a == b: continue

        dv = [a.position[i] - b.position[i] for i in range(2)]
        lns = dv[0] * dv[0] + dv[1] * dv[1]

        if lns < (a.size + b.size) ** 2:
          a.collide(b, dv)
          b.collide(a, dv)

class StateObject(object):
  typename = "ab"#stract
  mass = 0
  def __init__(self):
    self.state = None
    self.statevars = []
    self.stateformat = ""
    self.die = False
    self.id = 0
 
  def tick(self, dt):
    pass

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

  def collide(self, other, vec):
    pass

  def deserialize(self, data):
    try:
      vals = struct.unpack(self.stateformat, data)
    except:
      print "error while unpacking a", self.typename, self.__repr__()
      raise
    for k, v in zip(self.statevars, vals):
      setattr(self, k, v)
    self.post_deserialize()

class ShipState(StateObject):
  typename = "sp"
  mass = 1
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
    self.size = 2
    self.maxShield = 7500
    self.shield = 7500
    self.hull = 10000

    self.statevars = ["id", "r", "g", "b", "x", "y", "alignment", "timeToReload", "reloadInterval", "maxShield", "shield", "hull", "team"]
    self.stateformat = "i6f5ib"

    if data:
      self.deserialize(data)

  def pre_serialize(self):
    self.x, self.y = self.position
    self.r, self.g, self.b = self.color

  def post_deserialize(self):
    self.position = [self.x, self.y]
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
      bul.team = self.team
      self.state.spawn(bul)
      self.timeToReload = self.reloadInterval
      self.firing = False

    if self.shield < self.maxShield:
      self.shield += dt
    else:
      self.shield = self.maxShield

  def hitShield(self, damage = 1000):
    print "absorbing", damage, "damage on a shield with", self.shield, "energy and a hull of", self.hull
    if self.shield < damage:
      self.shield, damage = 0, damage - self.shield
      print "shields did not suffice. damage:", damage, "shields:", self.shield
    else:
      self.shield, damage = self.shield - damage, 0
      print "shields sufficed. damage:", damage, "shields:", self.shield

    self.hull -= damage
    print "hull:", self.hull

  def collide(self, other, vec):
    if other.typename == "bu":
      if other.team != self.team:
        self.speed[0] += vec[0]
        self.speed[1] += vec[1]
        self.hitShield()

class BulletState(StateObject):
  typename = "bu"
  mass = -0.5
  def __init__(self, data = None):
    StateObject.__init__(self)
    self.position = [0, 0]
    self.speed = [0, 0]
    self.size = 1
    self.team = 0
    self.lifetime = 10000
    self.state = None
   
    self.statevars = ["id", "x", "y", "sx", "sy", "team", "lifetime"]
    self.stateformat = "i4fbi"

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

  def collide(self, other, vec):
    try:
      if other.team != self.team:
        self.die = True
    except:
      self.die = True

class PlanetState(StateObject):
  typename = "ps"
  mass = 50
  def __init__(self, data = None):
    StateObject.__init__(self)

    self.position = [0, 0]
    self.speed = [0, 0] 
    self.size = 6
    self.team = 0

    self.state = None

    self.statevars = ["id", "x", "y", "size", "team"]
    self.stateformat = "i3fb"

    if data:
      self.deserialize(data)

  def pre_serialize(self):
    self.x, self.y = self.position

  def post_deserialize(self):
    self.position = [self.x, self.y]
