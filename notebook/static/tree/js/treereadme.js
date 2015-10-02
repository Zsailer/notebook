// Zach's extension

define([
    'jquery',
    'components/marked/lib/marked',
    'base/js/utils'
], function($, marked, utils){

    names = ["README.md", "ReadMe.md", "readme.md", "Readme.md"]

    var ReadMe = function(selector, options){
        var that = this;

        this.contents = options.contents;
        this.selector = selector;
        this.base_url = options.base_url;
        this.notebook_path = options.notebook_path || utils.get_body_data("notebookPath");
        //console.log(this.base_url);
        this.file_path = this.notebook_path + "/README.md"
        this.load();
    }

    ReadMe.prototype.file_list = function(list, err){

        var content = list.content;

        // Iterate through files to find README
        for (var i=0; i < content.length ;  i++) {
            var file_index = null;
            if (content[i].name == "README.md") {
                if (content[i].type == "file") {
                    file_index = i
                };
            };
        }
        console.log(file_index);
    }


    ReadMe.prototype.load = function() {
        /** load the README file */
        var that = this;
        return this.contents.get(this.file_path, {type: 'file', format: 'text'})
            .then(function(model) {
                that.text_content = model.content;
                var marked_down = marked(that.text_content);
                var panel_body = $("<div>").addClass("panel-body").append(marked_down);
                var panel = $("<div>").addClass("panel panel-default").append(panel_body);
                console.log(marked_down)
                $("#ipython-main-app").append(panel)
            })
            .catch(
                function(error) {
                    console.warn('Error loading: ', error);
                }
            );
    }


    return {"ReadMe": ReadMe};
})
