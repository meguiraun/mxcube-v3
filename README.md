# MXCUBE V3 - MAXIV

This is the repository of the mxcube v3 (aka web mxcube) with some specifities from Maxiv (basically, in order to test some feautures in our 911-3 beamline a cleanup of the HO files has been done, as well as a minor modification in the HO of the camera (MaxLabMDCamera, instead of saving the image into a file send directly to the web client), no additional modifications have been done in the HO/HR files.

Compared to the mxcube-web proof of concept there are several big differences (and of course, similarities, inspirations and code thievery):

- The original app.py (server) is not longer used, a new server code has been developed (*rest_mxcube*). As its name indicates, it follows a REST API architecture (at least tries to...) and some code has left apart (login stuff mainly)
- The above server file only contains server stuff, all the HO related code has been removed. Whenever a rest call is received the backend will call the appropiate aClass.aMethod in the RestParser file
- RestParser: this is where all the HO bussines is done (or will be...). It is split into different classes according to their functions:
	* SampleCentring()
	* Sample()
	* BeamLine() 
	* Collection() 
- There is not any kind of well though web layout, just functionalities.
- There are only present the relevant HOs files for the current features

## Current Features

### Frontend

- Sample Centring: image retrieval and display from our MD2, movement of the omega, kappa and phi motors, activate back ligth (setLevel not implemented), zoom level adjustment, clicking on the image gives the click-position and it displays on top of the image (for later centring algorithm)
- Beamline setup: movement of the associated motors, the ho-xml adaptation is not done, but backend/frontend code is already there
- QueueTree: currently the sample list is hardcoded in the jacascript code, however it should be easy to change to data sent by the server (at this moment it would be hardcoded/file). You can add standard collections to the selected sample(s), also remove. The ability of adding other types of nodes is not implemented (not needed now so left apart but easily addeable), the addition of a new node is triggered by the StandardCollection component (only the action, not the data). 
- Standard collection, not too much to say, just display and trigger the addition of a new node into the queue. It misses sending the parameters

### Backend

- Check documentation to see all the methods, it will require many more but for the test I did it was enough.
- Missing to implement several critical features such as running the queue and move some beamline motors, however that is more a job for the RestParser than for the server

## Improvements in HO
- Motor methods names are inconsistent in some cases (move vs moveToPosition), which in turn requires extra ugly logic in the server. Of course, this is out of the scope ...

## Next steps
- Add missing features to the items explained above
- Use the so called Multicollect to fully configure a single experiment, which means sending all the relevant data to the appropriate HO and executing some actions (prepare/start_oscilation? etc. on those HOs).
- Use the QueueModel of the v2.1 for the sample/experiment queue management? There are some qt dependencies to be resolved though (it can be left out for a first single-crystal experiment)
- Uniform data interchange between components (define a single dict for all cases? perhaps it will lead to noticeable unnecessary bandwidth usage?)
- Rest api improvements: keep adding methods and define the data interchange properly
- Rethink the class organization of the RestParser.py, I think that once we start adding features it will be a complete mess, specially when we mix HOs from different ~components
- Keep going on development!

## Documentation
- I have tried to generate the documentation for the hardware repository, but sphinx complains, but still there is a kind of doc for the HO that are used so far
- Also added doc for the rest api
- check ./doc/ folder

## Running
- Execute the following (same as before):
	* bin/mxcube-server /home/mikel/BioMAX/mxcube-v3/src/HardwareObjects.xml/

