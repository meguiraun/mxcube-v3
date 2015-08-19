"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
from HardwareRepository import BaseHardwareObjects
import logging
import os, time
import PyTango
import Image
import numpy as np
from threading import Event, Thread
import base64

#try:
#  import Image
#except ImportError:
#  logging.getLogger("HWR").warning("PIL not available: cannot take snapshots")
#  canTakeSnapshots=False
#else:
#  canTakeSnapshots=True

MAX_TRIES     = 3
SLOW_INTERVAL = 1000

class MaxLabMDCamera(BaseHardwareObjects.Device):

    def __init__(self,name):
        BaseHardwareObjects.Device.__init__(self,name)

    def _init(self):

        self.udiffVER_Ok  = False
        self.badimg       = 0
        self.pollInterval = 500
        self.connected    = False

        try:
            self.device = PyTango.DeviceProxy(self.tangoname)
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            print "last error ",str(last_error)
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error['desc'])
    
            self.device = BaseHardwareObjects.Null()
        else:
           self.setIsReady(True)
        print self.device

    def init(self):

      if self.device is not None:
          print "initializing camera object"
           #self.pollingTimer = qt.QTimer()
           #self.pollingTimer.connect(self.pollingTimer, qt.SIGNAL("timeout()"), self.poll)
          if self.getProperty("interval"):
              self.pollInterval = self.getProperty("interval")
          print self.pollInterval
          #self.getChannelObject('UdiffVersion').connectSignal('update', self.udiffVersionChanged)
          #self.stopper = self.pollingTimer(self.pollInterval, self.poll)
          self.stopper = False#self.pollingTimer(self.pollInterval, self.poll)
          thread = Thread(target=self.poll)
          thread.start()
          print "started"
          print "polling started"

    def udiffVersionChanged(self, value):

        print "udiff version is ", value
        if value == "MD2_2":
            print "start polling MD camera with poll interval=",self.pollInterval
            #self.pollingTimer.start(self.pollInterval)
            #self.startPolling()
        else:
            print "stop polling the camera. This microdiff version does not support a camera"
            #self.pollingTimer.stop()
            self.stopper=True

    def connectToDevice(self):

        print "Connecting to camera device"

        try:
             cmds = self.device.command_list_query()
             self.connected = True
        except PyTango.ConnectionFailed:
             print "Microdiff DS not running or bad name in config"
             self.connected = False
        except:
             self.connected = False
        
        if "getImageJPG" in cmds:
            print "YES"
        else:
            print "NO"

        return self.connected

    #@timer.setInterval(self.pollInterval)
    def poll(self):
        print "polling images"
        while not self.stopper:
            time.sleep(float(self.pollInterval)/1000)
        # if not self.connected:
        #   if not self.connectToDevice():
        #       self.stopper()
        #       self.stopper = self.pollingTimer(SLOW_INTERVAL, self.poll)
        #       return
        #   else:
        #       self.stopper()
        #       self.pollingTimer(self.pollInterval, self.poll)
            try:
                img=self.device.getImageJPG()
                #print "image retrieved"
                img = base64.b64encode(img.tostring())
                self.emit("imageReceived", img, 659, 493)
            except PyTango.ConnectionFailed:
                self.connected = False
                return
            except:
                import traceback
                traceback.print_exc()
       #  try:
       #      if img.any():
       # #        self.emit("imageReceived", img, 768, 576) 
       #          self.emit("imageReceived", img, 659, 493) # JN,20140807,adapt the MD2 screen to mxCuBE2
       #          if self.badimg > MAX_TRIES:
       #              self.badimg = 0
       #      else:
       #          print "bad"
       #          self.badimg += 1

       #      if self.badimg > MAX_TRIES:
       #          print "seems too bad. polling with a slow interval now"
       #          self.stopper()
       #          self.stopper = self.pollingTimer(SLOW_INTERVAL, self.poll)       
       #  except:
       #      import traceback
       #      traceback.print_exc()
    def imageUpdated(self, value):
       print "<HW> got new image"
       print value

    def gammaExists(self):
        return False
    def contrastExists(self):
        return False
    def brightnessExists(self):
        return False
    def gainExists(self):
        return False
    def getWidth(self):
        #return 768 #JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659
    def getHeight(self):
        #return 576 # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def setLive(self, state):
        self.liveState = state
        return True
    def imageType(self):
        return None

    def takeSnapshot(self, *args):
      #jpeg_data=self.device.GrabImage()
      jpeg_data=self.device.getImageJPG()
      #f = open(*(args + ("w",)))
      #f.write("".join(map(chr, jpeg_data)))
      #f.close()

      # JN 20150206, have the same resolution as the one shown on the mxCuBE video
      f = open("/tmp/mxcube_tmpSnapshot.jpeg","w")
      f.write("".join(map(chr, jpeg_data)))
      f.close()
      img_tmp=Image.open("/tmp/mxcube_tmpSnapshot.jpeg").crop((55,42,714,535))
      img_tmp.save("/tmp/mxcube_cropSnapshot.jpeg")
      img=np.fromfile("/tmp/mxcube_cropSnapshot.jpeg",dtype="uint8")

      f = open(*(args + ("w",)))
      f.write("".join(map(chr, img)))
      f.close()



    # def pollingTimer(self, interval, func):
    #     stopped = Event()
    #     print "in pollintimer"
    #     def loop():
    #         while not stopped.wait(interval): # the first call is in interval secs
    #             print "in pollingTimer"
    #             func()
    #     Thread(target=loop).start()    
    #     return stopped.set
