from __future__ import with_statement
import struct
from math import pi, sin, cos, sqrt
from random import random
import copy

def scatter(lis, amount = 1):
  return [random() * amount - amount / 2 + lisi for lisi in lis]

class stateVars:
  def __init__(self, other):
    self.so = other

  def __enter__(self):
    self.so.statevars_enabled = True

  def __exit__(self, a, b, c):
    del self.so.statevars_enabled

class prescribedType:
  def __init__(self, other, type):
    self.so = other
    self.typ = type

    try:
      self.pretyp = self.so.statevars_pretype
    except: pass

  def __enter__(self):
    self.so.statevars_pretype = self.typ

  def __exit__(self, a, b, c):
    del self.so.statevars_pretype
    try:
      self.so.statevars_pretype = self.pretyp
    except: pass

class GameState:
  def __init__(self, data = None):
    self.objects = []
    self.tickinterval = 50 # in miliseconds
    self.clock = 0
    self.nextNewId = 0
    if data:
      self.deserialize(data)

  def copy(self):
    return copy.deepcopy(self)

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
      else:
        print "got unknown type:", type

      objlen = struct.calcsize(obj.statevars_format)
      objdat, data = data[:objlen], data[objlen:]

      try:
        obj.deserialize(objdat)
      except:
        print "could not deserialize", odata.__repr__(), "- chunk:", objdat.__repr__()
        raise

      obj.bind(self)
      self.objects.append(obj)

  def getById(self, id):
    for obj in self.objects:
      if obj.id == id:
        return obj

    raise Exception

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

  def control(self, commands):
    for id, cmd in commands:
      self.getById(id).command(cmd)

class StateObject(object):
  typename = "ab"#stract
  mass = 0
  def __init__(self):
    self.state = None
    self.statevars = ["id"]
    self.tuples = []
    self.statevars_format = "i"
    self.die = False
    self.id = 0

  def __setattr__(self, attr, value):

    def addAttr(attr, value):
      self.statevars.append(attr)
      try: self.statevars_format += self.statevars_pretype
      except AttributeError:
        if type(value) == int:
          self.statevars_format += "i"
        elif type(value) == float:
          self.statevars_format += "f"
        else:
          print "unknown serialization type:"
          print attr, value, type(value)
      object.__setattr__(self, attr, value)

    try:
      if self.statevars_enabled and not attr.startswith("statevars"):
        if type(value) == list:
          for i in range(len(value)):
            addAttr("_%s_%d" % (attr, i), value[i])
          self.tuples.append(attr)
          raise Exception
        else:
          addAttr(attr, value)
      else:
        raise Exception

    except:
      object.__setattr__(self, attr, value)

  def tick(self, dt):
    pass

  def bind(self, state):
    self.state = state
    return self

  def pre_serialize(self):
    for tup in self.tuples:
      thetup = object.__getattribute__(self, tup)
      for i in range(len(thetup)):
        object.__setattr__(self, "_%s_%d" % (tup, i), thetup[i])

  def post_deserialize(self):
    for tup in self.tuples:
      object.__setattr__(self, tup, [object.__getattribute__(self, "_%s_%d" % (tup, i)) for i in range(len(object.__getattribute__(self, tup)))])

  def serialize(self):
    self.pre_serialize()
    return struct.pack(self.statevars_format, *[getattr(self, varname) for varname in self.statevars])

  def collide(self, other, vec):
    pass

  def deserialize(self, data):
    try:
      vals = struct.unpack(self.statevars_format, data)
    except:
      print "error while unpacking a", self.typename, self.__repr__()
      raise
    for k, v in zip(self.statevars, vals):
      setattr(self, k, v)
    self.post_deserialize()

  def command(self, cmd):
    pass

  def getProxy(self, history):
    return StateObjectProxy(self, history)

class StateObjectProxy(object):
  def __init__(self, obj, history):
    self.proxy_id = obj.id
    self.proxy_objref = obj
    history.registerProxy(self)

  def proxy_update(self, gamestate):
    self.proxy_objref = gamestate.getById(self.id)
  
  def __getattr__(self, attr):
    if attr.startswith("proxy_"):
      return object.__getattribute__(self, attr)
    else:
      return self.proxy_objref.__getattribute__(attr)

  def __setattr__(self, attr, value):
    if attr.startswith("proxy_"):
      object.__setattr__(self, attr, value)
    else:
      self.objref.__setattr__(attr, value)

  def __repr__(self):
    return "<Proxy of %s>" % self.proxy_objref.__repr__()

