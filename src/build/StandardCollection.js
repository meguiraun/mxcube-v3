/** @jsx React.DOM */

var discrete_params =  {osc_range: { label: "Oscillation range", default_value: 1.0 },
                        osc_start: { label: "Oscillation start", default_value: 0 },
                        exp_time: { label: "Exposure time", default_value: 10.0 },
                        num_images: { label: "Number of images", default_value: 1 }} 

var StandardCollection = React.createClass({displayName: "StandardCollection",
    getInitialState: function () {
        return {
            osc_range: { label: "Oscillation range", default_value: 1.0, value: 1.0 },
            osc_start: { label: "Oscillation start", default_value: 0, value: 0 },
            exp_time: { label: "Exposure time", default_value: 10.0, value: 10.0 },
            num_images: { label: "Number of images", default_value: 1, value: 1 },
            energy: {label: "Energy", default_value: 12.3984, value: 12.3984 },
            resolution: {label: "Resolution", default_value: 2.498, value: 2.498 },
            transmission: {label: "Transmission", default_value: 100.0, value: 100.0},
          };
    },
    componentWillMount: function() {
        //window.app_dispatcher.on("queue:new_item", this._add_queue_item);
     },
    componentWillUnMount: function() {
       //window.app_dispatcher.off("queue:new_item", this._add_queue_item);
     },
    addCollection:function(){
      console.log("************* adding collection")
      console.log(this.state)
      auxState = this.state
      //cleaning unused backend data from the state
      for(i in auxState){
          delete auxState[i]['label']
          delete auxState[i]['default_value']
      }

      window.app_dispatcher.trigger("SampleTree:new_collection", { sample: "Sample01", node:'dummyName', type:'Collection', params: auxState});//, text: "Discrete", fields: discrete_params });

      $.ajax({
      url: '/mxcube/api/v0.1/samples/samp01/collections/col01',
      data: {'parameters': auxState, 'Method': 'StandardCollection', 'SampleId':'samp01', 'CollectionId': 'col01'},
      type: 'POST',
      success: function(res) {
          console.log(res);
        },
      error: function(error) {
          console.log(error);
        },
    });
    },


    // runCollection:function(){
    //   console.log("************* adding collection")
    //   console.log(this.state)
    //   $.ajax({
    //   url: '/mxcube/api/v0.1/samples/sampid/collections/colid/run"',
    //   data: {'parameters': this.state, 'Method': 'StandardCollection', 'SampleId':'samp01', 'CollectionId': 'col01'},
    //   type: 'POST',
    //   success: function(res) {
    //       console.log(res);
    //     },
    //   error: function(error) {
    //       console.log(error);
    //     },
    // });
    // },
    isNumberKey: function(ev){
        //in order to save the current params into the state 'enter' must be pressed
        console.log("checking numbers") 
        var charCode = (ev.which) ? ev.which : event.keyCode
        if (charCode > 31 && (charCode < 48 || charCode > 57)){
            console.log("is a number")  
            return false;}
        if (ev.key == "Enter"){
            console.log("enter pressed")
            var auxSt = this.state
            var aux = auxSt[ev.target.id]
            aux['value'] = ev.target.value
            this.setState(aux)
        }
        return true;
        },
 
    render: function() {
        return React.createElement("div", {className: "panel panel-default"}, 
                  React.createElement("div", {className: "panel-heading clearfix"}, 
                    React.createElement("b", {className: "panel-title pull-left"}, "Standard Collection")
                  ), 
                    	React.createElement("div", {className: "panel-body"}, 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon1"}, "Oscillation range"), 
                          React.createElement("input", {type: "number", id: "osc_range", onKeyPress: this.isNumberKey, value: this.state['osc_range']['value']})
                        ), 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon2"}, "Oscillation start"), 
                          React.createElement("input", {type: "number", id: "osc_start", onKeyPress: this.isNumberKey, value: this.state['osc_start']['value']}), 
                          React.createElement("input", {type: "checkbox", name: "activate", value: "active"})
                        ), 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon3"}, "Exposure time"), 
                          React.createElement("input", {type: "number", id: "exp_time", onKeyPress: this.isNumberKey, value: this.state['exp_time']['value']})
                        ), 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon4"}, "Energy"), 
                          React.createElement("input", {type: "number", id: "energy", onKeyPress: this.isNumberKey, value: this.state['energy']['default_value']})
                        ), 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon5"}, "Resolution"), 
                          React.createElement("input", {type: "number", id: "resolution", onKeyPress: this.isNumberKey, value: this.state['resolution']['value']})
                        ), 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon6"}, "Transmission"), 
                          React.createElement("input", {type: "number", id: "transmission", onKeyPress: this.isNumberKey, value: this.state['transmission']['value']})
                        ), 
                        React.createElement("div", {className: "input-group"}, 
                          React.createElement("span", {className: "input-group-addon", id: "basic-addon7"}, "Number of images"), 
                          React.createElement("input", {type: "number", id: "num_images", onKeyPress: this.isNumberKey, value: this.state['num_images']['value']})
                        ), 
                        React.createElement("button", {onClick: this.addCollection}, "Add to queue")
                 	)
                )
    }
});

React.render(React.createElement(StandardCollection, null), document.getElementById('standardcollection'));
