import logging

from HardwareRepository.BaseHardwareObjects import Device

class Attenuators(Device):
    def __init__(self, name):
        Device.__init__(self, name)

        self.labels  = []
        self.bits    = []
        self.attno   = 0
        self.getValue = self.get_value 
       

    def init(self):
#20150119,JN for maxlab i9113
#        cmdToggle = self.getCommandObject('toggle')
#        cmdToggle.connectSignal('connected', self.connected)
#        cmdToggle.connectSignal('disconnected', self.disconnected)
#        self.chanAttState = self.getChannelObject('attstate')
#        self.chanAttState.connectSignal('update', self.attStateChanged)
        self.chanAttFactor = self.getChannelObject('attfactor')
        self.chanAttFactor.connectSignal('update', self.attFactorChanged)
        
#        if cmdToggle.isConnected():
#            self.connected()
        self.connected() # 20150119,JN for maxlab i9113
   
#        self.getAtteConfig()  #20150119,JN for maxlab i9113

    
    def getAtteConfig(self):
        self.attno = len( self['atte'] )

        for att_i in range( self.attno ):
           obj = self['atte'][att_i]
           self.labels.append( obj.label )
           self.bits.append( obj.bits )


    def getAttState(self):
        try:
            value= int(self.chanAttState.getValue())
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a integer value', str(self.name()))
            value=None
        return value


    def getAttFactor(self):
        try:
            value = float(self.chanAttFactor.getValue())
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
            value=None
        return value


    def get_value(self):
        return self.getAttFactor()


    def connected(self):
        self.setIsReady(True)
 
        
    def disconnected(self):
        self.setIsReady(False)


    def attStateChanged(self, channelValue):
        try:
            value = int(channelValue)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not an integer value', str(self.name())) 
        else:
            self.emit('attStateChanged', (value, ))


    def attFactorChanged(self, channelValue):
        try:
  	    value = float(channelValue)
        except:
            logging.getLogger("HWR").error('%s: received value on channel is not a float value', str(self.name()))
        else:
            self.emit('attFactorChanged', (value, )) 
  	      
