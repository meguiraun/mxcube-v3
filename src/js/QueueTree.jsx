/** @jsx React.DOM */

var SampleTree = React.createClass({

    getInitialState: function () {
        return {
            sampleList :[{sample:'Sample01', selected:false, nodes:[{name:'Charac01', selected:false, params:{}}, {name:'Collection01', selected:false, params:{}}, {name:'Collection02',selected:false, params:{}}]},{sample:'Sample02', selected:false, nodes: [{name:'Collection01',selected:false, params:{}}]},{sample:'Sample03', selected:false, nodes:[]}],
            selectedSamples : []
            };
    },
    getSampleList: function(){
		console.log('getting sample litst')
		//this.setState({sampleList : samples});
		// $.ajax({
		//   url: '/mxcube/api/v0.1/samples',
		//   data: {},
		//   type: 'GET',
		//   success: function(res) {
		//       return res
		//       console.log(res);
		//		this.setState({sampleList : samples});
		//     },
		//   error: function(error) {
		//       console.log(error);
		//     },
// });
    },

    getNodeNames: function(sample){
    	//It returns an array with the names of all the nodes in the given sample, making the code for the addition of nodes simpler
    	//TODO: once the sample is fournd do not continue iterating (return/break at that point)
        auxSamples = this.state.sampleList
        nodeArr = []
        for (k = 0; k < auxSamples.length; k++){
        	console.log('in loop nodenames  '+k )
          	if (auxSamples[i]['sample'] == sample){
        		for (j =0; j < auxSamples[i]['nodes'].length; j++){
              		nodeArr.push(auxSamples[i]['nodes'][j]['name'])
              	}           
      		}	
        }
        return nodeArr;
    },
    addSample: function(){
    	//TODO: up to now I am assuming the ideal case of the sample list is sent by the server
    },

  	addNodeToSample: function(item){
  		//Add a node to all the selected samples. Currently it only adds collection like nodes. the 'item' element is sent via backbone events from  StandardCollection.jsx
  		//TODO: once the sample is fournd do not continue iterating (return/break at that point)
  		//TODO: refactor the data sent via backbone events, harmonize etc. In fact, in the event only params are needed (I think) 
  		//TODO: add (default) params
		samples = this.state.sampleList
		selSamples = this.getSelectedSamples()
		if (selSamples.length == 0){
			alert('Select a sample')
			return
		}
		for (var elem in selSamples){ //0, 1, 2, ...
			for (i = 0; i < samples.length; i++){
				console.log('in inner loop   '+i)
				console.log(samples[i].sample)
				if (samples[i].sample == selSamples[elem]){
					nodeArr = this.getNodeNames(selSamples[elem]) //Kontuz!!! This fuynction has also an iteration, if same counter name is used, it will be populated here, (so, do not use i,j,k... when calling methods) --> Conclusion: namespaces refactoring needed (var, this, fuck...)
					var sameTypeArr= nodeArr.filter(function(d){ return /Collection/.test(d); }); //Collection01, Collection02....
					sameTypeArr.sort()
					if (sameTypeArr.length >0){
						newNum = parseInt(sameTypeArr[sameTypeArr.length -1].match(/\d+/)[0])+1 
					}
					else{
						newNum=1
					}
					newName = item['type']+ newNum//I know that there might be missing number if there have been deleted previosly

					// if (samples[i].nodes.indexOf(item['node']) > -1){
					//name does not exits
					samples[i]['nodes'].push({name: newName, selected: false, params: {}})
					}
			}
		}
		this.setState({sampleList: samples})
  	},

  	removeNodeFromSample: function(sample, node){
		//TODO: once the sample is fournd do not continue iterating (return/break at that point)
		//TODO: javascrtip event data (element id contains sample&node names) can be used instead of sending arguments, resulting in simpler react code
      	samples = this.state.sampleList
      	for (i = 0; i < samples.length; i++){
        	if (samples[i].sample == sample){
            	var index = samples[i].nodes.indexOf(node);
              	if (index > -1) {
                  samples[i].nodes.splice(index, 1);
              	}
        	}
        }
      	this.setState({sampleList: samples})
  	},

	toggleSelected: function(ev){
	  	//Add selection status of sample and node to the general state
	  	//TODO: sample and node are independent, useful if sample selected automatically select all its nodes? Useful when running queue, and when adding a new node it does not pay attention to the selected status of the nodes
	    //id types: smpSample02, colSample01Collection05..
		auxName = ev.target.id
		auxSamples = this.state.sampleList
		type = auxName.substr(0,3) //col || smp
		auxName = auxName.replace(type,'')
		auxName = auxName.replace('Checked','')
		//finding sample number position
		smpNum = auxName.match(/\d+/)[0]
		index = auxName.indexOf(smpNum)
		smpName = auxName.substr(0, index) +smpNum //e.g. Sample05

      	if (type == 'col'){
			//finding collection name
			colName = auxName.substr(index+smpNum.length) //number as 02 can appear
			colNum =  colName.match(/\d+/)[0]
			//set selected status
			//TODO: if found do not continue with the loop!!
			for (i = 0; i < auxSamples.length; i++){
            	if (auxSamples[i]['sample']== smpName){
                	for (j = 0; j < auxSamples[i]['nodes'].length; j++){
                    	if (auxSamples[i]['nodes'][j]['name'] == colName){
                        	auxSamples[i]['nodes'][j]['selected']= document.getElementById(ev.target.id).checked
                      	}
                  	}
             	}
          	}
      	}
      	else {//smp simple
        	for (i = 0; i < auxSamples.length; i++){
            	if (auxSamples[i]['sample']== smpName){
                	auxSamples[i]['selected'] = document.getElementById(ev.target.id).checked
              	}
          	}
      	}
      	this.setState({sampleList: auxSamples})
  	},

	getSelectedSamples: function(){
		var arr = []
		auxSamples = this.state.sampleList
		for (i = 0; i < auxSamples.length; i++){
		  	if (auxSamples[i]['selected']){
    			arr.push(auxSamples[i]['sample'])
		  	}
		}
		return arr;   
	},

 	getSelectedNodes: function(){
		//TODO: not sure if needed
  	},

	runCollection:function(){
		//TODO: send everything (this.state.sampleLits) and filter in the server, OR send only the selections
		//TODO: data to be sent 
		console.log("************* running collection")	
		$.ajax({
		url: '/mxcube/api/v0.1/samples/sampid/collections/colid/run"',
		data: {'parameters': this.state, 'Method': 'StandardCollection', 'SampleId':'samp01', 'CollectionId': 'col01'},
		type: 'POST',
		success: function(res) {
		  console.log(res);
		},
		error: function(error) {
		  console.log(error);
		},
		});
	},

	componentWillMount: function() {
		window.app_dispatcher = _.extend({}, Backbone.Events);
		window.app_dispatcher.on("SampleTree:new_collection", this.addNodeToSample);
	},

  	componentWillUnMount: function() {
    	window.app_dispatcher.off("SampleTree:new_collection", this.addNodeToSample);
  	},

	componentDidMount: function(){
		console.log('mounted');
  	},

	anAction: function(msg){
		console.log(msg)  
	},

	render: function () {
		console.log('rendering tree');
   		console.log(this.getSelectedSamples())
    	that = this//for fixing namespace issue in the next linked loops

 		return <div className="panel panel-default"> 
              		<div className="panel-heading clearfix">
            			   <b className="panel-title pull-left">Sample Tree</b>
                  </div>  

                  <div className="panel-body">
                    <ul >
                      {this.state.sampleList.map(function (item){
                      return <li>
                          <input type="checkbox" id={'smp'+item['sample']+'Checked'} onChange={that.toggleSelected}></input>
                          <label>{item['sample']}</label>
                          <button type="button" className="btn btn-success btn-xs" id={item['sample']}  onClick={that.anAction}> 'delete'</button>
                             <ul>
                              {item['nodes'].map(function (node){
                              return <li>
                                  <input type="checkbox" id={'col'+item['sample']+node['name']+'Checked'} onChange={that.toggleSelected}></input>
                                  <label>{node}</label>
                                  <button type="button"  id={item['sample']+node} onClick={that.removeNodeFromSample.bind(that,item['sample'],node)}>'Remove' </button>
                                 </li>
                          })}
                          </ul></li>; })}
                        
                      </ul>
                  <button onClick={this.runCollection}>Run queue</button>    
                  </div>  
            </div>
	    },	
	});

React.render(<SampleTree/>, document.getElementById('SampleTreeGoesHere'));
 