from __future__ import with_statement
import struct
from math import pi, sin, cos, sqrt
from random import random
import copy

# randomly bend a vector around
def scatter(lis, amount = 1):
  return [random() * amount - amount / 2 + lisi for lisi in lis]

serializeKnowledgeBase =  {}

# this object can be used with the "with" statement to turn on the automatic
# serialization registration magic of StateObject
class stateVars:
  def __init__(self, other):
    global serializeKnowledgeBase
    if type(other) in serializeKnowledgeBase:
      self.knowndata = serializeKnowledgeBase[type(other)]
    self.so = other

  def __enter__(self):
    if "knowndata" not in dir(self):
      self.so.statevars_enabled = True

  def __exit__(self, a, b, c):
    global serializeKnowledgeBase
    if "knowndata" in dir(self):
      self.so.statevars = self.knowndata["statevars"]
      self.so.statevars_format = self.knowndata["statevars_format"]
      self.so.tuples = self.knowndata["tuples"]
    else:
      del self.so.statevars_enabled
      d = {"statevars": self.so.statevars,
           "statevars_format": self.so.statevars_format,
           "tuples": self.so.tuples}
      serializeKnowledgeBase[type(self.so)] = d

# using this object with the "with" statement, the type of the included vars
# can be predetermined, instead of letting the magic find it out.
# this can be used to use smaller types (b instead of i) for saving space.
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

# the GameState object holds all objects in the state and can serialize or
# deserialize itself. it can also accept input commands and relay it to the
# objects that are supposed to get it.
class GameState:
  def __init__(self, data = None):
    self.objects = []
    self.tickinterval = 50 # in miliseconds
    self.clock = 0
    self.nextNewId = 0
    if data:
      self.deserialize(data)

    self.spawns = []

  def copy(self):
    return copy.deepcopy(self)

  def tick(self):
    # advance the clock and let all objects to their business.
    self.spawns = []
    self.clock += self.tickinterval
    for o in self.objects:
      o.tick(self.tickinterval)
      if o.die:
        self.objects.remove(o)

    self.doGravity(self.tickinterval)
    self.doCollisions(self.tickinterval)

  def spawn(self, object, obvious=False):
    # spawn the object into the state and bind it
    if not obvious or object.id == 0:
      object.id = self.nextNewId
      self.nextNewId += 1
    else:
      print "spawning with forced ID:", object.id
    self.objects.append(object.bind(self))
    if not obvious:
      self.spawns.append(object)
    print "spawned:", object.__repr__()

  def serialize(self):
    # serialize the whole gamestate
    data = struct.pack("!i", self.clock)
    data = data + "".join(obj.typename + obj.serialize() for obj in self.objects)
    return data

  def getSerializeType(self, dataFragment):
    # TODO: automatically find the matching object through its 
    #       typename property
    type, data = dataFragment[:2], dataFragment[2:]
    if type == "sp":
      obj = ShipState()
    elif type == "bu":
      obj = BulletState()
    elif type == "ps":
      obj = PlanetState()
    else:
      print "got unknown type:", type.__repr__()

    return obj

  def getSerializedLen(self, dataFragment):
    if isinstance(dataFragment, str):
      return struct.calcsize(self.getSerializeType(dataFragment).statevars_format)
    else:
      return struct.calcsize(dataFragment.statevars_format)

  def deserialize(self, data):
    # deserialize the data

    # the fact, that objects gets cleared, is the reason for the GameStateProxy
    # objects to exist
    self.objects = []
    odata = data
    self.clock, data = struct.unpack("!i", data[:4])[0], data [4:]
    while len(data) > 0:
      obj = self.getSerializeType(data)
      data = data[2:]

      # cut the next N bytes out of the data.
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
        if lns == 0:
          lns = 0.000001
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
    # relays control messages to the objects.
    for id, cmd in commands:
      self.getById(id).command(cmd)


# the base class for a State Object, that also implements the serialization
# black magic.
class StateObject(object):
  typename = "ab"#stract
  mass = 0
  def __init__(self):
    self.state = None
    self.statevars = ["id"]
    self.tuples = []
    self.statevars_format = "!i"
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
      # only when the magic is turned on and only if the attribute is relevant,
      # shall we cause magic to happen.
      if self.statevars_enabled and not attr.startswith("statevars"):
        if type(value) == list:
          for i in range(len(value)):
            addAttr("_%s_%d" % (attr, i), value[i])
          self.tuples.append(attr)
          # don't forget to add the actual tuple value for internal usage.
          raise Exception
        else:
          addAttr(attr, value)
      else:
        # this is usually called when statevars_enabled is not set.
        raise Exception

    except:
      object.__setattr__(self, attr, value)

  # the base class does nothing by itself.
  def tick(self, dt):
    pass

  def bind(self, state):
    self.state = state
    return self

  # since the struct module cannot handle lists, we do it instead
  def pre_serialize(self):
    for tup in self.tuples:
      thetup = object.__getattribute__(self, tup)
      for i in range(len(thetup)):
        object.__setattr__(self, "_%s_%d" % (tup, i), thetup[i])

  def post_deserialize(self):
    for tup in self.tuples:
      val = [object.__getattribute__(self, "_%s_%d" % (tup, i)) \
               for i in range(len( object.__getattribute__(self, tup) )) \
            ]
      object.__setattr__(self, tup, val)

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

    return self

  def command(self, cmd):
    pass

  # return a proxy object that points at us.
  def getProxy(self, history):
    return StateObjectProxy(self, history)

# the proxy object uses the gamestate history object in order to always point
# at the current instance of the object it was generated from.
class StateObjectProxy(object):
  def __init__(self, obj, history):
    self.proxy_id = obj.id
    self.proxy_objref = obj
    history.registerProxy(self)

  def proxy_update(self, gamestate):
    self.proxy_objref = gamestate.getById(self.id)
  
  # all attributes that do not have anything to do with the proxy will be
  # proxied to the StateObject
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
      self.state.spawn(bul, True)
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
      self.position = [0., 0.]
      self.speed = [0., 0.]
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

# the StateHistory object saves a backlog of GameState objects in order to
# interpret input data at the time it happened, even if received with a
# latency. this allows for fair treatment of all players, except for cheaters,
# who could easily abuse this system.
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

  def byClock(self, clock):
    found = 0
    for i in range(len(self.gsh)):
      if self.gsh[i].clock == clock:
        found = i
        break
    return found

  def inject(self, id, command, clock = None):
    if clock:
      found = self.byClock(clock)
    else:
      found = len(self.gsh) - 1

    self.firstDirty = found
    self.inputs[found].append((id, command))

  def injectObject(self, object, clock = None):
    if clock:
      found = self.byClock(clock)
    else:
      found = len(self.gsh) -1

    self.firstDirty = found
    self.gsh[found].spawn(object, True)

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
