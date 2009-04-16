import main
from socket import *
from gamestate import *

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

  conn = socket(AF_INET, SOCK_DGRAM)
  conn.bind(("", port))

  gs = GameState()
  for i in range(10):
    planet = PlanetState()
    planet.position = [random() * 200 - 100, random() * 200 - 100]
    gs.spawn(planet)

  return gs

def initClient(addr, port, cport = None):
  global conn
  global mode
  global clients
  global srvaddr

  mode = MODE_CLIENT

  if not cport: cport = port
  
  conn = socket(AF_INET, SOCK_DGRAM)
  try:
    conn.bind(("", cport))
  except:
    try:
      conn.bind(("", cport + 1))
    except:
      conn.bind(("", cport + 2))

  conn.settimeout(10)

  data = ""
  while not data and not data.startswith("tickinterval"):
    try:
      conn.sendto(struct.pack("cc32s", TYPE_SHAKE, SHAKE_HELLO, gethostname()), (addr, int(port)))
      print "hello sent."
      data = ("",)
      while "tickinterval" not in data[0]:
        data = conn.recvfrom(4096)
        print data.__repr__()
    except error:
      pass

  main.tickinterval = int(data[0].split(":")[1])
  
  plp = ShipState() # proposed local player state
  plp.position = [random() * 10, random() * 10]
  plp.alignment = random()

  conn.sendto(TYPE_SHAKE + SHAKE_SHIP + plp.serialize(), (addr, port))
  srvaddr = (addr, port)

  gs = GameState()

  myshipid = None
  while myshipid is None:
    shipid, sender = conn.recvfrom(4096)
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
  conn.sendto(msg, srvaddr)

def sendCmd(cmd):
  global srvaddr
  msg = struct.pack("cic", TYPE_INPUT, main.gsh[-1].clock, cmd)
  conn.sendto(msg, srvaddr)

def pumpEvents():
  global conn
  global mode
  global clients
  global nextTeam
  global chatlist

  if mode == "s":
    try:
      while True:
        msg, sender = conn.recvfrom(4096)
        type = msg[0]
        if type == TYPE_INPUT:
          type, clk, cmd = struct.unpack("cic", msg)

          main.gsh.inject(clients[sender].shipid, cmd, clk)
        
        elif type == TYPE_SHAKE:
          print "got a shake message"
          # HANDSHAKE CODE BEGIN
          if sender not in clients:
            print "sender is unknown"
            if msg[1] == SHAKE_HELLO:
              print "got a shake_hello"
              nc = Client()
              nc.name = msg[2:msg.find("\x00")]
              nc.socket = socket(AF_INET, SOCK_DGRAM)
              nc.socket.connect(sender)

              nc.socket.send(TYPE_SHAKE + "tickinterval:" + str(main.tickinterval))
              clients[sender] = nc
              print clients
          else:
            print "sender is in clients."
            if msg[1] == SHAKE_SHIP:
              print "got a shake_ship."
              remoteship = ShipState(msg[2:])
              remoteship.team = nextTeam
              nextTeam += 1
              main.gsh[-1].spawn(remoteship)
              clients[sender].shipid = remoteship.id
              print "sending a your-id-package"
              clients[sender].socket.sendto(TYPE_SHAKE + SHAKE_YOURID + struct.pack("i", clients[sender].shipid), sender)
              print "sent."

              print "distributing a playerlist"
              msg = TYPE_INFO + INFO_PLAYERS + "".join(struct.pack("i32s", c.shipid, c.name) for c in clients.values())
              for dest in clients.values():
                dest.socket.send(msg)

        elif type == TYPE_CHAT:
          if msg[1] == CHAT_MESSAGE:
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
    for a, c in clients.items():
      c.socket.sendto(msg, a)

  elif mode == "c":
    gsdat = ""
    while not gsdat:
      try:
        data = conn.recv(4096)
        if data[0] == TYPE_STATE:
          gsdat = data
        elif data[0] == TYPE_INFO:
          if data[1] == INFO_PLAYERS:
            data = data[2:]
            while len(data) > 0:
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
