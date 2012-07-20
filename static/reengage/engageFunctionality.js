var postQueue = function () {
    //The queue of posts to be made
    return $('.post');
};
var postuuid = 0; //Each post has a unique uuid - hack for now, generate actual ids later

// typedef struct {
//     str uuid;
//     str title;  // name of the post
//     str content;  // content of the post
//     str typeOfContent;  // some type (source unknown)
//     str contentLink;  // link to the post (use unknown)
// } Post;

var createNewPost = function (params, first) {
    // creates a new post on the UI. also sends a request to create a new post on the server.
    // if first, post is put on top of the queue.
    params = params || {
        'uuid': '123',
        'title': 'Example title',
        'content': 'Example content',
        'typeOfContent': 'typeOfContent',
        'contentLink': 'contentLink'
    };
    /*var content = "";
    var typeOfContent = "";
    var contentLink = "";

    var newPost = new Post(title, content, typeOfContent, contentLink, postuuid++);
    if (first) {
        postQueue.splice(0,0,newPost);
    }
    else if (!first) {
        postQueue.push(newPost);
    }*/

    /* TODO: ajax, and if succeeds, ... */

    var postObj = $('<div />', {
        'class': 'post',
        'id': params.uuid,
    });
    postObj  // put the thing on the page.
        .data({
            'title': params.title,
            'content': params.content,
            'typeOfContent': params.typeOfContent,
            'contentLink': params.contentLink
        })
        .click(clickPost)
        .append($('<div />', {
            'class': 'postDate',
            'html': '2012-04-31' // getDate(i)
        }))
        .append($('<div />', {
            'class': 'postTitle',
            'html': params.title
        }))
        .append($('<div />', {
            'id': 'delete' + params.uuid,
            'class': 'postDelete postDeleteImg',
            'html': params.title,
            'css': {
                'height': '15px'
            }
        }));

    postObj[(first? 'prependTo': 'appendTo')]('#replaceHiddenPost');
    updateQueueUI();
};

var updateQueueUI = function (selectedPostUUID) { //Outputs post titles and dates in replaceWithPosts, aka main box area
    var out = "";

    //If no posts in queue, suggest making a new post, else write out the posts in the queue
    if ($('.post').length > 0) {
//         for (var i = 0; i < postQueue.length; i++) {
//             var post = postQueue[i];
//             out += "    <div class='post' id='" + post.uuid + "'>";
//             out += "        <div class='postDate'>" + getDate(i) + "</div>";
//             out += "        <div class='postTitle'>" + post.title + "</div>";
//             out += "        <div class='postDelete'><a href='#' class='postDeleteImg' id='delete" + post.uuid + "' height='15px'></a></div>";
//             out += "    </div>";
//         }
//         //$("#" + post.uuid + " .postDelete").data("uuid", post.uuid);
//         $("#replaceTextWithPosts").hide();
//         $("#replaceHiddenPost").html(out);
//         $("#replaceHiddenPost").show();
//
//         for (var i = 0; i < postQueue.length; i++) {
//             var uuid = postQueue[i].uuid;
//             $("#" + uuid + " .postDelete").data("uuid", uuid);
//         }
        $("#replaceHiddenPost").show();
        $("#replaceTextWithPosts").hide();
    }
    else {
        $("#replaceHiddenPost").hide();
        $("#replaceTextWithPosts").show();
    }

    // reset selection (if the selected post was deleted)
    $('.post').removeClass('selected');
    if (selectedPostUUID) {
        $('#' + selectedPostUUID).addClass('selected');
    } else {
        $('.post').eq(0).addClass('selected');
    }
};

var removePost = function (uuid) { //Looks through queue for post of this uuid and deletes it
//     var ifOk = function() {
//         var x = 0;
//         for (var i = 0; i < postQueue.length; i++) {
//             if (postQueue[i].uuid === uuid) {
//                 postQueue.splice(i, 1);
//
//                 if (postQueue.length > 0) { //If queue isn't empty
//                     if (postQueue.length === 1) { //If queue only has one post left in it
//                         x = postQueue[0].uuid;
//                     }
//                     else if (postQueue.length === i) { //If deleted post was last in queue
//                         x = postQueue[i-1].uuid;
//                     }
//                     else {
//                         x = postQueue[i].uuid;
//                     }
//                 }
//             }
//         }
//
//         updateQueueUI();
//
//         if (postQueue.length > 0) {
//             $("#" + x).addClass("selected");
//         }
//         else {
//             ("#selectedTitleContent").html("Post Title Here");
//         }
//     };

    confirmDialog(
        "Confirm",
        "Are you sure you want to delete this post?",
        function () {
            $('#' + uuid).remove();
            updateQueueUI();
        }
    );
};

