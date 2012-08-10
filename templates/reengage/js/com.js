"use strict";
/*
 * Willet's "ReEngage"
 * Copyright Willet Inc, 2012
 */

var client = {},    // {props}
  //apps = {},      // [{props}, {...}]; clients own apps
  //products = {},  // [{props}, {...}]; clients own products
  //queues = {},    // [{props}, {...}]; apps own queues
  //posts = {},     // [{props}, {...}]; queues own posts

    jsonTemplate = {
        // whenever a ajax request is sent, this is used as defaults.
        'dataType': 'json',
        'type': 'GET',
        'cache': false,
        'headers': {
            'x-requested-with': 'XMLHttpRequest'
        },
        'beforeSend': function (jqXHR, settings) {
            var ajax_loader = $('#ajax_loader');
            if (ajax_loader.length) {
                ajax_loader.show();
            }
        },
        'error': function (jqXHR, textStatus, errorThrown) {
            alertDialog(
                'Oops :(',
                'Could not talk to server. Please try again later!' +
                '<br /><br />' +
                'message: ' + textStatus
            );
        }
    };

var ajaxRequest = function (url, data, sideEffect, callback) {
    // execute a generic AJAX request.
    // sideEffect runs if request succeeds.
    // callback runs after sideEffect, and is optional.
    $.ajax($.extend({}, jsonTemplate, {
        'url': url,
        'data': data,
        'success': function (data) {
            sideEffect(data);  // do things with that data
            callback && callback();  // continue doing whatever
        }
    }));
};

var loadClient = function (client_uuid, callback) {
    // overwrites existing client, apps, queues, and posts objects.
    // returns nothing.
    ajaxRequest(
        '{% url ClientJSONDynamicLoader %}',
        {'client_uuid': client_uuid || '{{ client.uuid }}'},
        function (data) {
            client = {
                'uuid': data.uuid,
                'name': data.name,
                'domain': data.domain
                // @later 'apps': ...
            };
            loadApps(client);
        },
        callback
    );
};

var loadApps = function (client, callback) {
    // overwrites existing apps, queues, and posts objects.
    // returns nothing.
    ajaxRequest(
        '{% url AppJSONDynamicLoader %}',
        {
            'client_uuid': client.uuid,
            'class': 'ReEngage'
        },
        function (response) {
            var data = response.apps || [];  // key

            var apps = [];  // reset
            for (var i = 0; i < data.length; i++) {
                var app = {
                    'uuid': data[i].uuid,
                    'name': data[i].name,  // e.g. ReEngageShopify
                    'client': client,
                    'queue': {
                        'uuid': data[i].queue  // MVP single queue
                    },
                    'queues': [],  // you can choose to load it
                };
                apps.push(app);
                for (var i2 = 0; i2 < app.queues.length; ++i2) {
                    // load each queue now
                    loadQueues(app, app.queues[i2]);
                }
            }
            loadQueues(app, app.queue);
            client.apps = apps;
        },
        callback
    );
};

// @unused in MVP
var loadQueues = function (app, queue, callback) {
    // returns nothing.
    ajaxRequest(
        '{% url ReEngageQueueJSONHandler %}',
        {
            'app_uuid': (app && app.uuid) || '', // not used (one-app-one-queue MVP)
            'queue_uuid': (queue && queue.uuid) || '' // not used (one-app-one-queue MVP)
        },
        function (response) {
            // normally returns an array, but not yet
            var data = [response.queues || {}];  // data is a list of queues

            var queues = [];  // reset
            for (var i = 0; i < data.length; i++) {
                var queue = {
                    // data[i] is a queue
                    'uuid': data[i].uuid,
                    'app': app,  // "owner" in DB
                    'activePosts': data[i].activePosts,  // "queued" in DB
                    'expiredPosts': data[i].expiredPosts  // "expired" in DB
                };
                queues.push(queue);
            }
            app.queues = queues;
            updateQueueUI($(".post.selected").data("uuid"));
        },
        callback
    );
};

var loadPosts = function (queue, callback) {
    // returns nothing.
    ajaxRequest(
        '{% url ReEngageQueueJSONHandler %}',
        {'queue_uuid': queue.uuid},
        function (response) {
            var data = response.posts || [];  // key

            var posts = [];  // reset
            queue.activePosts = []; // reset references
            queue.expiredPosts = []; // reset references

            for (var i = 0; i < data.length; i++) {
                var post = {
                    'uuid': data[i].uuid,
                    'network': data[i].network,
                    'title': data[i].title || '',  // the name of the post
                    'content': data[i].content,  // the body text
                    'queue': queue
                };
                posts.push(post);
                if (data[i].expired) {
                    queue.expiredPosts.push(post);  // add posts
                } else {
                    queue.activePosts.push(post);
                }
            }
            updateQueueUI();
        },
        callback
    );
};

var createPost = function (title, content, first, uuid) {
    // creates a post on the server. reloads the queue.
    $.ajax({
        'url': '{% url ReEngageQueueJSONHandler %}',
        'type': "POST",
        'dataType': 'json',
        'data': {
            'title': title,
            'content': content,
            'method': (first? 'prepend' : 'append')
        },
        'cache': false,
        'success': function (data) {
            // alertDialog("", "Post created on server");
            var post = data.post;
            loadQueues(client.apps[0], '', function () {
                updateQueueUI(post.uuid);
                updatePostUI();
            });
            // updateQueueUI(post.uuid);
        }
    });
};

var updatePost = function (uuid, title, content) {
    // updates a post on the server. reloads the queue.
    var url = '{% url ReEngagePostJSONHandler "__REPLACE__" %}'
              .replace(/__REPLACE__/g, uuid);
    $.ajax($.extend({}, jsonTemplate, {
        'url': url,
        'type': 'PUT',
        'dataType': 'html',
        'data': {
            'title': title,
            'content': content
        },
        'cache': false,
        'success': function () {
            // alertDialog("Saved!", "Post saved!");

            // show the saved indicator for 2 seconds, then hide it
            $('#postSaveIndicator').show();
            setTimeout(function() {
                $('#postSaveIndicator').fadeOut('slow');
            }, 2000);

            loadQueues(client.apps[0]);
            updateQueueUI(uuid);
        }
    }));
};

var deletePost = function (uuid) {
    // deletes a post from the server. reloads the queue.
    var url = '{% url ReEngagePostJSONHandler "__REPLACE__" %}'
              .replace(/__REPLACE__/g, uuid);

    var prevPostUUID = $('#' + uuid).prev().data('uuid');
    $.ajax($.extend({}, jsonTemplate, {
        'url': url,
        'type': "DELETE",
        'dataType': 'json',
        'data': {},
        'success': function () {
            loadQueues(client.apps[0]);
            updateQueueUI(prevPostUUID);
            updatePostUI();
        }
    }));
};