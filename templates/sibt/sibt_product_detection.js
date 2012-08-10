(function(window){
    /**
     * Willet SIBT product detecion
     */
    var document = window.document;

    var run = function() {
        try {
            var purchase_cta = document.getElementById('{{ sibt_button_id }}');
            if (purchase_cta) {
                // get the hash
                var hash        = window.location.hash;
                var hash_search = '#code=';
                var hash_index  = hash.indexOf(hash_search);
                var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);

                // setup script
                var sibt_script = document.createElement('script');
                var head = document.getElementsByTagName('head')[0];
                sibt_script.type = 'text/javascript';
                sibt_script.src = "{{ URL }}{% url SIBTShopifyServeScript %}?" +
                    "willt_code=" + willt_code +
                    "&user_uuid={{ user.uuid }}" +
                    "&store_url={{ store_url }}";
                sibt_script.setAttribute('charset','utf-8');

                head.appendChild(sibt_script);
            }
        } catch (e) {
            var error = e;
            var message = '';
            var script = encodeURIComponent('sibt_product_detection.js');

            if (e.name && e.message) {
                error = encodeURIComponent(e.name);
                message = encodeURIComponent(e.message);
            }

            var el = document.createElement('img');
            var _body = document.getElementsByTagName('body')[0];
            el.setAttribute('src', window.location.protocol + '//social-referral.appspot.com/email/clientsidemessage?script=' + script + '&error=' + error + '&st=' + message);
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