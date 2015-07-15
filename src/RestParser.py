import time
from HardwareRepository import HardwareRepository
import collections, os
import gevent.event
from bottle import response
from threading import Thread
from Queue import Queue

"""
Generic/mandatory data structure, each method will require additional data such as motor names, positions, etc. 
generic_data ={
  "Data": {
	  DATA_STRUCTURE, #{} whatever is required, the put/get methods do not care about the specific data
  },
  #the next ones for debugging purposes (coming from the web client):
  "Origin": UI component,
  "Debug": True/false, 
  "Time": YY:MM:DD, HH:MM:SS,
  "Username": username,
  "Proposal": proposal
}
The data shown below for each method must also include the dict above
"""
def dataDict(self, origin):
	return {
		'Origin' : origin,
		'Debug' : True,
		'Time' : time.ctime(),
		'Username' : 'mikegu',
		'Proposal': 'test2015'
	}

hwr_directory = os.environ["XML_FILES_PATH"]
hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
hwr.connect()

experimentQueue = []

class SampleCentring():

	clicks = collections.deque(maxlen=3)

	def __init__(self):
		"""Initialize all the HO related to the sample centring as well as the camera. A dictionary holds all the motor objects for an easy later
		"""
		print "in SampleCentring init"
		self.diffractometer = hwr.getHardwareObject("/minidiff")#image.bl_setup.diffractometer_hwobj
		self.zoom = self.diffractometer.getObjectByRole("zoom")
		self.kappa = self.diffractometer.getObjectByRole("kappa")
		self.omega = self.diffractometer.getObjectByRole("phi")
		self.phi = self.diffractometer.getObjectByRole("phi_z")#ask mx people about phi/phi_z
		self.backLight = self.diffractometer.getObjectByRole("backlight") #in/out motor, 1/0, bakclight tango attr in md2
		self.backLightLevel = self.diffractometer.getObjectByRole("light") #light level motor, bakclightfactor tango attr in md2

		def new_sample_video_frame_received(img, width, height, *args):
			self.video.new_frame.set(img)

		self.video = self.diffractometer.getObjectByRole("camera")
		self.video.connect("imageReceived", new_sample_video_frame_received)
		self.video.new_frame = gevent.event.AsyncResult()
		self.motors_mapping={'Kappa':self.kappa,'Omega':self.omega, 'Phi':self.phi, 'Zoom':self.zoom, 'Light': self.backLight, 'LightLevel': self.backLightLevel}

	def move(self, data):
		""" Move the selected motor to the desired position (check 'data' dict).
		Be careful:
			- MicrodiffMotor AND MicrodiffLight: 'move' method
			- MicrodiffZoom: 'moveToPosition' method
			- InOut: wagoIn/wagoOut (for the backligh activation)
		"""
		motor = self.motors_mapping[data['moveable']]
		new_pos = data['position']
		#the following if-s to solve inconsistent movement method
		try:
			if data['moveable']== 'Zoom':
				motor.moveToPosition(data['position'])
			elif data['moveable']== 'Light':
				if data['position']: motor.wagoIn()
				else: motor.wagoOut()
			else: 
				motor.move(data['position']) #
		except Exception as ex:
			print ex.value

	def getStatus(self, *args):
		data = dataDict()
		if len(args)>0: #so speciic data/'id' is supplied, several 'id'-s are allowed
			for i in args:
				motor = motors_mapping[i['moveable']]

				if data['moveable']== 'Zoom':
					pos = motor.getCurrentPositionName()
					status = "unknown" 
				elif data['moveable']== 'Light':
					pos = motor.getWagoState() # {0:"out", 1:"in", True:"in", False:"out"}
					status = motor.getWagoState()
				else: 
					pos = motor.get_position()
					status = motor.get_state()
				data[i['moveable']] = {'Status': status, 'position': pos}
		#return everything
		else:
			for i in motors_mapping:
				motor = motors_mapping[i]
				if i == 'Zoom':
					pos = motor.getCurrentPositionName()
					status = "unknown" 
				elif i == 'Light':
					pos = motor.getWagoState() # {0:"out", 1:"in", True:"in", False:"out"}
					status = motor.getWagoState()
				else: 
					pos = motor.get_position()
					status = motor.get_state()
				
				data[i] = {'Status': status, 'position': pos}
		
		return data
	
	def getCentring(self,data):
		pass
	def setCentring(self,data):
		clicks.append([data['PosX'],data['PosY']])
		#define a util lib for the algorithm
		return True
	def centre(self,data):
		pass
	def snapshot(self,data):
		pass

