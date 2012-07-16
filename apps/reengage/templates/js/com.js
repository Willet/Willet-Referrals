"use strict";
/*
 * Willet's "ReEngage"
 * Copyright Willet Inc, 2012
 */

var client = {},    // {props}
    apps = {},      // [{props}, {...}]; clients own apps
    products = {},  // [{props}, {...}]; clients own products
    queues = {},    // [{props}, {...}]; apps own queues
    posts = {},     // [{props}, {...}]; queues own posts

    jsonTemplate = {
        // whenever a ajax request is sent, this is used as defaults.
        'dataType': 'json',
        'type': 'GET',
        'headers': {
            'x-requested-with': 'XMLHttpRequest'
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
    // overwrites existing client object.
    // returns nothing.
    ajaxRequest(
        '{% url ClientJSONDynamicLoader %}',
        {'client_uuid': client_uuid || '{{ client.uuid }}'},
        function (data) {
            client = {
                'uuid': data.uuid,
                'name': data.name,
                'domain': data.domain,
                'apps': []  // you can choose to load it
            };
        },
        callback
    );
};

var loadApps = function (client, callback) {
    // overwrites existing apps object.
    // returns nothing.
    ajaxRequest(
        '{% url AppsJSONDynamicLoader %}',
        {'client_uuid': client.uuid},
        function (response) {
            var data = response.apps;  // key

            apps = [];  // reset
            client.apps = []; // reset references

            for (var i = 0; i < data.length; i++) {
                apps.push({
                    'uuid': response[i].uuid,
                    'name': response[i].name,  // e.g. ReEngageShopify
                    'client': client,
                    'queues': []  // you can choose to load it
                });
            }

            client.apps = apps;
        },
        callback
    );
};

var loadQueues = function (app, callback) {
    // overwrites existing queues object.
    // returns nothing.
    ajaxRequest(
        '{% url QueuesJSONDynamicLoader %}',
        {'app_uuid': app.uuid},
        function (response) {
            var data = response.queues;  // key

            queues = [];  // reset
            app.queues = []; // reset references

            for (var i = 0; i < data.length; i++) {
                queues.push({
                    'uuid': data[i].uuid,
                    'app': app,  // "owner" in DB
                    'activePosts': [],  // "queued" in DB
                    'expiredPosts': []  // "expired" in DB
                });
            }
        },
        callback
    );
};

var loadPosts = function (queue, callback) {
    // overwrites existing posts object.
    // returns nothing.
    ajaxRequest(
        '{% url PostsJSONDynamicLoader %}',
        {'queue_uuid': queue.uuid},
        function (response) {
            var data = response.posts;  // key

            posts = [];  // reset
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
        },
        callback
    );
};

var __main__ = function () {
    $(document).ready(function () {
        // ...
    });
};

// fire up Mr.AJAX
if (window.__name__ === '__main__') {
    loadClient('', function () {
        loadApps(client, function () {
            loadQueues(apps[0], function () {
                loadPosts(queues[0], __main__);
            })
        })
    });
}