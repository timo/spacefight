from OpenGL.GL import *

def makeBlock(startfun, endfun):
    class retCls:
        def __init__(self, *args, **kwargs):
	    self.args = args
	    self.kwargs = kwargs
        def __enter__(self):
	    startfun(self.args, self.kwargs)
	def __exit__(self):
	    endfun()

def __identityMatrix():
  glPushMatrix()
  glLoadIdentity()

glMatrix = makeBlock(glPushMatrix, glPopMatrix)
glIdentityMatrix = makeBlock(__identityMatrix, glPopMatrix)
glPrimitive = makeBlock(glBegin, glEnd)