class BeamLine():
	# def __init__(self):
		# self.beamline = hwr.getHardwareObject("/beamline-setup")
		# self.resolution = self.beamline.getObjectByRole("resolution")
		# self.transmission = self.beamline.getObjectByRole("transmission")
		# self.energy = self.beamline.getObjectByRole("energy")
		# self.aperture = self.beamline.getObjectByRole("aperture")
		# self.beamSize = self.beamline.getObjectByRole("beamsize")
		# self.motors_mapping={'Energy':self.energy,'Resolution':self.resolution, 'Transmission':self.transmission, 'Aperture': self.aperture, 'BeamSize':self.beamSize}

	def move(self, data):
		motor = self.motors_mapping[data['moveable']]
		try:
			return motor.move(data['position']) #
		except Exception as ex:
			print ex.value

	def getStatus(self, *args):
		data = dataDict()
		if len(args)>0: #so speciic data/'id' is supplied, several 'id'-s are allowed
			for i in args:
				motor = motors_mapping[i['moveable']]
				data[i['moveable']] = {'Status': motor.get_state(), 'position': motor.get_position()}
		#return everything
		else:
			for i in motors_mapping:
				motor = motors_mapping[i]
				data[i] = {'Status': motor.get_state(), 'position': motor.get_position()}
		
		return data

class Sample():
	def __init__(self):
		self.sampleList = []

	def addSample(self, data):
		#if the sample does not come from ispyb, manually create
		self.sampleList.append(data)
		pass
	def updateSample(self, data):
		pass
	def deleteSample(self, data):
		#samp = next((item for item in self.sampleList if item["SampleId"] == data['SampleId'], 'None')
		#self.sampleList.remove(samp)	
		pass
	def getSample(self, data):
 		#samp = next((item for item in self.sampleList if item["SampleId"] == data['SampleId'], 'None')
		#return samp
		pass
	def getSelectedSample(self):
		pass
	def getSampleList(self):	
		return self.sampleList
	def getCollection(self, *args):	
		pass
	def getMode(self, data):
		pass
	def setCentring(self, data):
		pass
	def mountSample(self, data):
		pass
	def umountSample(self, data):
		pass
	def addSampleToQueue(self, data):
		"""
		data = {'SampleID':'Sample42',params:{'spacegroup': 89, ...}}
		"""
		experimentQueue.append(data)

	def removeSampleFromQueue(self, *args):
		pass

	def executeQueue(self):
		pass
	def executeElement(self, data):
		pass
	def stop(self, *args):
		pass
	def pause(self, *args):
		pass
	def getQueueStatus(self, *args):
		pass
	def emptyQueue(self):
		while not experimentQueue.empty:
			q.get_nowait()
class Collection():
	def __init__(self):
		pass
	def defineCollectionMethod(self, data):
		pass
	def addCollection(self, data):
		pass
	def updateCollection(self, data):
		pass
	def getCollection(self, data):
		pass
	def deleteCollection(self, data):
		pass
	def getCollectionStatus(self, *args):
		pass
	def removeCollectionSample(self, *args):
		pass
class Characterisation():
	def __init__(self):
		pass
	def addCharacterisation(self, data):
		pass
	def updateCharacterisation(self, data):
		pass
	def deleteCharacterisation(self, data):
		pass

class SampleChanger():
	def __init__(self):
		pass
	def getSampleChangerContent(self):
		pass

# class Macros():