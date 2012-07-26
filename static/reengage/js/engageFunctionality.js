"use strict";
/*
 * Willet's "ReEngage"
 * Copyright Willet Inc, 2012
 *
 */

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

var createPostElement = function (post, first) {
    // given a post object (from the server), render it.
    var postObj = $('<div />', {
        'class': 'post',
        'id': post.uuid,
    });
    postObj  // put the thing on the page.
        .data({
            'uuid': post.uuid,
            'title': post.title,
            'content': post.content,
            'typeOfContent': post.typeOfContent,
            'contentLink': post.contentLink
        })
        .click(function () {
            clickPost(post.uuid);
        })
        .append($('<div />', {
            'class': 'postDate',
            'html': '(scheduled)'
        }))
        .append($('<div />', {
            'class': 'postTitle',
            'html': post.title
        }))
        .append($('<div />', {
                'id': 'delete' + post.uuid,
                'class': 'postDelete postDeleteImg'
            }).click(function() {
                removePost(post.uuid);
            })
        );


    postObj[(first? 'prependTo': 'appendTo')]('#replaceHiddenPost');
};

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

    createPostElement(params, first);

    updateQueueUI(params.uuid);
    createPost(params.title, params.content, first);

    return params.uuid;
};

var updateQueueUI = function (selectedPostUUID) {
    // Outputs post titles and dates in replaceWithPosts, aka main box area

    var queueArea = $('#replaceHiddenPost'),
        emptyQueueArea = $('#replaceTextWithPosts'),
        serverPosts = client.apps[0].queues[0].activePosts;

    // reset the array of posts displayed.
    queueArea.empty();
    for (var i = 0; i < serverPosts.length; i++) {
        createPostElement(serverPosts[i], false);
    }

    //If no posts in queue, suggest making a new post, else write out the posts in the queue
    if ($('.post').length > 0) {
        queueArea.show();
        emptyQueueArea.hide();
    } else {
        queueArea.hide();
        emptyQueueArea.show();
    }

    // reset selection (if the selected post was deleted)
    $('.post').removeClass('selected');
    if (selectedPostUUID) {
        $('#' + selectedPostUUID).addClass('selected');
        // updatePostUI();
    } // else: select nothing
};

var updatePostUI = function () {
    // Change the right-hand side area with the appropriate UI:
    // either no post at all, or information about the selected post.

    //If no posts in queue, suggest making a new post, else write out the posts in the queue
    if ($('.post.selected').length > 0) {
        $("#replaceTextWithPostContent").hide();
        $("#postContentContainer").show();
        $("#editTitle").show();
    }
    else {
        $("#replaceTextWithPostContent").show();
        $("#postContentContainer").hide();
    }

    var post = $('.post.selected');
    if (post.length) {
        var uuid = post.data('uuid');
        //Actions to do regardless of whether post is first in queue
        $('#selectedTitleContent').html(post.data('title'));
        $('#postContent').val(post.data('content'));
        $('#postSave').eq(0).data('uuid', uuid);
    }
};

var removePost = function (uuid) {
    // removes a post from the UI.
    confirmDialog(
        "Confirm",
        "Are you sure you want to delete this post?",
        function () {
            deletePost(uuid);
            $('#' + uuid).remove();
            // updateQueueUI();
        }
    );
};

// var clickPost = function (post) {
var clickPost = function (uuid) {

    var post = $("#" + uuid);
    var uuid = post.data('uuid');

    updateQueueUI(uuid);  // "select it"
    updatePostUI();
};

//------jQuery Dialogs------

var alertDialog = function (alertTitle, content) {
    var $dialog = $("<div></div>")
        .html(content)
        .dialog({
            autoOpen: false,
            title: alertTitle,
            'modal': true,
            'width': 400,
            buttons: [
                {
                    text: "Ok",
                    click: function() {
                        $(this).dialog("destroy");
                    }
                }
            ]
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
            buttons: [
                {
                    text: "Cancel",
                    click: function() {
                        $(this).dialog("destroy");
                    }
                },
                {
                    text: "Ok",
                    className: "clickOnEnter",
                    click: function() {
                        $(this).dialog("destroy");
                        ifOk();
                    }
                }
            ]
        });

    $dialog.dialog('open');
};

