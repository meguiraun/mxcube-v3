#for pretty printing:
import pprint
# 

from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractMultiCollect import *
from gevent.event import AsyncResult
import logging
import time
import os
import httplib

class FixedEnergy:
    def __init__(self, wavelength, energy):
      self.wavelength = wavelength
      self.energy = energy

    def set_wavelength(self, wavelength):
      return

    def set_energy(self, energy):
      return

    def getCurrentEnergy(self):
      return self.energy

    def get_wavelength(self):
      return self.wavelength


class TunableEnergy:
    # self.bl_control is passed by MultiCollect class
    @task
    def set_wavelength(self, wavelength):
        energy_obj = self.bl_control.energy
        return energy_obj.startMoveWavelength(wavelength)

    @task
    def set_energy(self, energy):
        energy_obj = self.bl_control.energy
        return energy_obj.startMoveEnergy(energy)

    def getCurrentEnergy(self):
        return self.bl_control.energy.getCurrentEnergy()

    def get_wavelength(self):
        return self.bl_control.energy.getCurrentWavelength()


class CcdDetector:
    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        self.getChannelObject("take_dark").setValue(take_dark)
        self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)
        #self.getCommandObject("build_collect_seq").executeCommand("write_dp_inputs(COLLECT_SEQ,MXBCM_PARS)", wait=True)

    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
        self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
        self.getCommandObject("prepare_acquisition").executeCommand('setMxThumbnailPaths("%s","%s")' % (jpeg_full_path, jpeg_thumbnail_full_path))
        self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)
       
    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if osc_range < 1E-4:
            # still image
            return (start, start+osc_range)
        else:
            self.execute_command("prepare_oscillation", start, start+osc_range, exptime, npass)
            return (start, start+osc_range)
        
    @task
    def do_oscillation(self, start, end, exptime, npass):
        self.execute_command("do_oscillation", start, end, exptime, npass)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
        self.execute_command("start_acquisition")  
      
    @task
    def write_image(self, last_frame):
        if last_frame:
            self.execute_command("flush_detector")
        else:
            self.execute_command("write_image")

    @task
    def stop_acquisition(self):
        self.execute_command("detector_readout")
      
    @task
    def reset_detector(self):   
        self.execute_command("reset_detector")


class PixelDetector:
    def __init__(self):
        self.shutterless = True
        self.new_acquisition = True
        self.oscillation_task = None
        self.shutterless_exptime = None
        self.shutterless_range = None

    @task
    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        self.new_acquisition = True
        if  osc_range < 0.0001:
            self.shutterless = False
        take_dark = 0
        if self.shutterless:
            self.shutterless_range = osc_range*number_of_images
            self.shutterless_exptime = (exptime + 0.003)*number_of_images
        self.execute_command("prepare_acquisition", take_dark, start, osc_range, exptime, npass, comment)
        #self.getCommandObject("build_collect_seq").executeCommand("write_dp_inputs(COLLECT_SEQ,MXBCM_PARS)",wait=True)
        
    @task
    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
      if self.shutterless and not self.new_acquisition:
          return

      self.getCommandObject("prepare_acquisition").executeCommand('setMxCollectPars("current_phi", %f)' % start)
      self.getCommandObject("prepare_acquisition").executeCommand('setMxCurrentFilename("%s")' % filename)
      self.getCommandObject("prepare_acquisition").executeCommand("ccdfile(COLLECT_SEQ, %d)" % frame_number, wait=True)

    @task
    def prepare_oscillation(self, start, osc_range, exptime, npass):
        if self.shutterless:
            if self.new_acquisition:
                self.execute_command("prepare_oscillation", start, start+self.shutterless_range, self.shutterless_exptime, npass)
        else:
            if osc_range < 1E-4:
                # still image
                pass
            else:
                self.execute_command("prepare_oscillation", start, start+osc_range, exptime, npass)
        return (start, start+osc_range)

    @task
    def start_acquisition(self, exptime, npass, first_frame):
      if not first_frame and self.shutterless:
        time.sleep(exptime) 
      else:
        self.execute_command("start_acquisition")

    @task
    def do_oscillation(self, start, end, exptime, npass):
      if self.shutterless:
          if self.new_acquisition:
              # only do this once per collect
              npass = 1
              exptime = self.shutterless_exptime
              end = start + self.shutterless_range
          
              # make oscillation an asynchronous task => do not wait here
              self.oscillation_task = self.execute_command("do_oscillation", start, end, exptime, npass, wait=False)
          else:
              try:
                 self.oscillation_task.get(block=False)
              except gevent.Timeout:
                 pass #no result yet, it is normal
              except:
                 # an exception occured in task! Pilatus server died?
                 raise
      else:
          self.execute_command("do_oscillation", start, end, exptime, npass)
    
    @task
    def write_image(self, last_frame):
      if last_frame:
        if self.shutterless:
            self.oscillation_task.get()
            self.execute_command("specific_collect_frame_hook")

    def stop_acquisition(self):
        self.new_acquisition = False
      
    @task
    def reset_detector(self):
      if self.shutterless:
          self.oscillation_task.kill()
      self.execute_command("reset_detector")


