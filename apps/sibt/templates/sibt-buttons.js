/** 
 * Willet's "Should I Buy This" Shopify App for ShopConnection
 * Copyright Willet Inc, 2012
**/

;(function () {
    var manage_script_loading = function (scripts, ready_callback) {
        // Loads scripts in parallel, and executes ready_callback when
        // all are finished loading
        var i = scripts_not_ready = scripts.length,
            ready_callback = ready_callback || function () {};

        var script_loaded = function (index) {
            // Checks if the scripts are all loaded
            if (!--scripts_not_ready) {
                // Good to go!
                ready_callback();
            }
        };

        var load = function (url, index) {
            // Load one script
            var script = document.createElement('script'), loaded = false;
            script.setAttribute('type', 'text/javascript');
            script.setAttribute('src', url);
            script.onload = script.onreadystatechange = function() {
                var rs = this.readyState;
                if (rs && rs!='complete' && rs!='loaded') return;
                if (loaded) return;
                loaded = true;
                // Clean up DOM
                document.body.removeChild(script);
                // Script done, update manager
                script_loaded();
            };
            document.body.appendChild(script);
        };

        // Start asynchronously loading all scripts
        while (i--) {
            load(scripts[i], i);
        }
    };

    // Once all dependencies are loading, fire this function
    var init = function () {
        jQuery(document).ready(function($) {
            if (window.$ && window.$.fn && window.$.fn.jquery) {
                jQuery.noConflict(); // Suck it, Prototype!
            }

            // load CSS for colorbox as soon as possible!!
            var _willet_css = {% include stylesheet %}
            var _willet_app_css = '{{ app_css }}';
            var _willet_style = document.createElement('style');
            var _willet_head  = document.getElementsByTagName('head')[0];
            _willet_style.type = 'text/css';
            if (_willet_style.styleSheet) {
                _willet_style.styleSheet.cssText = _willet_css + _willet_app_css;
            } else {
                var rules = document.createTextNode(_willet_css + _willet_app_css);
                _willet_style.appendChild(rules);
            }
            _willet_head.appendChild(_willet_style);

            // wait for DOM elements to appear + $ closure!
            var ask_success = false,
                is_asker = ('{{ is_asker }}' == 'True'), // did they ask?
                is_live = ('{{ is_live }}' == 'True'),
                show_votes = ('{{ show_votes }}' == 'True'),
                hash_index = -1;
            
            var willet_metadata = function () {
                return  'app_uuid={{app.uuid}}&' + 
                        'user_uuid={{user.uuid}}&' + 
                        'instance_uuid={{instance.uuid}}&' + 
                        'target_url=' + window.location.href;
            };
            
            // Send action to server
            var store_analytics = function (message) {
                var message = message || '{{ evnt }}';
                //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
                var random_id = 'a' + String((new Date()).getTime()).replace(/\D/gi,'');
                
                $('<iframe />', {
                    id: random_id,
                    name: random_id,
                    css : {'display': 'none'},
                    src : "{{ URL }}{% url TrackSIBTShowAction %}?evnt=" + message + "&" + willet_metadata (),
                    load: function () {
                        try {
                            var iframe_handle = document.getElementById(random_id);
                            iframe_handle.parentNode.removeChild ( iframe_handle );
                        } catch (e) { }
                    }
                }).appendTo("body");
            };
            
            /**
            * Called when ask iframe is closed
            */
            var _willet_ask_callback = function( fb_response ) {
                if (ask_success) {
                    is_asker = true;
                    $('#_willet_button').html('Refresh the page to see your results!');
                }
            };

            var _willet_button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                if (is_asker || show_votes) {
                    window.location.reload(true);
                } else {
                    store_analytics(message);
                    show_ask ();
                }
            };

            var show_ask = function ( message ) {
                // shows the ask your friends iframe

                var url =  "{{URL}}/s/ask.html?user_uuid={{ user.uuid }}" + 
                                             "&store_url={{ store_url }}" +
                                             "&url=" + window.location.href;
                $.willet_colorbox({
                    transition: 'fade',
                    close: '',
                    scrolling: false,
                    iframe: true, 
                    initialWidth: 0, 
                    initialHeight: 0, 
                    innerWidth: '600px',
                    innerHeight: '400px', 
                    fixed: true,
                    href: url,
                    onClosed: _willet_ask_callback
                });
            };

            var sibt_elem = $('#_willet_shouldIBuyThisButton');
            if (sibt_elem.length > 0) {
                // is the div there?
                // actually running it
                store_analytics();

                var button = $("<div />", {
                    'id': '_willet_button_v3'
                });
                button.html ("<p>Should you buy this? Can\'t decide?</p>" +
                             "<div class='button' " +
                                 "title='Ask your friends if you should buy this!'>" +
                                 "<img src='{{URL}}/static/plugin/imgs/logo_button_25x25.png' alt='logo' />" +
                                 "<div id='_willet_button' class='title'>Ask Trusted Friends</div>" +
                             "</div>")
                .css({
                    'clear': 'both'
                });
                $(sibt_elem).append(button);
                $('#_willet_button').click(_willet_button_onclick);
                
                // watch for message
                // Create IE + others compatible event handler
                $(window).bind('onmessage message', function(e) {
                    var message = e.originalEvent.data;
                    if (message == 'shared') {
                        ask_success = true;
                    } else if (message == 'close') {
                        $.willet_colorbox.close();
                    }
                });
                
                // analytics to record the amount of time this script has been loaded
                $('<iframe />', {
                    css : {'display': 'none'},
                    src : "{{ URL }}{% url ShowOnUnloadHook %}?evnt=SIBTVisitLength&" + willet_metadata ()
                }).appendTo("body");
                
                // Load jQuery colorbox
                manage_script_loading([
                    '{{ URL }}/s/js/jquery.colorbox.js?' + willet_metadata ()], function () {
                        // init colorbox last
                        window.jQuery.willet_colorbox.init ();
                });
            }
        });
    };

    var scripts_to_load = ['{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}'];

    if (!window.jQuery || window.jQuery.fn.jquery < "1.4.0") { // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js');
    }

    // Go time! Load script dependencies
    manage_script_loading( scripts_to_load, init);
})();