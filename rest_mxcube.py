import bottle
from bottle import get, post, request, response, route, static_file, redirect, error
from bottle import GeventServer, run
from beaker.middleware import SessionMiddleware
import gevent
import gevent.event
from gevent import monkey; monkey.patch_all()
import os, src.RestParser

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': './data',
    'session.auto': True
}
mxcube = bottle.Bottle()
mxcube_app = SessionMiddleware(mxcube, session_opts)

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

sampleCentring = RestParser.SampleCentring()
sample = RestParser.Sample()
beamline = RestParser.BeamLine() 
collection = RestParser.Collection() 
# queue = RestParser.Queue() 

@error(404)
def error404(error):
    return 'Nothing to see here, move on'

@mxcube.route("/")
def serve_static_file():
   return static_file('Main.html', os.path.dirname(__file__))

@mxcube.route("/<url:path>")
def serve_static_file(url):
   return static_file(url, os.path.dirname(__file__))

###----SSE SAMPLE VIDEO STREAMING----###
def sse_pack(d):
    """Pack data in SSE format"""
    buffer = ''
    for k in ['retry','id','event','data']:
        if k in d.keys():
            buffer += '%s: %s\n' % (k, d[k])
    return buffer + '\n'
msg = {
    'retry': '1000'
    }  
msg['event'] = 'message'

@mxcube.route('/mxcube/api/v0.1/samplecentring/camera/stream')
def stream_video():
    """it just send a message to the client so it knows that there is a new image. A HO is supplying that image"""
    bottle.response.content_type = 'multipart/x-mixed-replace; boundary="!>"'
    response.content_type ="text/event-stream"
    response.cache_control = 'no-cache'
    response.headers['content-type'] ='text/event-stream'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['CharacterEncoding'] = "utf-8"
    event_id = 0
    print "going to stream video"
    while True:
        sampleCentring.video.new_frame.wait()
        im = sampleCentring.video.new_frame.get()    
        msg.update({
         'event': 'update',
         'data' : im,
         'id'   : event_id
        })
        #print "mezu bat", str(event_id), str(len(im))
        yield sse_pack(msg)
        event_id += 1
        #gevent.sleep(0.08)
        gevent.sleep(0.1)

###----SAMPLE CENTRING----###
@mxcube.route("/mxcube/api/v0.1/samplecentring/:id/move", method='PUT')
def move_motor(id):
    """SampleCentring: move "id" moveable to the position specified in the data:position
    Moveable can be a motor (kappa, omega, phi), a ligth, light/zoom level.
    data = {generic_data, "moveable": id, "position": pos}
    return_data={"result": True/False}
    """
    print "move called  ", id
    data = dict(request.POST.items())
    return sampleCentring.move(data)

@mxcube.route("/mxcube/api/v0.1/samplecentring/status", method='GET')
def get_status():
    """SampleCentring: get generic status, positions of moveables ...
    data = {generic_data}
    return_data = { generic_data, 
                  Moveable1:{'Status': status, 'position': position}, 
                  ...,  
                  MoveableN:{'Status': status, 'position': position} 
                  }
    """
    data = dict(request.POST.items())
    return sampleCentring.getStatus()

@mxcube.route("/mxcube/api/v0.1/samplecentring/:id/status", method='GET')
def get_status_of_id(id):
    """SampleCentring: get status of element with id:"id"
    data = {generic_data, 'Moveable1', ..., MoveableN}
    return_data = {'Status': status, 'position': position}
    """
    data = dict(request.POST.items())
    return sampleCentring.getStatus(data)

@mxcube.route("/mxcube/api/v0.1/samplecentring/camera/subscribe", method='GET')
def get_camera_view():
    """SampleCentring: subscribe to the streaming
    data = {generic_data} #or nothing?
    return_data={"url": url}
    """
    data = dict(request.POST.items())
    print "In sample camera"
    print data
    return {'url':'/mxcube/api/v0.1/samplecentring/camera/stream'}
    print "subscribing done"