class MAXLABMultiCollect(AbstractMultiCollect, HardwareObject):
    def __init__(self, name, detector, tunable_bl):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._detector        = detector
        self._tunable_bl      = tunable_bl
        self._centring_status = None

        self.image_file_format = "%(prefix)s_%(run_number)s_%%03d.%(suffix)s"


    def execute_command(self, command_name, *args, **kwargs): 
      wait = kwargs.get("wait", True)
      cmd_obj = self.getCommandObject(command_name)
      return cmd_obj(*args, wait=wait)
          
        
    def init(self):
        lims = self.getObjectByRole("dbserver"),
        logging.getLogger("HWR").info("lims object is %s", str(lims))

        self.setControlObjects(diffractometer = self.getObjectByRole("diffractometer"),
                               sample_changer = self.getObjectByRole("sample_changer"),
                               lims = self.getObjectByRole("dbserver"),
                               safety_shutter = self.getObjectByRole("safety_shutter"),
                               machine_current = self.getObjectByRole("machine_current"),
                               cryo_stream = self.getObjectByRole("cryo_stream"),
                               energy = self.getObjectByRole("energy"),
                               resolution = self.getObjectByRole("resolution"),
                               detector_distance = self.getObjectByRole("detector_distance"),
                               transmission = self.getObjectByRole("transmission"),
                               undulators = self.getObjectByRole("undulators"),
                               flux = self.getObjectByRole("flux"))

        mxlocalHO = self.getObjectByRole("beamline_configuration")
        bcm_pars  = mxlocalHO["BCM_PARS"]
        spec_pars = mxlocalHO["SPEC_PARS"]

        try:
          undulators = bcm_pars["undulator"]
        except IndexError:
          undulators = []

        self.setBeamlineConfiguration(directory_prefix = self.getProperty("directory_prefix"),
                                      synchrotron_name = bcm_pars.getProperty("synchrotron_name"),
                                      default_exposure_time = bcm_pars.getProperty("default_exposure_time"),
                                      default_number_of_passes = bcm_pars.getProperty("default_number_of_passes"),
                                      maximum_radiation_exposure = bcm_pars.getProperty("maximum_radiation_exposure"),
                                      nominal_beam_intensity = bcm_pars.getProperty("nominal_beam_intensity"),
                                      minimum_exposure_time = bcm_pars.getProperty("minimum_exposure_time"),
                                      minimum_phi_speed = bcm_pars.getProperty("minimum_phi_speed"),
                                      minimum_phi_oscillation = bcm_pars.getProperty("minimum_phi_oscillation"),
                                      maximum_phi_speed = bcm_pars.getProperty("maximum_phi_speed"),
                                      detector_fileext = bcm_pars.getProperty("FileSuffix"),
                                      detector_type = bcm_pars["detector"].getProperty("type"),
                                      detector_mode = spec_pars["detector"].getProperty("binning"),
                                      detector_manufacturer = bcm_pars["detector"].getProperty("manufacturer"),
                                      detector_model = bcm_pars["detector"].getProperty("model"),
                                      detector_px = bcm_pars["detector"].getProperty("px"),
                                      detector_py = bcm_pars["detector"].getProperty("py"),
                                      beam_ax = spec_pars["beam"].getProperty("ax"),
                                      beam_ay = spec_pars["beam"].getProperty("ay"),
                                      beam_bx = spec_pars["beam"].getProperty("bx"),
                                      beam_by = spec_pars["beam"].getProperty("by"),
                                      undulators = undulators,
                                      focusing_optic = bcm_pars.getProperty('focusing_optic'),
                                      monochromator_type = bcm_pars.getProperty('monochromator'),
                                      beam_divergence_vertical = bcm_pars.getProperty('beam_divergence_vertical'),
                                      beam_divergence_horizontal = bcm_pars.getProperty('beam_divergence_horizontal'),     
                                      polarisation = bcm_pars.getProperty('polarisation'),
                                      #auto_processing_server = self.getProperty("auto_processing_server"),
                                      input_files_server = self.getProperty("input_files_server"))
  
        #self.bl_control.diffractometer.connect("centringAccepted", self.sample_centring_done)

	self.getChannelObject("spec_messages").connectSignal("update", self.log_message_from_spec)
        self.prepareCollectionMacro = self.getProperty("data_collection_macro")

        self._detector.getCommandObject = self.getCommandObject
        self._detector.getChannelObject = self.getChannelObject
        self._detector.execute_command = self.execute_command
        self._tunable_bl.bl_control = self.bl_control

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True, ))


    def log_message_from_spec(self, msg):
        logging.getLogger("HWR").info(msg)        


    @task
    def take_crystal_snapshots(self):
        self.bl_control.diffractometer.takeSnapshots(wait=True)


    @task
    def data_collection_hook(self, data_collect_parameters):
        self.bl_control.diffractometer.backLightOut()
        self.execute_command("prepare_collection")
        self.collect_pars_dp = data_collect_parameters
        return AbstractMultiCollect.data_collection_hook(self, data_collect_parameters)

    @task
    def set_transmission(self, transmission_percent):
        return
        # self.bl_control.transmission.setTransmission(transmission_percent)


    def set_wavelength(self, wavelength):
        return self._tunable_bl.set_wavelength(wavelength)


    def set_energy(self, energy):
        return self._tunable_bl.set_energy(energy)


    @task
    def set_resolution(self, new_resolution):
        return
        

    @task
    def move_detector(self, detector_distance):
        return

    @task
    def data_collection_cleanup(self):
        self.execute_command("close_fast_shutter")

    @task
    def close_fast_shutter(self):
        self.execute_command("close_fast_shutter")


    @task
    def open_fast_shutter(self):
        self.execute_command("open_fast_shutter")

        
    @task
    def move_motors(self, motor_position_dict):
        for motor in motor_position_dict.keys(): #iteritems():
            position = motor_position_dict[motor]
            if type(motor) == types.StringType:
                # find right motor object from motor role in diffractometer obj.
                motor_role = motor
                motor = self.bl_control.diffractometer.getDeviceByRole(motor_role)
                del motor_position_dict[motor_role]
                if motor is None:
                  continue
                motor_position_dict[motor]=position

            logging.getLogger("HWR").info("Moving motor '%s' to %f", motor.getMotorMnemonic(), position)
            motor.move(position)

        while any([motor.motorIsMoving() for motor in motor_position_dict.iterkeys()]):
            logging.getLogger("HWR").info("Waiting for end of motors motion")
            time.sleep(0.5)  


    @task
    def open_safety_shutter(self):
        return
        #self.bl_control.safety_shutter.openShutter()
        #while self.bl_control.safety_shutter.getShutterState() == 'closed':
        #  time.sleep(0.1)


    @task
    def close_safety_shutter(self):
        return
        #self.bl_control.safety_shutter.closeShutter()
        ##while self.bl_control.safety_shutter.getShutterState() == 'opened':
          #time.sleep(0.1)


    @task
    def prepare_intensity_monitors(self):
        self.execute_command("adjust_gains")


    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""):
        return self._detector.prepare_acquisition(take_dark, start, osc_range, exptime, npass, number_of_images, comment)


    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        return self._detector.set_detector_filenames(frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path)


    def prepare_oscillation(self, start, osc_range, exptime, npass):
        return self._detector.prepare_oscillation(start, osc_range, exptime, npass)

    
    def do_oscillation(self, start, end, exptime, npass):
        return self._detector.do_oscillation(start, end, exptime, npass)
    
  
    def start_acquisition(self, exptime, npass, first_frame):
        return self._detector.start_acquisition(exptime, npass, first_frame)
    
      
    def write_image(self, last_frame):
        return self._detector.write_image(last_frame)


    def stop_acquisition(self):
        return self._detector.stop_acquisition()
        
      
    def reset_detector(self):
        return self._detector.reset_detector()
        

    def prepare_input_files(self, files_directory, prefix, run_number, process_directory):

        i = 1
        logging.info("Creating XDS (MAXLAB) processing input file directories")

        self.xds_template    = "/home/blissadm/mxCuBE-V2.0/dp_file_templates/xdstemplate_maxlab.inp"
        self.mosflm_template = "/home/blissadm/mxCuBE-V2.0/dp_file_templates/mosflmtemplate_maxlab.inp"

        try:
           self.xds_template_buf    = open(self.xds_template).read()
           self.mosflm_template_buf = open(self.mosflm_template).read()
           self.write_files = True
        except:
           print "Cannot find template for xds and mosflm input files "
           self.write_files = False 

        while True:
          xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
          xds_directory = os.path.join(process_directory, xds_input_file_dirname)

          if not os.path.exists(xds_directory):
            break

          i+=1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
        mosflm_directory = os.path.join(process_directory, mosflm_input_file_dirname)
        logging.info("  - mosflm directory: %s", mosflm_directory)
   
        self.raw_data_input_file_dir = os.path.join(files_directory, "process", xds_input_file_dirname)
        self.mosflm_raw_data_input_file_dir = os.path.join(files_directory, "process", mosflm_input_file_dirname)

        for dir in (self.raw_data_input_file_dir, xds_directory):
          self.create_directories(dir)
          logging.info("Creating XDS processing input file directory: %s", dir)
          os.chmod(dir, 0777)

        for dir in (self.mosflm_raw_data_input_file_dir, mosflm_directory):
          self.create_directories(dir)
          logging.info("Creating MOSFLM processing input file directory: %s", dir)
          os.chmod(dir, 0777)
         
        raw_hkl2000_dir = os.path.join(files_directory, "process", "hkl2000")
        hkl2000_dir = os.path.join(process_directory, "hkl2000")
        for dir in (raw_hkl2000_dir, hkl2000_dir):
          self.create_directories(dir)
          os.chmod(dir, 0777)
 
        try: 
          try: 
              os.symlink(files_directory, os.path.join(process_directory, "links"))
          except os.error, e:
              if e.errno != errno.EEXIST:
                  raise
        except:
            logging.exception("Could not create processing file directory")

        return xds_directory, mosflm_directory

    @task
    def write_input_files(self, collection_id):

        # assumes self.xds_directory and self.mosflm_directory are valid

        #print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
        #print "WRITING INPUT FILES"
        #print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"

        dp_pars   = self.collect_pars_dp

        print "\nDATA COLLECT PARS"
        print "-------------------------------------------"
        pprint.pprint(dp_pars)
        print "-------------------------------------------"

        # get info from HWR server (is this updated when file is changed?)
        # GET some info from beamline control and beamline config objects
        mxlocalHO = self.getObjectByRole("beamline_configuration")
        self.detm = self.getObjectByRole("detector_distance")

        bcm_pars  = mxlocalHO["BCM_PARS"]
        spec_pars = mxlocalHO["SPEC_PARS"]

        # prepare / calculate some values (configured in mxlocal.xml - updated with lab6calibrate script)

        AXBeam = spec_pars["beam"].getProperty("ax")
        AYBeam = spec_pars["beam"].getProperty("ay")
        BXBeam = spec_pars["beam"].getProperty("bx")
        BYBeam = spec_pars["beam"].getProperty("by")

        # obtained from detm motor hardware object configured in mxcollect.xml
        detdistpos = self.detm.getPosition()

        XBeam = (AXBeam * detdistpos) + BXBeam
        YBeam = (AYBeam * detdistpos) + BYBeam

        # obtained from energy hardware object configured in mxcollect.xml
        wavelength = self.bl_control.energy.getCurrentWavelength()