var newPostConfirm = function () {
    $("#newPostDialog").dialog({
        'modal': true,
        buttons: [
            {
                text: "Cancel",
                click: function() {
                    $(this).dialog("destroy");
                    $("#newPostTitle").val("");
                }
            },
            {
                text: "Ok",
                className: "clickOnEnter",
                click: function () {
                    var title = $("#newPostTitle").val();
                    var first = ($("input[name=first]:checked").val() === "first");

                    //Make sure a title was given to the new post
                    if (!title.length) {
                        $(this).dialog("destroy");
                        confirmDialog("Warning!", "Give your post a title!", newPostConfirm);
                    } else {
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
        ]
    });
};

var newTitlePromptDialog = function () {
    // invoked when "(edit)" is clicked after selecting a post.
    var $emptyWarning = $("<div>Posts must have a title. Try again.</div>")
        .dialog({
            title: "Warning!",
            'modal': true,
            buttons: [
                {
                    text: "Ok",
                    click: function() {
                        $(this).dialog("close");
                        $editDialog.dialog("open");
                    }
                }
            ]
        });
    $emptyWarning.dialog("close");

    var $editDialog = $("#editTitleDialog").dialog({
        'modal': true,
        buttons: [
            {
                text: "Cancel",
                click: function() {
                    $(this).dialog("destroy");
                    $("#editTitleInput").val("");
                }
            },
            {
                text: "Ok",
                className: "clickOnEnter",
                click: function() {
                    var title = $("#editTitleInput").val();
                    if (!title) {
                        $(this).dialog("close");
                        $emptyWarning.dialog("open");
                    } else {
                        var uuid = $('.post.selected').data('uuid');
                        var post = $('#' + uuid);
                        post.data('title', title);

                        updatePost(uuid, title, '');

                        $("#selectedTitleContent").html(title);
                        $(".post.selected .postTitle").html(title);

                        $(this).dialog("close");
                        $("#editTitleInput").val("");
                    }
                }
            }
        ]
    });
    $editDialog.dialog("open");

};


//------Functions attached to html elements-----

$(document).ready(function () {
    $("#IEWarning").hide(); //Warning will only show up if scripts are blocked

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
            $("#newTitleWarning, #endOrBeginning").hide();
            newPostConfirm();
        } else {
            $("#endOrBeginning").show();
            var activePost = $(".post.selected");

            if (activePost.length &&
                activePost.data('content') !== $("#postContent").val()) {
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
            } else if (activePost.length &&
                      !activePost.data('content')) {
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
        var posts = $(".post");

        var newPost = $(this);
        var oldPost = $(".post.selected");
        var content = $("#postContent").val();

        if (!oldPost.data('content') && !content) { // if new post has no content
            alertDialog("Warning!", "Give your current post some content first!");
            return;
        }

        if (oldPost.data('content') != content) { // if content changed
            confirmDialog(
                "Confirm", "You have unsaved changes. Discard changes?",
                function () {
                    $("#postContent").val(oldPost.data('content'));
                    if (oldPost.data('content')) {
                        clickPost(newPost.data('uuid'));
                    } else {
                        alertDialog("Warning!", "Give your current post some content first!");
                    }
                }
            );
            return;
        }
        // updateQueueUI(newPost.data('uuid'));
        // clickPost(newPost.data('uuid'));
    });

    //When you click 'save', contents are saved to the post
    $(document).on("click", "#postSave", function () {
        if (!$("#postContent").val()) {
            alertDialog("Warning!", "Give your current post some content first!");
        } else {
            var uuid = $('.post.selected').data("uuid");
            $('#' + uuid).data({
                'typeOfContent': 'type1',
                'content': $("#postContent").val()
            });
            updatePost(uuid, '', $("#postContent").val());
        }
    });

    //When you click 'edit' beside the title, prompts you to change the post title
    $(document).on("click", "#editTitle", function () {
        newTitlePromptDialog();
    });

    $(".enableEnterPress").keyup(function(event) {
        if (event.keyCode === 13) {
            $(".clickOnEnter").click();
        }
    });


    // some hook thingy that is rumoured to trigger when any ajax completes
    var ajaxHookThingy = function () {
        var ajax_loader = $('#ajax_loader');
        if (ajax_loader.length) {
            ajax_loader.fadeOut('slow');
        }
    };
    // $(document).ajaxComplete(ajaxHookThingy);
    $(document).ajaxStop(ajaxHookThingy);

    // start the stuff
    loadClient();
    setInterval(function () {
        updateQueueUI($('.post.selected').data('uuid'));
    }, 5000);
});