@mxcube.route("/mxcube/api/v0.1/samplecentring/camera/unsubscribe", method='GET')
def get_camera_view():
    """SampleCentring: subscribe from the streaming
    data = {generic_data} #or nothing?
    return_data={"result": True/False}
    """
    print "In sample camera unsubscribe"
    data = dict(request.POST.items())
    print "unsubscribing done"
    return True

@mxcube.route("/mxcube/api/v0.1/samplecentring/centring/:id", method='GET')
def get_centring_of_id(id):
    """SampleCentring: get centring point position of point with id:"id", id=1,2,3...
    data = {generic_data, "point": id}
    return_data = {"id": {x,y}}
    """
    data = dict(request.POST.items())
    return sampleCentring.getCentring(data)

@mxcube.route("/mxcube/api/v0.1/samplecentring/centring/:id", method='POST')
def put_centring_with_id(id):
    """SampleCentring: set centring point position of point with id:"id", id=1,2,3...
    data = {generic_data, "point": id, "position": {x,y}}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return sampleCentring.setCentring(data)

@mxcube.route("/mxcube/api/v0.1/samplecentring/centre", method='PUT')
def centre():
    """Start centring procedure
    data = {generic_data, "Mode": mode}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return sampleCentring.centre(data)

@mxcube.route("/mxcube/api/v0.1/samplecentring/snapshot", method='PUT')
def snapshot():
    """Save snapshot of the sample view
    data = {generic_data, "Path": path} # not sure if path should be available, or directly use the user/proposal path
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return sampleCentring.snapshot(data)

###----SAMPLE----###
@mxcube.route("/mxcube/api/v0.1/samples/:id", method='POST')
def add_sample(id):
    """Add the information of the sample with id:"id"
    data = {generic_data, "SampleId":id, sample_data={'holderLength': 22.0, 'code': None, 'containerSampleChangerLocation': '1', 'proteinAcronym': 'Mnth', 'cellGamma': 0.0, 'cellAlpha': 0.0, 'sampleId': 444179, 'cellBeta': 0.0, 'crystalSpaceGroup': 'R32', 'sampleLocation': '2', 'sampleName': 'sample-E02', 'cellA': 0.0, 'diffractionPlan': {}, 'cellC': 0.0, 'cellB': 0.0, 'experimentType': 'Default'}}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.addSample(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id", method='PUT')
def update_sample(id):
    """Update the information of the sample with id:"id"
    data = {generic_data, "SampleId":id, sample_data={'holderLength': 22.0, 'code': None, 'containerSampleChangerLocation': '1', 'proteinAcronym': 'Mnth', 'cellGamma': 0.0, 'cellAlpha': 0.0, 'sampleId': 444179, 'cellBeta': 0.0, 'crystalSpaceGroup': 'R32', 'sampleLocation': '2', 'sampleName': 'sample-E02', 'cellA': 0.0, 'diffractionPlan': {}, 'cellC': 0.0, 'cellB': 0.0, 'experimentType': 'Default'}}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.updateSample(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id", method='GET')
def get_sample(id):
    """Get the information of the sample with id:"id"
    data = {generic_data, "SampleId":id}
    return_data={"SampleId":id, sample_data={'holderLength': 22.0, 'code': None, 'containerSampleChangerLocation': '1', 'proteinAcronym': 'Mnth', 'cellGamma': 0.0, 'cellAlpha': 0.0, 'sampleId': 444179, 'cellBeta': 0.0, 'crystalSpaceGroup': 'R32', 'sampleLocation': '2', 'sampleName': 'sample-E02', 'cellA': 0.0, 'diffractionPlan': {}, 'cellC': 0.0, 'cellB': 0.0, 'experimentType': 'Default'}}
    """
    data = dict(request.POST.items())
    return samples.getSample(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id", method='DELETE')
def delete_sample(id):
    """Delete the sample with id:"id"
    data = {generic_data, "SampleId":id}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.deleteSample(data)

@mxcube.route("/mxcube/api/v0.1/samples", method='GET')
def get_sample_list():
    """Get the sample list already on the queue
    data = {generic_data}
    return_data={"SampleId1":id, ..., "SampleIdN":id}
    """
    data = dict(request.POST.items())
    return samples.getSampleList()

@mxcube.route("/mxcube/api/v0.1/samples/:id/mode", method='POST')
def set_sample_mode(id):
    """Set sample changer mode: sample changer, manually mounted, ... (maybe it is enoug to set for all the same mode)
    data = {generic_data, "Mode": mode}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.getMode(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id/centring", method='PUT')
def set_centring_mode(id):
    """Set centring method: semi auto, fully auto,  ...
    data = {generic_data, "Mode": mode}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.setCentring(data)

###----SAMPLECHANGER----###
@mxcube.route("/mxcube/api/v0.1/samples/:id/mount", method='PUT')
def mount_sample(id):
    """Mount sample with id:"id"
    data = {generic_data, "SampleId": id}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.mountSample(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id/umount", method='PUT')
def umount_sample():
    """Umount mounted sample
    data = {generic_data}
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.umountSample(data)

###----COLLECTION----###
@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid/mode", method='POST')
def set_collection_method(method):
    """Define the collection method, standard collection, helical, mesh
    data={generic_data, "Method":method}
    return_data={"result": True/False}
    OBSOLETE BY ADD COLLECTION
    """
    data = dict(request.POST.items())
    return collection.defineCollectionMethod(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid", method='PUT')
def update_collection(method):
    """update a collection into the sample queue ***asociated to a sample!
    data={generic_data, "Method":method, "SampleId": sampleid ,"CollectionId": id, parameters}, 
    for example for a standard data collection:
    data={generic_data, "Method":StandardCollection, "SampleId": sampleid, "CollectionId": colid, parameters:{
            osc_range: { label: "Oscillation range", default_value: 1.0, value: 0 },
            osc_start: { label: "Oscillation start", default_value: 0, value: 0 },
            exp_time: { label: "Exposure time", default_value: 10.0, value: 0 },
            n_images: { label: "Number of images", default_value: 1, value: 0 },
            energy: {label: "Energy", default_value: 12.3984, value: 0 },
            resolution: {label: "Resolution", default_value: 2.498, value: 0 },
            transmission: {label: "Transmission", default_value: 100.0, value: 0} },
          }, 
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return collection.updateCollection(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid", method='POST')
def add_collection(id, colid):
    """Add a collection into the sample queue ***asociate to a sample!
    data={generic_data, "Method":method, "SampleId": sampleid ,"CollectionId": id, parameters}, 
    for example for a standard data collection:
    data={generic_data, "Method":StandardCollection, "SampleId": sampleid, "CollectionId": colid, parameters:{
            osc_range: { label: "Oscillation range", default_value: 1.0, value: 0 },
            osc_start: { label: "Oscillation start", default_value: 0, value: 0 },
            exp_time: { label: "Exposure time", default_value: 10.0, value: 0 },
            n_images: { label: "Number of images", default_value: 1, value: 0 },
            energy: {label: "Energy", default_value: 12.3984, value: 0 },
            resolution: {label: "Resolution", default_value: 2.498, value: 0 },
            transmission: {label: "Transmission", default_value: 100.0, value: 0} },
          }, 
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    print data
    return collection.addCollection(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid", method='GET')
def get_collection(id):
    """get the collection with id:"colid"
    data={generic_data}, 
    for example for a standard data collection:
    return_data={"Method":StandardCollection,  "SampleId": sampleid, "CollectionId": colid, parameters:{
            osc_range: { label: "Oscillation range", default_value: 1.0, value: 0 },
            osc_start: { label: "Oscillation start", default_value: 0, value: 0 },
            exp_time: { label: "Exposure time", default_value: 10.0, value: 0 },
            n_images: { label: "Number of images", default_value: 1, value: 0 },
            energy: {label: "Energy", default_value: 12.3984, value: 0 },
            resolution: {label: "Resolution", default_value: 2.498, value: 0 },
            transmission: {label: "Transmission", default_value: 100.0, value: 0} },
          }, 
    """
    data = dict(request.POST.items())
    return collection.getCollection(data)

@mxcube.route("/mxcube/api/v0.1/samples/:id/collections", method='GET')
def get_collection_list(id):
    """get the collection with id:"id"
    data={generic_data}, 
    for example for a standard data collection:
    return_data={"Method":StandarCollection,  "SampleId": sampleid, "CollectionId": colid, parameters:{
            osc_range: { label: "Oscillation range", default_value: 1.0, value: 0 },
            osc_start: { label: "Oscillation start", default_value: 0, value: 0 },
            exp_time: { label: "Exposure time", default_value: 10.0, value: 0 },
            n_images: { label: "Number of images", default_value: 1, value: 0 },
            energy: {label: "Energy", default_value: 12.3984, value: 0 },
            resolution: {label: "Resolution", default_value: 2.498, value: 0 },
            transmission: {label: "Transmission", default_value: 100.0, value: 0} },
          }, 
    """
    data = dict(request.POST.items())
@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid", method='DELETE')
def delete_collection(id):
    """delete the collection with id:"id"
    data={generic_data, "CollectionId": id},   
    return_data={"result": True/False}
    """
    data = dict(request.POST.items())
    return samples.getCollection(data)
@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/status", method='GET')
def get_collection_status(id):
    """get the status of all data collections, (running, stopped, cancelled, finished, ...)
    data={generic_data},   
    return_data={ {"CollectionId": id1, "Status": status}, ..., {"CollectionId": idN, "Status": status} }
    """
    data = dict(request.POST.items())
    return collection.getCollectionStatus(data)
@mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid/status", method='GET')
def get_collection_id_status(id):
    """get the status of the collection with id:"id", (running, stopped, cancelled, finished, ...)
    data={generic_data},
    return_data={"CollectionId": id, "Status": status}
    """
    data = dict(request.POST.items())
    return collection.getCollectionStatus(data)
# @mxcube.route("/mxcube/api/v0.1/samples/:id/collections/:colid/run", method='PUT')
# def get_collection_id_status(id):
#     """run the collection with id:"colid"
#     data={generic_data},
#     return_data={"CollectionId": id, "Status": status}
#     """
#     data = dict(request.POST.items())
#     return collection.runCollectionStatus(data)

###----BEAMLINE----###
@mxcube.route("/mxcube/api/v0.1/beamline/:id/move", method='PUT')
def move_motor(id):
    """Beamline: move "id" moveable (energy, resolution ...) to the position specified
    data = {generic_data, "moveable": id, "position": pos}
    return_data={"result": True/False}
    """  
    data = dict(request.POST.items())
    print data, id
    return beamline.move(data)

@mxcube.route("/mxcube/api/v0.1/beamline/status", method='GET')
def get_bl_status(id):
    """Beamline: get beamline generic status (energy, resolution ...)
    data = {generic_data}
    return_data = { generic_data, {"moveable1":position}, ..., {"moveableN":position} , xxxx }
    """  
    data = dict(request.POST.items())
    return beamline.getStatus()

@mxcube.route("/mxcube/api/v0.1/beamline/:id/status", method='GET')
def get_bl_id_status(id):
    """Beamline: get beamline status of id:"id"
    data = {generic_data, "Moveable":id}
    return_data = {"Moveable": id, "Status": status}
    """ 
    data = dict(request.POST.items())
    return beamline.getStatus(data)

###----SAMPLE QUEUE----###


if __name__ == '__main__':
   run(app=mxcube_app, host="", port="8081",server=GeventServer)
   