import main
from socket import *
from gamestate import *
from select import select
from timing import timer

TYPE_STATE = "g"
TYPE_SHAKE = "c"
TYPE_CHAT  = "m"
TYPE_INPUT = "i"
TYPE_COMMAND = "C"
TYPE_INFO  = "n"

SHAKE_HELLO  = "h"
SHAKE_SHIP   = "s"
SHAKE_YOURID = "i"

INFO_PLAYERS = "p"
INFO_MYCLOCK = "c"

CHAT_MESSAGE = "m"

MODE_CLIENT = "c"
MODE_SERVER = "s"

COMMAND_SPAWN = "s"
COMMAND_KILL  = "k"
COMMAND_REPLACE = "r"

class Client():
  def __init__(self):
    self.shipid = None
    self.name = ""
    self.socket = None
    self.remote = True
    self.sender = ()

  def __repr__(self):
    if self.socket:
      return "<Client %(name)s on %(addr)s%(remote)s with ship %(shipid)s>" % {\
          'addr': str(self.socket.getpeername()),
          'remote': ["", " (remote)"][int(self.remote)],
          'shipid': str(self.shipid) or "None",
          'name': self.name}
    else:
      return "<Client %(name)s (socketless)%(remote)s with ship %(shipid)s>" % {\
          'remote': ["", " (remote)"][int(self.remote)],
          'shipid': str(self.shipid) or "None",
          'name': self.name}
      


clients = {} # in server mode this is a dict of (addr, port) to Client
             # in client mode this is a dict of shipid to Client

conn = None # the server socket
srvaddr = ("", 1)

nextTeam = 1

chatlog = []

def setupConn():
  global conn
  conn.setblocking(0)

def initServer(port):
  global conn
  global mode

  mode = MODE_SERVER

  conn = socket(AF_INET, SOCK_STREAM)
  conn.bind(("", port))
  conn.listen(2)
  conn.setblocking(False)

  gs = GameState()
  for i in range(1):
    planet = PlanetState()
    planet.position = [random() * 200 - 100, random() * 200 - 100]
    gs.spawn(planet)

  return gs

def initClient(addr, port):
  global conn
  global mode
  global clients

  mode = MODE_CLIENT

  conn = socket(AF_INET, SOCK_STREAM)
  conn.settimeout(10)
  conn.connect((addr, port))

  data = ""
  while not data and not data.startswith("tickinterval"):
    try:
      mysend(conn, struct.pack("!cc32s", TYPE_SHAKE, SHAKE_HELLO, gethostname()))
      print "hello sent."
      data = ("",)
      while "tickinterval" not in data:
        data = myrecv(conn)
        print data.__repr__(), "tickinterval" in data
    except error:
      raise

  print "Got tickinterval.", data
  ticki = ""
  data  = data.split(":")[1]
  try:
    while data:
      ticki, data = ticki + data[0], data[1:]
      main.tickinterval = int(ticki)
  except:
    pass

  print "tickinterval is", main.tickinterval
  
  plp = ShipState() # proposed local player state
  plp.position = [random() * 10., random() * 10.]
  print "player position:", plp.position
  plp.alignment = random()

  mysend(conn, TYPE_SHAKE + SHAKE_SHIP + plp.serialize())
  print "sent ship.", plp.serialize().__repr__()

  gs = None

  myshipid = None
  while myshipid is None:
    shipid = myrecv(conn)
    if shipid[0] == TYPE_SHAKE and shipid[1] == SHAKE_YOURID:
      myshipid = struct.unpack("!i", shipid[2:])[0]
  
  while not gs:
    statemsg = myrecv(conn)
    if statemsg[0] == TYPE_STATE:
      gs = GameState(statemsg[1:])
    else:
      print "oops. what?", shipid.__repr__()

  myself = Client()
  myself.name = gethostname()
  myself.shipid = myshipid
  myself.remote = False
  clients[None] = myself

  return gs

def sendChat(chat):
  global srvaddr
  msg = TYPE_CHAT + CHAT_MESSAGE + chat
  mysend(conn, msg)

def sendCmd(cmd):
  msg = struct.pack("!cic", TYPE_INPUT, main.gsh[-1].clock, cmd)
  main.gsh.inject(clients[None].shipid, cmd)
  mysend(conn, msg)

def mysend(sock, data):
  sock.send(struct.pack("!i", len(data)) + data)

def myrecv(sock):
  wantedlen = struct.calcsize("!i")
  first = ""
  while len(first) < wantedlen:
    first += sock.recv(wantedlen - len(first))
    if len(first) == 0:
      return ""
  wantedlen = struct.unpack("!i", first)[0]
  second = ""
  while len(second) < wantedlen:
    second += sock.recv(wantedlen - len(second))
  if wantedlen != len(second):
    print wantedlen, len(second)
  return second