// var clickPost = function (post) {
var clickPost = function (uuid) {
    var post = $(this) || $("#" + uuid);

    var content = post.data('content');
    var uuid = post.data('uuid');
    var typeOfContent = post.data('typeOfContent');

    updateQueueUI(uuid);

    //If first post in queue, replace all contents on right
    if (postQueue().length === 1) {
        $("#replaceTextWithPostContent").hide();
        $("#postContentContainer").show();
        $("#editTitle").show();

        $("#postKind option[value='type1']").attr("selected", "selected");
        $("#postContent").val(content);
    }
    //If not first in queue, only replace necessary values
    else {
        $("#postKind option[value='" + typeOfContent + "']").attr("selected", "selected");
        $("#postContent").val(content);
    }
    //Actions to do regardless of whether post is first in queue
    $("#postSave")
        .attr("title", uuid)
        .data('uuid', uuid);
    $("#selectedTitleContent").html(post.title);
};

//------jQuery Dialogs------

var alertDialog = function (alertTitle, content) {
    var $dialog = $("<div></div>")
        .html(content)
        .dialog({
            autoOpen: false,
            title: alertTitle,
            buttons: {
                "Ok": function() {
                    $(this).dialog("destroy");
                }
            }
        });

    $dialog.dialog('open');
    return false;
};

var confirmDialog = function(confirmTitle, content, ifOk) {
    var $dialog = $("<div></div>")
        .html(content)
        .dialog({
            autoOpen: false,
            title: confirmTitle,
            buttons: {
                "Cancel": function() {
                    $(this).dialog("destroy");
                },
                "Ok": function() {
                    $(this).dialog("destroy");
                    ifOk();
                }
            }
        });

    $dialog.dialog('open');
};

var newPostConfirm = function() {
    $("#newPostDialog").dialog({
        buttons: {
                "Cancel": function() {
                    $(this).dialog("destroy");
                    $("#newPostTitle").val("");
                },
                "Ok": function() {
                    var title = $("#newPostTitle").val();
                    var first = ($("input[name=first]:checked").val() === "first");

                    //Make sure a title was given to the new post
                    if (title.length === 0) {
                        $(this).dialog("destroy");
                        confirmDialog("Warning!", "Give your post a title!", newPostConfirm);
                    }
                    else {
                        //Create post, make lightbox disappear, update queue
                        createNewPost({
                            'uuid': parseInt(Math.random() * 100000000),
                            'title': title,
                            'content': 'Example content',
                            'typeOfContent': 'typeOfContent',
                            'contentLink': 'contentLink'
                        }, first);
                        $(this).dialog("destroy");

                        updateQueueUI();

                        //Write queue, select newly created post
                        if (first) {
                            var uuid = postQueue()[0].uuid;
                            var post = postQueue()[0];
                        } else {
                            var uuid = postQueue()[postQueue().length - 1].uuid;
                            var post = postQueue()[postQueue().length - 1];
                        }

                        post.typeOfContent = "type1" //This is the default value - change later

                        clickPost($(post).data('uuid'));
                        $("#newPostTitle").val("");
                    }
                }
        }
    });
};

var newTitlePromptDialog = function() {
    var $emptyWarning = $("<div></div>")
        .html("You can't give a post an empty title! Try again.")
        .dialog({
            title: "Warning!",
            buttons: {
                "Ok": function() {
                    $(this).dialog("close");
                    $editDialog.dialog("open");
                }
            }
        });
    $emptyWarning.dialog("close");

    var $editDialog = $("#editTitleDialog").dialog({
        buttons: {
            "Cancel": function() {
                $(this).dialog("destroy");
                $("#editTitleInput").val("");
            },
            "Ok": function() {
                var title = $("#editTitleInput").val();
                if (title.length === 0) {
                    $(this).dialog("close");
                    $emptyWarning.dialog("open");
                }
                else {
                    var id = $(".post.selected").attr('id');
                    for (var i = 0; i < postQueue().length; i++) {
                        if (postQueue()[i].uuid == id) {
                            var post = postQueue()[i];
                        }
                    }
                    post.title = title;
                    $("#selectedTitleContent").html(post.title);
                    $(".post.selected .postTitle").html(post.title);
                    $(this).dialog("close");
                    $("#editTitleInput").val("");
                }
            }
        }
    });
    $editDialog.dialog("open");

};






















//------Functions attached to html elements-----

