import main
from socket import *
from gamestate import *
from select import select

TYPE_STATE = "g"
TYPE_SHAKE = "c"
TYPE_CHAT  = "m"
TYPE_INPUT = "i"
TYPE_INFO  = "n"

SHAKE_HELLO  = "h"
SHAKE_SHIP   = "s"
SHAKE_YOURID = "i"

INFO_PLAYERS = "p"

CHAT_MESSAGE = "m"

MODE_CLIENT = "c"
MODE_SERVER = "s"


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
  for i in range(10):
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
      conn.send(struct.pack("cc32s", TYPE_SHAKE, SHAKE_HELLO, gethostname()))
      print "hello sent."
      data = ("",)
      while "tickinterval" not in data:
        data = conn.recv(4096)
        print data.__repr__(), "tickinterval" in data
    except error:
      pass

  print "Got tickinterval."
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
  plp.position = [random() * 10, random() * 10]
  plp.alignment = random()

  conn.send(TYPE_SHAKE + SHAKE_SHIP + plp.serialize())
  print "sent ship."

  gs = GameState()

  myshipid = None
  while myshipid is None:
    shipid = conn.recv(4096)
    if shipid[0] == TYPE_SHAKE and shipid[1] == SHAKE_YOURID:
      myshipid = struct.unpack("i", shipid[2:])[0]
      success = True
    elif shipid[0] == TYPE_STATE:
      gs = GameState(shipid[1:])
    else:
      print "oops. what?", shipid.__repr__()

  myship = ShipState()
  gs.spawn(myship)
  myship.id = myshipid

  myself = Client()
  myself.name = gethostname()
  myself.shipid = myshipid
  myself.remote = False
  clients[None] = myself

  return gs

def sendChat(chat):
  global srvaddr
  msg = TYPE_CHAT + CHAT_MESSAGE + chat
  conn.send(msg)

def sendCmd(cmd):
  global srvaddr
  msg = struct.pack("cic", TYPE_INPUT, main.gsh[-1].clock, cmd)
  conn.send(msg)

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
        stuff = [(sock.recv(2), clients[sock]) for sock in readysock]
        for msg, sender in stuff:
          type = msg[0]
          if type == TYPE_INPUT:
            msg += sender.socket.recv(struct.calcsize("cic") - len(msg))
            type, clk, cmd = struct.unpack("cic", msg)

            main.gsh.inject(sender.shipid, cmd, clk)

          elif type == TYPE_SHAKE:
            print "got a shake message"
            # HANDSHAKE CODE BEGIN
            if msg[1] == SHAKE_HELLO:
              print "got a shake_hello"
              msg += sender.socket.recv(4096)
              sender.name = msg[2:msg.find("\x00")]

              sender.socket.send(TYPE_SHAKE + "tickinterval:" + str(main.tickinterval))
              print TYPE_SHAKE + "tickinterval:" + str(main.tickinterval)
              print clients
            elif msg[1] == SHAKE_SHIP:
              print "got a shake_ship."

              remoteship = ShipState()

              msg += sender.socket.recv(struct.calcsize(remoteship.statevars_format) - len(msg))

              remoteship.team = nextTeam
              nextTeam += 1
              main.gsh[-1].spawn(remoteship)
              sender.shipid = remoteship.id
              print "sending a your-id-package"
              sender.socket.send(TYPE_SHAKE + SHAKE_YOURID + struct.pack("i", sender.shipid))
              print "sent."

              print "distributing a playerlist"
              msg = TYPE_INFO + INFO_PLAYERS + "".join(struct.pack("i32s", c.shipid, c.name) for c in clients.values())
              for dest in clients.keys():
                dest.send(msg)

          elif type == TYPE_CHAT:
            if msg[1] == CHAT_MESSAGE:
              msg += struct.calcsize("cc128s") - len(msg)
              dmsg = struct.pack("cc128s", TYPE_CHAT, CHAT_MESSAGE, ": ".join([clients[sender].name, msg[2:]]))
              for dest in clients.values():
                dest.socket.send(dmsg)

              print "chat:", cliends[sender].name + ": " + msg[2:]

          else:
            print msg.__repr__()

    except error, e:
      if e.args[0] != 11:
        raise

    main.gsh.apply()
    msg = TYPE_STATE + main.gsh[-1].serialize()
    for sock in clients.keys():
      sock.send(msg)

  elif mode == "c":
    gsdat = ""
    while not gsdat:
      try:
        data = conn.recv(4096)
        if not data:
          pass
        elif data[0] == TYPE_STATE:
          gsdat = data
        elif data[0] == TYPE_INFO:
          if data[1] == INFO_PLAYERS:
            data = data[2:]
            if len(data) < struct.calcsize("i32s"):
              data += conn.recv(struct.calcsize("i32s") - len(data))
            nc = Client()
            chunk, data = data[:struct.calcsize("i32s")], data[struct.calcsize("i32s"):]
            nc.shipid, nc.name = struct.unpack("i32s", chunk)
            nc.name = nc.name[:nc.name.find("\x00")]
            nc.remote = nc.shipid != clients[None].shipid
            # we want our client as the None-client, so we reassign this here.
            if not nc.remote:
              clients[None] = nc
            else:
              clients[nc.shipid] = nc

            main.makePlayerList()
        elif data[0] == TYPE_CHAT:
          if data[1] == CHAT_MESSAGE:
            chatlog.append(data[2:])
            main.updateChatLog()

      except error:
        pass

    last = False
    while not last:
      try: 
        gsdat = conn.recv(4096)
      except error:
        last = True

    main.gsh[-1].deserialize(gsdat[1:])
    main.gsh.updateProxies()
