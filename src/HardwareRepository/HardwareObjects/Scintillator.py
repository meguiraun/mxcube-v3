from HardwareRepository.BaseHardwareObjects import Device

class Scintillator(Device):
  def __init__(self, *args, **kwargs):
    Device.__init__(self, *args, **kwargs)

  def init(self):
    self.stateChan = self.getChannelObject("dev_state")
    self.stateChan.connectSignal("update", self.dev_state_updated)


  def dev_state_updated(self, state):
    self.emit("wagoStateChanged", (state,))

 
  def wagoIn(self):
    cmd=self.getCommandObject("set_in")
    cmd()

  def wagoOut(self):
    cmd=self.getCommandObject("set_out")
    cmd() 

  def getWagoState(self):
    return self.stateChan.getValue()
