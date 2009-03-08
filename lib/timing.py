import time
import math

class gameTimer:
  def __init__(self):
    """this class times a running game so that it always runs at the same speed
even if the framerate constantly changes"""
    # initialize the timer, but don't start it yet
    self.startTime = 0
    self.running = False

    # used for timing
    self.frameStartTime = 0
    self.frameTime = 0

    # the game runs in a special speed unit which is just called timeunit.
    # in a standard game one full timeunit is exactly 1 second.
    # the curspd variable (which shall be adjusted every frame to fit the
    # current execution speed and framerate of the game) is multiplied with
    # every speed or similar to get a nice value.
    self.curspd = 1

    # this variable is used for artificially speeding up the game
    self.gameSpeed = 1
  
  def startTiming(self):
    self.running = True
    self.startTime = time.time()

  def now(self):
    """returns the current time in the game in seconds with high precision"""
    if self.running:
      return time.time() - self.startTime
    else:
      raise Exception, "timer not yet initialized, yet now was called"

  def startFrame(self):
    """call this function at the beginning of a frame to start the speed adjusting"""
    self.frameStartTime = self.now()

  def endFrame(self):
    """call this function at the end of a frame to finish speed adjusting.
sets an appropriate value for self.curspd"""
    self.frameTime = self.now() - self.frameStartTime
    # this should probably work...
    self.curspd = self.frameTime
    self.curspd = self.speed()

  def blink(self, duration):
    if self.now() % (duration * 2) < duration:
      return True
    return False

  def pulse(self, duration, low = 0, high = 1):
    return (low + high) / 2. + math.sin(self.now() / duration * 2 * math.pi) * (low - high) / 2

  def speed(self):
    """returns the speed at which the game shall run.
currently it is curspd * gameSpeed"""
    return self.curspd * self.gameSpeed

timer = gameTimer()