class ShipState(StateObject):
  typename = "sp"
  mass = 1
  def __init__(self, data = None):
    StateObject.__init__(self)
    with stateVars(self):
      self.color = [random(), random(), random()]
      self.position = [0.0, 0.0]
      self.speed = [0.0, 0.0]        # in units per milisecond
      self.alignment = 0.0         # from 0 to 1
      self.timeToReload = 0      # in miliseconds
      self.reloadInterval = 500
      self.maxShield = 7500
      self.shield = 7500
      self.hull = 10000
      with prescribedType(self, "b"):
        self.team = 0

    self.size = 2
    self.firing = 0
    self.turning = 0
    self.thrust = 0

    if data:
      self.deserialize(data)

  def __repr__(self):
    return "<ShipState at %s, team %d, id %d>" % (self.position, self.team, self.id)

  def tick(self, dt):
    self.position[0] += self.speed[0] * dt
    self.position[1] += self.speed[1] * dt
    self.speed[0] *= 0.95 ** (dt * 0.01)
    self.speed[1] *= 0.95 ** (dt * 0.01)

    self.alignment += self.turning * dt * 0.0007
    self.turning = 0

    if self.thrust:
      self.speed = [self.speed[0] + cos(self.alignment * pi * 2) * 0.001, self.speed[1] + sin(self.alignment * pi * 2) * 0.001]
      self.thrust = 0

    if self.timeToReload > 0:
      self.timeToReload = max(0, self.timeToReload - dt)
    
    if self.firing and self.timeToReload == 0:
      bul = BulletState()
      face = scatter([cos(self.alignment * pi * 2) * 0.02, sin(self.alignment * pi * 2) * 0.02], 0.002)
      bul.position = [self.position[0] + face[0], self.position[1] + face[1]]
      bul.speed = [face[0] + self.speed[0], face[1] + self.speed[1]]
      bul.team = self.team
      self.state.spawn(bul)
      self.timeToReload = self.reloadInterval
      self.firing = False

    if self.shield < self.maxShield:
      self.shield += dt
    else:
      self.shield = self.maxShield

  def hitShield(self, damage = 1000):
    if self.shield < damage:
      self.shield, damage = 0, damage - self.shield
    else:
      self.shield, damage = self.shield - damage, 0

    self.hull -= damage

  def collide(self, other, vec):
    if other.typename == "bu":
      if other.team != self.team:
        if vec[0] != 0 and vec[1] != 0:
          len = sqrt(vec[0] * vec[0] + vec[1] * vec[1])
          self.speed[0] += vec[0] / len
          self.speed[1] += vec[1] / len
        self.hitShield()

  def command(self, cmd):
    if   cmd == "l": self.turning = -1
    elif cmd == "r": self.turning = 1
    elif cmd == "t": self.thrust = 1
    elif cmd == "f": self.firing = True

class BulletState(StateObject):
  typename = "bu"
  mass = -0.5
  def __init__(self, data = None):
    StateObject.__init__(self)
    with stateVars(self):
      self.position = [0, 0]
      self.speed = [0, 0]
      self.lifetime = 10000
      with prescribedType(self, "b"):
        self.team = 0

    self.state = None
    self.size = 1
   
    if data:
      self.deserialize(data)

  def tick(self, dt):
    self.position[0] += self.speed[0] * dt
    self.position[1] += self.speed[1] * dt
    self.lifetime -= dt
    if self.lifetime <= 0:
      self.die = True

  def collide(self, other, vec):
    if other.typename == self.typename:
      return
    try:
      if other.team != self.team:
        self.die = True
    except:
      self.die = True

class PlanetState(StateObject):
  typename = "ps"
  mass = 30
  def __init__(self, data = None):
    StateObject.__init__(self)

    with stateVars(self):
      self.position = [0, 0]
      self.speed = [0, 0] 
      self.color = [random(), random(), random()]
      self.size = 6
      with prescribedType(self, "b"):
        self.team = -1

    self.state = None

    if data:
      self.deserialize(data)

class StateHistory:
  def __init__(self, initialState):
    self.gsh = [initialState]
    self.inputs = [[]]
    self.maxstates = 20
    self.firstDirty = 0

    self.proxies = []
 
  def __getitem__(self, i):
    return self.gsh.__getitem__(i)

  def registerProxy(self, po):
    self.proxies.append(po)

  def updateProxies(self):
    for po in self.proxies:
      po.proxy_update(self.gsh[-1])

  def inject(self, id, command, clock = None):
    if clock:
      found = 0
      for i in range(len(self.gsh)):
        if self.gsh[i].clock == clock:
          found = i
          break
    else:
      found = len(self.gsh) - 1

    self.firstDirty = found
    self.inputs[found].append((id, command))

  def apply(self):
    for i in range(self.firstDirty + 1, len(self.gsh)):
      # this trick allows us to keep the gamestates
      # instead of regenerating them all the time
      self.gsh[i] = self.gsh[i - 1]
      self.gsh[i - 1] = self.gsh[i - 1].copy()
      self.gsh[i].control(self.inputs[i - 1])
      self.gsh[i].tick()

    if self.firstDirty + 1 - len(self.gsh):
      self.updateProxies()
    self.firstDirty = len(self.gsh)

    if len(self.gsh) < self.maxstates:
      self.gsh = self.gsh[:-1] + [self.gsh[-1].copy(), self.gsh[-1]]
      self.inputs.append([])
    else:
      # again: make sure to keep the gamestate at the top intact!
      self.gsh = self.gsh[1:-1] + [self.gsh[-1].copy(), self.gsh[-1]]
      self.inputs = self.inputs[1:] + [[]]

    self.gsh[-1].control(self.inputs[-2])
    self.gsh[-1].tick()
