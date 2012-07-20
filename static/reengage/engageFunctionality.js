"use strict";
/*
 * Willet's "Should I Buy This"
 * Copyright Willet Inc, 2012
 *
 */

var postQueue = function () {
    //The queue of posts to be made
    return $('.post');
};

var randomUUID = function () {
    return parseInt(Math.random() * 100000000);
};

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
        'typeOfContent': 'type1',
        'contentLink': 'contentLink'
    };

    /* TODO: ajax, and if succeeds, ... */

    var postObj = $('<div />', {
        'class': 'post',
        'id': params.uuid,
    });
    postObj  // put the thing on the page.
        .data({
            'uuid': params.uuid,
            'title': params.title,
            'content': params.content,
            'typeOfContent': params.typeOfContent,
            'contentLink': params.contentLink
        })
        .click(function () {
            clickPost(params.uuid);
        })
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
            'class': 'postDelete postDeleteImg'
        }));

    postObj[(first? 'prependTo': 'appendTo')]('#replaceHiddenPost');
    updateQueueUI();

    return params.uuid;
};

var updateQueueUI = function (selectedPostUUID) {
    // Outputs post titles and dates in replaceWithPosts, aka main box area

    //If no posts in queue, suggest making a new post, else write out the posts in the queue
    if ($('.post').length > 0) {
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

var removePost = function (uuid) {
    // removes a post from the UI. TODO: ajax
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
    console.log('clicked clickPost');

    var post = $("#" + uuid);

    var content = post.data('content');
    var uuid = post.data('uuid');

    updateQueueUI(uuid);

    //If first post in queue, replace all contents on right
    if (postQueue().length === 1) {
        $("#replaceTextWithPostContent").hide();
        $("#postContentContainer").show();
        $("#editTitle").show();
    } // otherwise...?

    //Actions to do regardless of whether post is first in queue
    $('#selectedTitleContent').text(post.data('title'));
    $('#postContent').val(content);
    $('#postSave').eq(0).data('uuid', uuid);
};

//------jQuery Dialogs------

var alertDialog = function (alertTitle, content) {
    var $dialog = $("<div></div>")
        .html(content)
        .dialog({
            autoOpen: false,
            title: alertTitle,
            'modal': true,
            buttons: {
                "Ok": function () {
                    $(this).dialog("destroy");
                }
            }
        });

    $dialog.dialog('open');
    return false;
};

var confirmDialog = function (confirmTitle, content, ifOk) {
    var $dialog = $("<div></div>")
        .html(content)
        .dialog({
            autoOpen: false,
            title: confirmTitle,
            'modal': true,
            buttons: {
                "Cancel": function () {
                    $(this).dialog("destroy");
                },
                "Ok": function () {
                    $(this).dialog("destroy");
                    ifOk();
                }
            }
        });

    $dialog.dialog('open');
};

var newPostConfirm = function () {
    $("#newPostDialog").dialog({
        'modal': true,
        buttons: {
            "Cancel": function () {
                $(this).dialog("destroy");
                $("#newPostTitle").val("");
            },
            "Ok": function () {
                var title = $("#newPostTitle").val();
                var first = ($("input[name=first]:checked").val() === "first");

                //Make sure a title was given to the new post
                if (!title.length) {
                    $(this).dialog("destroy");
                    confirmDialog("Warning!", "Give your post a title!", newPostConfirm);
                }
                else {
                    //Create post, make lightbox disappear, update queue
                    var uuid = createNewPost({
                        'uuid': randomUUID(),
                        'title': title,
                        'content': 'Example content',
                        'typeOfContent': 'type1',  //This is the default value - change later
                        'contentLink': 'contentLink'
                    }, first);
                    $(this).dialog("destroy");

                    updateQueueUI();

                    clickPost(uuid);
                    $("#newPostTitle").val("");
                }
            }
        }
    });
};

var newTitlePromptDialog = function () {
    // invoked when "(edit)" is clicked after selecting a post.
    var $emptyWarning = $("<div>You can't give a post an empty title! Try again.</div>")
        .dialog({
            title: "Warning!",
            'modal': true,
            buttons: {
                "Ok": function () {
                    $(this).dialog("close");
                    $editDialog.dialog("open");
                }
            }
        });
    $emptyWarning.dialog("close");

    var $editDialog = $("#editTitleDialog").dialog({
        'modal': true,
        buttons: {
            "Cancel": function () {
                $(this).dialog("destroy");
                $("#editTitleInput").val("");
            },
            "Ok": function () {
                var title = $("#editTitleInput").val();
                if (!title) {
                    $(this).dialog("close");
                    $emptyWarning.dialog("open");
                }
                else {
                    var uuid = $('.post.selected').data('uuid');
                    var post = $('#' + uuid);
                    post.data('title', title);

                    // TODO: ajax

                    $("#selectedTitleContent").html(title);
                    $(".post.selected .postTitle").html(title);

                    $(this).dialog("close");
                    $("#editTitleInput").val("");
                }
            }
        }
    });
    $editDialog.dialog("open");

};






















//------Functions attached to html elements-----

$(document).ready(function () {

    //For features whose links are visible, but whose functionalities aren't part of the MVP
    $(".comingSoon").on("click", function () {
        var title = "Coming soon!";
        var content = "This feature will soon be available. Thank you for your patience!";

        alertDialog(title, content);
    });

    //When 'New Post' is clicked
    $("#newPost").on("click", function () {
        //make sure that currently selected post was given content, that is, if queue.length > 0
        //also make sure changes from current post were saved

        var posts = $('.post');

        if (!posts.length) {
            $("#newTitleWarning").hide();
            newPostConfirm();
        } else {
            var activePost = $(".post.selected");

            if (activePost.data('content') !== $("#postContent").val()) {
                var ifOk = function () {
                    $("#postContent").val(activePost.data('content'));
                    if (!$("#postContent").val()) {
                        alertDialog("Warning!", "Give your current post some content first!");
                    }
                    else {
                        newPostConfirm();
                    }
                };
                confirmDialog("Confirm", "Unsaved changes. Discard changes?", ifOk);
            } else if (!activePost.data('content')) {
                alertDialog("Warning!", "Give your current post some content first!");
            } else {
                newPostConfirm();
            }
        }
    });

    //When 'cancel' in 'new post' dialog is clicked
     $("#newPostCancel").on("click", function () {
        $("#light").hide();
        $("#newPostTitle").val("");
    });

    //Pressing 'enter' in New Post textbox == clicking 'ok' in New Post textbox
    $("#newPostTitle").keyup(function (event) {
        if (event.keyCode === 13) {
            $("#newPostOk").click();
        }
    });

    //When a post is clicked, clickPost() populates post content to right, and selects the clicked post
    //First checks to make sure you've saved any changes to the right
    $(document).on("click", ".post", function () {
        //newuuid is uuid of post just clicked, olduuid is uuid of post previously selected
        var newPost = $(this);
        var oldPost = $(".post.selected");
        var posts = $(".post");

        if (posts.length > 1) {
            var content = $("#postContent").val();
            console.log(content);
            if (!oldPost.data('content') && !content) {
                alertDialog("Warning!", "Give your current post some content first!");
            } else if (oldPost.data('content') != content) {
                confirmDialog(
                    "Confirm", "You have unsaved changes. Discard changes?",
                    function () {
                        $("#postContent").val(oldPost.content);
                        if (oldPost.content !== "") {
                            clickPost(newPost.data('uuid'));
                        } else {
                            alertDialog("Warning!", "Give your current post some content first!");
                        }
                    }
                );
            } else {
                clickPost(newPost.data('uuid'));
            }
        } else {
            clickPost(newPost.data('uuid'));
        }
    });

    //Delete post
    $(document).on("click", ".postDelete", function () {
        var uuid = $(this).data("uuid");
        confirmDialog(
            "Confirm", "Are you sure you want to delete this post?",
            function () {
                $('#' + uuid).remove();
                updateQueueUI();
            }
        );
    });

    //When you click 'save', contents are saved to the post
    $(document).on("click", "#postSave", function () {
        if (!$("#postContent").val()) {
            alertDialog("Warning!", "Give your current post some content first!");
        } else {
            var uuid = $('.post.selected').data("uuid");
            console.log('got postSave uuid of ' + uuid);
            $('#' + uuid).data({
                'typeOfContent': 'type1',
                'content': $("#postContent").val()
            });
            alertDialog("", "Saved!");
        }
    });

    //When you click 'edit' beside the title, prompts you to change the post title
    $(document).on("click", "#editTitle", function () {
        newTitlePromptDialog();
    });
});