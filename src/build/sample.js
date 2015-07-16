/** @jsx React.DOM */

var Search = React.createClass({displayName: "Search",
     render: function() {
         return React.createElement("div", {className: "search input-group", role: "search"}, 
                  React.createElement("input", {type: "search", className: "form-control", placeholder: "Search"}), 
                  React.createElement("span", {className: "input-group-btn"}, 
                    React.createElement("button", {className: "btn btn-default", type: "button"}, " ", 
                      React.createElement("span", {className: "glyphicon glyphicon-search"}), 
                      React.createElement("span", {className: "sr-only"}, "Search")
                    )
                  )
                )
    }
});

var SampleList = React.createClass({displayName: "SampleList",
     getInitialState: function() {
       return { "authorized_samples": [] }
     },

     check_sc: function() {
       this.setState({ "authorized_samples": [444182,444185] });
     },

     render: function() {
        var id = 0;
        var samples = this.props.samples.map(function(sample) {
             id += 1;
             var can_mount = (this.state.authorized_samples.indexOf(sample.sampleId) >= 0);
             return React.createElement(Sample, {sample: sample, key: id, can_mount: can_mount});
        }.bind(this));
        return React.createElement("div", null, 
                 React.createElement(Search, null), 
                 React.createElement("button", {type: "button", className: "btn btn-primary btn-block top7", onClick: this.check_sc}, 
                   React.createElement("span", {className: "glyphicon glyphicon-refresh"}), " Check sample changer"
                 ), 
                 React.createElement("div", {className: "panel-group top5"}, samples)
               )
     },
});

var Sample = React.createClass({displayName: "Sample",
     add_mount_task: function() {
       window.app_dispatcher.trigger("queue:new_item", { "kind":"sample", "text": "Mount "+this.props.sample.sampleName, fields:{} });
       //everytime a new sample is loaded into the queue its name is sent to the server
       $.ajax({
       //error: function(XMLHttpRequest, textStatus, errorThrown) { alert(textStatus) },
       url: 'sample_field_update',
       type: 'POST',
       data: { "Type":"Sample", "Name":this.props.sample.sampleName },
       dataType: "json" });  
     },

     render: function() {
       var idref = "sample"+this.props.key;
       var idhref = "#"+idref;
       var fields = [];
       var fieldno = 0;
       var hiddenfields = ['sampleId', 'sampleName' ];

       for (field in this.props.sample) { 
           if (hiddenfields.indexOf(field) >= 0) continue;
           var value = this.props.sample[field];
           fields.push( React.createElement(EditableField, {key: fieldno, sampleid: this.props.sample.sampleId, name: field, value: value}) );
           fieldno += 1;
       }
       
       var mount_button = "";
       if (this.props.can_mount) {
         mount_button = React.createElement("div", {className: "btn-group pull-right"}, 
                          React.createElement("a", {href: "#", className: "btn btn-success btn-xs", onClick: this.add_mount_task}, "Mount")
                        )
       } 

       return React.createElement("div", {className: "panel panel-default"}, 
                React.createElement("div", {className: "panel-heading clearfix"}, 
                  React.createElement("b", {className: "panel-title pull-left"}, 
                    React.createElement("a", {"data-toggle": "collapse", "data-parent": "#accordion", href: idhref}, 
                     this.props.sample.sampleName
                    )
                  ), 
                   mount_button 
               ), 
               React.createElement("div", {id: idref, className: "panel-collapse collapse out"}, 
                 React.createElement("div", {className: "panel-body"}, 
                   fields
                 )
               )
             )
     },

});

var EditableField = React.createClass({displayName: "EditableField",
	
   componentDidMount: function() {
      $(this.refs.editable.getDOMNode()).editable();
   }, 

   render: function() {
       return React.createElement("p", null, this.props.name, ": ", React.createElement("a", {href: "#", ref: "editable", "data-name": this.props.name, "data-pk": this.props.sampleid, "data-url": "/sample_field_update", "data-type": "text", "data-title": "Edit value"}, this.props.value))
   } 
})

React.render(React.createElement(SampleList, null), document.getElementById('SampleTreeGoesHere'));