def pumpEvents():
  global conn
  global mode
  global clients
  global nextTeam
  global chatlist

  if mode == "s":
    try:
      receiving = True
      readysock = []
      while receiving:
        if conn in select([conn], (), (), 0)[0]:
          print "accepting new connection!"
          newsock, addr = conn.accept()
          nc = Client()
          nc.socket = newsock

          clients[newsock] = nc

        readysock = select(clients.keys(), (), (), 0)[0]
        receiving = bool(readysock)
        stuff = [(myrecv(sock), clients[sock]) for sock in readysock]
        for msg, sender in stuff:
          if msg:
            type = msg[0]
          else: continue
          if type == TYPE_INPUT:
            type, clk, cmd = struct.unpack("!cic", msg)

            main.gsh.inject(sender.shipid, cmd, clk)
            dmsg = struct.pack("!ciic", type, clk, sender.shipid, cmd)


            for sock in clients.keys():
              if sock != sender.socket:
                mysend(sock, dmsg)

          elif type == TYPE_SHAKE:
            print "got a shake message"
            # HANDSHAKE CODE BEGIN
            if msg[1] == SHAKE_HELLO:
              print "got a shake_hello"
              sender.name = msg[2:msg.find("\x00")]

              mysend(sender.socket, TYPE_SHAKE + "tickinterval:" + str(main.tickinterval))
              print TYPE_SHAKE + "tickinterval:" + str(main.tickinterval)
              print clients
            elif msg[1] == SHAKE_SHIP:
              print "got a shake_ship."

              remoteship = ShipState(msg[2:])

              remoteship.team = nextTeam
              nextTeam += 1
              main.gsh[-1].spawn(remoteship)
              sender.shipid = remoteship.id
              print "sending a your-id-package"
              mysend(sender.socket, TYPE_SHAKE + SHAKE_YOURID + struct.pack("!i", sender.shipid))
              print "sent."

              print "sending the complete current gamestate"
              mysend(sender.socket, TYPE_STATE + main.gsh[-1].serialize())

              print "distributing a playerlist of", len(clients), "players."
              msg = TYPE_INFO + INFO_PLAYERS + "".join(struct.pack("!i32s", c.shipid, c.name) for c in clients.values())
              for dest in clients.keys():
                mysend(dest, msg)

          elif type == TYPE_CHAT:
            if msg[1] == CHAT_MESSAGE:
              dmsg = struct.pack("!cc128s", TYPE_CHAT, CHAT_MESSAGE, ": ".join([sender.name, msg[2:]]))
              for dest in clients.values():
                mysend(dest.socket, dmsg)

              print "chat:", sender.name + ": " + msg[2:]

          else:
            print msg.__repr__()

    except error, e:
      if e.args[0] != 11:
        raise

    main.gsh.apply()
    if main.gsh[-2].spawns:
      print "sending a spawn package:", main.gsh[-2].spawns, "for clock", main.gsh[-2].clock
      msg = TYPE_COMMAND + COMMAND_SPAWN + struct.pack("!i", main.gsh[-2].clock) + "".join([spawned.typename + spawned.serialize() for spawned in main.gsh[-2].spawns])
      for dest in clients.values():
        mysend(dest.socket, msg)

    if main.gsh[-1].clock & 1000:
      msg = TYPE_INFO + INFO_MYCLOCK + struct.pack("!i", main.gsh[-1].clock)
      for dest in clients.values():
        mysend(dest.socket, msg)

  elif mode == "c":
    receiving = select([conn], (), (), 0)[0]
    while receiving:
      receiving = select([conn], (), (), 0)[0]
      try:
        data = myrecv(conn)
        if not data:
          continue
        elif data[0] == TYPE_INPUT:
            clk, id, cmd = struct.unpack("!iic", data[1:])

            main.gsh.inject(id, cmd, clk)
        elif data[0] == TYPE_STATE:
          gsdat = data
        elif data[0] == TYPE_INFO:
          if data[1] == INFO_PLAYERS:
            print "got a new playerlist"
            data = data[2:]
            clients = {None: clients[None]}
            while data:
              nc = Client()
              chunk, data = data[:struct.calcsize("!i32s")], data[struct.calcsize("!i32s"):]
              nc.shipid, nc.name = struct.unpack("!i32s", chunk)
              nc.name = nc.name[:nc.name.find("\x00")]
              nc.remote = nc.shipid != clients[None].shipid
              # we want our client as the None-client, so we reassign this here.
              if not nc.remote:
                clients[None] = nc
              else:
                clients[nc.shipid] = nc

            main.makePlayerList()

          elif data[1] == INFO_MYCLOCK:
            clock = struct.unpack("!i", data[2:])[0]
            timer.catchUp += max(0, (clock - main.gsh[-1].clock) / 1000.)
            timer.waitUp += min(0, (clock - main.gsh[-1].clock) / 1000.)

        elif data[0] == TYPE_CHAT:
          if data[1] == CHAT_MESSAGE:
            chatlog.append(data[2:])
            main.updateChatLog()
        elif data[0] == TYPE_COMMAND:
          if data[1] == COMMAND_SPAWN:
            print "got a spawn command", data.__repr__()
            dat = data[2:]
            clock, data = struct.unpack("!i", dat[:4])[0], dat[4:]
            
            while data:
              objtype, data = data[:2], data[2:]
              obj = main.gsh[-1].getSerializeType(objtype)
              ln = main.gsh[-1].getSerializedLen(obj)
              objdat, data = data[:ln], data[ln:]
              print "trying to spawn:", objdat.__repr__(), "at", clock
              obj.deserialize(objdat)
              print "got obj with id", obj.id
              try:
                if main.gsh[-1].getById(obj.id): 
                  print "already taken. updating..."
                  main.gsh.updateObject(obj.id, objdat, clock)
              except NotFound:
                main.gsh.injectObject(obj, clock)

      except error:
        pass

    main.gsh.apply()
    main.gsh.updateProxies()