$(document).ready(function() {

    //For features whose links are visible, but whose functionalities aren't part of the MVP
    $(".comingSoon").on("click", function() {
        var title = "Coming soon!";
        var content = "This feature will soon be available. Thank you for your patience!";

        alertDialog(title, content);
    });

    //When 'New Post' is clicked
    $("#newPost").on("click", function() {
        //make sure that currently selected post was given content, that is, if queue.length > 0
        //also make sure changes from current post were saved

        if (postQueue().length === 0) {
            $("#newTitleWarning").hide();
            newPostConfirm();
        }
        else {
            var uuid = $(".post.selected").attr('id');
            for (var i = 0; i < postQueue().length; i++) {
                if (postQueue()[i].uuid == uuid) {
                    var post = postQueue()[i];
                }
            }

            if (post.content !== $("#postContent").val() ||
                post.typeOfContent !== $("#postKind option:selected").val()) {
                var ifOk = function() {
                    $("#postContent").val(post.content);
                    if ($("#postContent").val() === "") {
                        alertDialog("Warning!", "Give your current post some content first!");
                    }
                    else {
                        newPostConfirm();
                    }
                };
                confirmDialog("Confirm", "Unsaved changes. Discard changes?", ifOk);
            }
            else if (post.content === "") {
                alertDialog("Warning!", "Give your current post some content first!");
            }
            else {
                newPostConfirm();
            }
        }
    });

    //When 'cancel' in 'new post' dialog is clicked
     $("#newPostCancel").on("click", function() {
        $("#light").hide();
        $("#newPostTitle").val("");
    });

    //Pressing 'enter' in New Post textbox == clicking 'ok' in New Post textbox
    $("#newPostTitle").keyup(function(event) {
        if (event.keyCode === 13) {
            $("#newPostOk").click();
        }
    });

    //When a post is clicked, clickPost() populates post content to right, and selects the clicked post
    //First checks to make sure you've saved any changes to the right
    $(document).on("click", ".post", function() {
        //newuuid is uuid of post just clicked, olduuid is uuid of post previously selected
        var newuuid = $(this).attr('id');
        var olduuid = $(".post.selected").attr('id');

        for (var i = 0; i < postQueue().length; i++) {
            if (olduuid == postQueue()[i].uuid) {
                var oldPost = postQueue()[i];
            }
        }

        for (var i = 0; i < postQueue().length; i++) {
            if (newuuid == postQueue()[i].uuid) {
                var newPost = postQueue()[i];

                if (postQueue().length > 1) {
                    var typeOfContent = $("#postKind option:selected").val();
                    var content = $("#postContent").val();
                    if (oldPost.content === "" && content === "") {
                        alertDialog("Warning!", "Give your current post some content first!");
                    }
                    else if ((oldPost.typeOfContent != typeOfContent) || (oldPost.content != content)) {
                        var ifOk = function() {
                            $("#postContent").val(oldPost.content);
                            if (oldPost.content !== "") {
                                clickPost($(newPost).data('uuid'));
                            }
                            else {
                                alertDialog("Warning!", "Give your current post some content first!");
                            }
                        };
                        confirmDialog("Confirm", "You have unsaved changes. Discard changes?", ifOk);
                    }
                    else clickPost($(newPost).data('uuid'));
                    }
                else clickPost($(newPost).data('uuid'));
            }
        }
    });

    //Delete post
    $(document).on("click", ".postDelete", function() {
            var uuid = $(this).data("uuid");
            var yes = confirmDialog("Confirm", "Are you sure you want to delete this post?");

            var ifOk = function() {
                var x = 0;
                for (var i = 0; i < postQueue().length; i++) {
                    if (uuid == postQueue()[i].uuid) {
                        postQueue().splice(i, 1);

                        if (postQueue().length > 0) { //If queue isn't empty
                            if (postQueue().length === 1) { //If queue only has one post left in it
                                x = 0;
                            }
                            else if (postQueue().length === i) { //If deleted post was last in queue
                                x = i - 1;
                            }
                            else {
                                x = i;
                            }
                        }
                    }
                }

                updateQueueUI();

                //If there are posts remaining, select post identified by var x in above looping; otherwise remove post content form
                if (postQueue().length > 0) {
                    clickPost($(postQueue()[x]).data('uuid'));
                }
                else {
                    $("#replaceTextWithPostContent").show();
                    $("#postContentContainer").hide();
                    $("#editTitle").hide();
                    $("#selectedTitleContent").html("Post title here");
                }
            }

            confirmDialog("Confirm", "Are you sure you want to delete this post?", ifOk);
    });

    //When you click 'save', contents are saved to the post
    $(document).on("click", "#postSave", function () {
        if (!$("#postContent").val()) {
            alertDialog("Warning!", "Give your current post some content first!");
        } else {
            var uuid = $(this).data("uuid");
            console.log('got postSave uuid of ' + uuid);
            $('#' + uuid).data({
                'typeOfContent': $("#postKind option:selected").val(),
                'content': $("#postContent").val()
            });
            alertDialog("Saved!", "");
        }
    });

    //When you click 'edit' beside the title, prompts you to change the post title
    $(document).on("click", "#editTitle", function() {
        newTitlePromptDialog();
    });

    $(document).on("mouseenter", ".postDelete", function() {
        var uuid = $(this).data("uuid");
        $("#delete" + uuid).css("background-position", "0 0");
    });

    $(document).on("mouseleave", ".postDelete", function() {
        var uuid = $(this).data("uuid");
        $("#delete" + uuid).css("background-position", "bottom");
    });

});