# FROM SPEC - FOR XDS - DP_INPUTS (pixel size) are set in setup file with dp_files_setup macro
#  bcmpars["beam"]["x"] and "y" are those just calculated above XBeam, YBeam
#    _DP_INPUTS["orgx"] = bcmpars["beam"]["x"]/DP_INPUTS["pixel_size_x"]
#    _DP_INPUTS["orgy"] = bcmpars["beam"]["y"]/DP_INPUTS["pixel_size_y"]
#
        pixsize_x =  bcm_pars.getProperty("pixel_size_x")
        pixsize_y =  bcm_pars.getProperty("pixel_size_y")

        orgx = XBeam / pixsize_x
        orgy = YBeam / pixsize_y
       
        # XDS content goes here
        finfo    = dp_pars["fileinfo"]
        osc_seq  = dp_pars["oscillation_sequence"][0]

        xds_file_template    = "%(prefix)s_%(run_number)s_???.%(suffix)s" % finfo
        mosflm_file_template = "%(prefix)s_%(run_number)s_###.%(suffix)s" % finfo

        for input_file_dir, file_prefix in ((self.raw_data_input_file_dir, "../.."), (self.xds_directory, "../links")): 
	  xds_input_file = os.path.join(input_file_dir, "XDS.INP")

          xds_file = open(xds_input_file, "w")

          # IMAGE NUMBERING FOR XDS
          startImageNumber     = osc_seq["start_image_number"]
          endImageNumber       = osc_seq["start_image_number"] + osc_seq["number_of_images"] - 1

          startImageNumber_beg = osc_seq["start_image_number"]
          endImageNumber_beg   = osc_seq["start_image_number"] + 4
          if endImageNumber_beg > endImageNumber:
             endImageNumber_beg = endImageNumber

          startImageNumber_end = osc_seq["start_image_number"] + osc_seq["number_of_images"] - 5
          if startImageNumber_end < startImageNumber:
             startImageNumber_end = startImageNumber 

          endImageNumber_end   = osc_seq["start_image_number"] + osc_seq["number_of_images"] - 1

          startImageNumber_bkg = osc_seq["start_image_number"]
          endImageNumber_bkg   = osc_seq["start_image_number"] + 9
          if endImageNumber_bkg > endImageNumber: 
             endImageNumber_bkg = endImageNumber

          xdswait_exposure_time = int(osc_seq["exposure_time"]) + 20

          try:
              valdict = {
                  "user_comment":                 self.collect_pars_dp["comment"],
                  "I911-collection_start_time":   time.strftime("%Y-%m-%d %H:%M:%S"), # just a hack for now (2013-09-09) should be taken from the lims system in AbstractMultiCollect.py, so we are certain it's the same
                  "startImageNumber":             startImageNumber,
                  "endImageNumber":               endImageNumber,
                  "startImageNumber_bkg":         startImageNumber_bkg,
                  "endImageNumber_bkg":           endImageNumber_bkg,
                  "startImageNumber_beg":         startImageNumber_beg,
                  "endImageNumber_beg":           endImageNumber_beg,
                  "startImageNumber_end":         startImageNumber_end,
                  "endImageNumber_end":           endImageNumber_end,
                  "axisRange":                    osc_seq["range"],
                  "axisStart":                    osc_seq["start"],
                  "exposure_time":                osc_seq["exposure_time"],
                  "xdswait_exposure_time":        xdswait_exposure_time,
                  "wavelength":                   wavelength,
                  "imageDirectory":               finfo["directory"],
                  "fileTemplate":                 xds_file_template,
                  "detectorDistance":             detdistpos,
                  "xbeam_px":                     orgy,    
                  "ybeam_px":                     orgx,    
                  "detectorPixelSizeHorizontal":  pixsize_y,    
                  "detectorPixelSizeVertical":    pixsize_x,   
             } 
          except:
             import traceback
             traceback.print_exc()

          try:
             xds_buf = self.xds_template_buf % valdict
          except:
             import traceback
             traceback.print_exc()

          xds_file.write( xds_buf )
          xds_file.close()

          os.chmod(xds_input_file, 0666)

        for input_file_dir, file_prefix in ((self.mosflm_raw_data_input_file_dir, "../.."), (self.mosflm_directory, "../links")): 
	  mosflm_input_file = os.path.join(input_file_dir, "mosflm.inp")

          mosflm_file = open(mosflm_input_file, "w")

          # MOSFLM content goes here
          valdict = {
                  "user_comment":      self.collect_pars_dp["comment"],
                  "wavelength":        wavelength,
                  "detectorDistance":  detdistpos,
                  "xbeam":             YBeam,   
                  "ybeam":             XBeam,   
                  "imageDirectory":    finfo["directory"],
                  "fileTemplate":      mosflm_file_template,
                  "imageSuffix":       finfo["suffix"],
                  "startImageNumber":  osc_seq["start_image_number"],
                  "axisStart":         osc_seq["start"],
                  "axisEnd":           osc_seq["start"] + osc_seq["range"] * osc_seq["number_of_images"] - osc_seq["overlap"] * (osc_seq["number_of_images"] - 1),
          } 


          try:
             mosflm_buf  = self.mosflm_template_buf % valdict
          except:
             import traceback
             traceback.print_exc()

          mosflm_file.write( mosflm_buf )
          mosflm_file.close()
          os.chmod(mosflm_input_file, 0666)

        # write input file for STAC, JN,20140709
        stac_template = "/home/blissadm/mxCuBE-V2.0/dp_file_templates/stactemplate_maxlab.inp"
        try:
          stac_template_buf  =open(stac_template).read()
        except:
          print "Cannot find template for stac input files "
          return
        phi=self.bl_control.diffractometer.phiMotor.getPosition()
        sampx=self.bl_control.diffractometer.sampleXMotor.getPosition()
        sampy=self.bl_control.diffractometer.sampleYMotor.getPosition()
        phiy=self.bl_control.diffractometer.phiyMotor.getPosition()
        phi=self.bl_control.diffractometer.phiMotor.getPosition()
         
        for stac_om_input_file_name, stac_om_dir in (("mosflm.descr", self.mosflm_directory), 
                                                     ("xds.descr", self.xds_directory),
                                                     ("mosflm.descr", self.mosflm_raw_data_input_file_dir),
                                                     ("xds.descr", self.raw_data_input_file_dir)):
          stac_om_input_file = os.path.join(stac_om_dir, stac_om_input_file_name)
          stac_om_file = open(stac_om_input_file, "w")

          if stac_om_input_file_name.startswith("xds"):
            om_type="xds"
            if stac_om_dir == self.raw_data_input_file_dir:
              om_filename=os.path.join(stac_om_dir, "CORRECT.LP")
            else:
              om_filename=os.path.join(stac_om_dir, "xds_fastproc", "CORRECT.LP")
          else:
            om_type="mosflm"
            om_filename=os.path.join(stac_om_dir, "bestfile.par")

          valdict = {
                  "omfilename":       om_filename,
                  "omtype":	      om_type,
                  "axisStart":        osc_seq["start"],
                  "kappaStart":       osc_seq["kappaStart"],
                  "phiStart":         osc_seq["phiStart"],
                  "sampx":            sampx,
                  "sampy":            sampy,
                  "phiy":             phiy,
                  "phi":              phi,
               
          }
          try:
             stac_buf  = stac_template_buf % valdict
          except:
             import traceback
             traceback.print_exc()

          stac_om_file.write(stac_buf)
          stac_om_file.close()
          os.chmod(stac_om_input_file, 0666)


    def get_wavelength(self):
        return self._tunable_bl.get_wavelength()
      

    def get_detector_distance(self):
        return

       
    def get_resolution(self):
        return self.bl_control.resolution.getPosition()


    def get_transmission(self):
        #return self.bl_control.transmission.getAttFactor()
        return None


    def get_undulators_gaps(self):
        und_gaps = [None]*3
        #i = 0
        #for undulator_cfg in self.bl_config.undulators:
        #    und_gaps[i]=self.bl_control.undulators.getUndulatorGap(undulator_cfg.getProperty("type"))
        #    i+=1
        return und_gaps


    def get_resolution_at_corner(self):
      return self.execute_command("get_resolution_at_corner")


    def get_beam_size(self):
      return (self.execute_command("get_beam_size_x"), self.execute_command("get_beam_size_y"))


    def get_slit_gaps(self):
      #return (None,None)
      return (self.execute_command("get_slit_gap_h"), self.execute_command("get_slit_gap_v"))


    def get_beam_shape(self):
      return self.execute_command("get_beam_shape")

    
    def get_measured_intensity(self):
      try:
        val = self.getChannelObject("image_intensity").getValue()
        return float(val)
      except:
        return 0


    def get_machine_current(self):
      try:
        val = self.bl_control.machine_current.getCurrent()
        return float(val)
      except:
        return 0

      #return ""
      #return self.bl_control.machine_current.getCurrent()


    def get_machine_message(self):
      return ""
      #return self.bl_control.machine_current.getMessage()


    def get_machine_fill_mode(self):
      return ""
      #return self.bl_control.machine_current.getFillMode()


    def get_cryo_temperature(self):
      try:
        val = self.bl_control.cryo_stream.getTemperature()
        return float(val)
      except:
        return 0
      #return ""
      #return self.bl_control.cryo_stream.getTemperature()


    def getCurrentEnergy(self):
      return self._tunable_bl.getCurrentEnergy()


    def get_beam_centre(self):
      return (self.execute_command("get_beam_centre_x"), self.execute_command("get_beam_centre_y"))

    
    def getBeamlineConfiguration(self, *args):
      # TODO: change this to stop using a dictionary at the other end
      return self.bl_config._asdict()


    def isConnected(self):
        return True

      
    def isReady(self):
        return True
 
    
    def sampleChangerHO(self):
        return self.bl_control.sample_changer


    def diffractometer(self):
        return self.bl_control.diffractometer


    def dbServerHO(self):
        return self.bl_control.lims


    def sanityCheck(self, collect_params):
        return
    

    def setBrick(self, brick):
        return


    def directoryPrefix(self):
        return self.bl_config.directory_prefix


    def store_image_in_lims(self, frame, first_frame, last_frame):
        if isinstance(self._detector, CcdDetector):
            return True

        if isinstance(self._detector, PixelDetector):
            if first_frame or last_frame:
                return True

    def get_flux(self):
        return 0
        #return self.bl_control.flux.getCurrentFlux()

    """
    getOscillation
        Description: Returns the parameters (and results) of an oscillation.
        Type       : method
        Arguments  : oscillation_id (int; the oscillation id, the last parameters of the collectOscillationStarted
                                     signal)
        Returns    : tuple; (blsampleid,barcode,location,parameters)
    """
    def getOscillation(self, oscillation_id):
      return self.oscillations_history[oscillation_id - 1]
       

    def sampleAcceptCentring(self, accepted, centring_status):
      self.sample_centring_done(accepted, centring_status)


    def setCentringStatus(self, centring_status):
      self._centring_status = centring_status


    """
    getOscillations
        Description: Returns the history of oscillations for a session
        Type       : method
        Arguments  : session_id (int; the session id, stored in the "sessionId" key in each element
                                 of the parameters list in the collect method)
        Returns    : list; list of all oscillation_id for the specified session
    """
    def getOscillations(self,session_id):
      #TODO
      return []



    def get_archive_directory(self, directory):
        res = None

        dir_path_list = directory.split(os.path.sep)
        try:
          suffix_path=os.path.join(*dir_path_list[4:])
        except TypeError:
          return None
        else:
          if 'inhouse' in directory:
            #albnar 20/08/2014: Try to have the same behavior of the visitors
            #archive_dir = os.path.join('/data/ispyb/', dir_path_list[3], suffix_path)
            archive_dir = os.path.join('/data/ispyb/', dir_path_list[4], *dir_path_list[5:])
          else:
            archive_dir = os.path.join('/data/ispyb/', dir_path_list[4], *dir_path_list[5:])
          if archive_dir[-1] != os.path.sep:
            archive_dir += os.path.sep

          return archive_dir
         

    # JN, 20140904, save snapshot in the RAW_DATA folder in the end of the data collection 
    def do_collect(self, owner, data_collect_parameters):

        AbstractMultiCollect.do_collect(self, owner, data_collect_parameters)

        file_parameters = data_collect_parameters["fileinfo"] 
        snapshot_directory = self.get_archive_directory(file_parameters["directory"])
        snapshot_filename = "%s_%s_*.snapshot.jpeg" % (file_parameters["prefix"],
                                                                file_parameters["run_number"]) 
        full_snapshot = os.path.join(snapshot_directory,
                                             snapshot_filename)
        os.system("cp %s %s" % (full_snapshot,file_parameters["directory"]))
        #logging.info("cp %s %s" % (full_snapshot,file_parameters["directory"]))

