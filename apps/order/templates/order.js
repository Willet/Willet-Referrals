/** Willet's "Order" Shopify App
  * Copyright 2011, Willet, Inc.
  * Tracks when orders occur
 **/

(function(window){
    var document = window.document;
    var tell_server = function () {
        var iframe = document.createElement( 'iframe' );

        iframe.style.display = 'none';
        iframe.src = "{{SECURE_URL}}{% url OrderIframeNotification %}?" +
                     "&user_uuid={{user.uuid}}" +
                     "&client_uuid={{client.uuid}}" +
                     "&url=" + window.location.href;
        document.body.appendChild( iframe );
    };
    var run = function() {
        /**
        * Insert style and get the ball rolling
        */
        try {
            var page = window.location.href;
            if ( page.indexOf( 'https://checkout.shopify.com/orders' ) != -1 ) {
                tell_server();
            }
        } catch (e) {
            var error = e;
            var message = '';
            var script = 'order.js';

            if (e.name && e.message) {
                error = e.name;
                message = e.message;
            }

            var el = document.createElement('img');
            var _body = document.getElementsByTagName('body')[0];
            el.setAttribute('src', 'http://rf.rs/admin/ithinkiateacookie?script=' + script + '&error=' + error + '&st=' + message);
            _body.appendChild(el);
        }
    };

    /**
     * This is jQuery's bindReady, modified to work for our scripts
     * This should ensure that the DOM is ready before we insert
     */

    // Mozilla, Opera and webkit nightlies currently support this event
    if (document.readyState && document.readyState === "complete") {
        run();
    } else if (document.addEventListener) {
        // Use the handy event callback
        document.addEventListener("DOMContentLoaded", function(){
            document.removeEventListener("DOMContentLoaded", arguments.callee, false );
            run();
        }, false);
    } else if (document.attachEvent) {
        // ensure firing before onload,
        // maybe late but safe also for iframes
        document.attachEvent("onreadystatechange", function(){
            if (document.readyState === "complete") {
                document.detachEvent( "onreadystatechange", arguments.callee );
                run();
            }
        });

        // If IE and not an iframe
        // continually check to see if the document is ready
        if ( document.documentElement.doScroll && window == window.top ) (function(){
            try {
                // If IE is used, use the trick by Diego Perini
                // http://javascript.nwbox.com/IEContentLoaded/
                document.documentElement.doScroll("left");
            } catch( error ) {
                setTimeout( arguments.callee, 0 );
                return;
            }
            // and execute any waiting functions
            run();
        })();
    }
}(window));

