/** Willet's "Which One[s] Should I Buy?" Shopify App
  * Copyright 2012, Willet, Inc.
 **/

// WOSIB installation provides jQuery 1.6.2.
// Therefore, we will be writing jQuery code.
jQuery(document).ready (function () {
    // if cart is empty, do nothing
    if (_willet_cart_items && _willet_cart_items.length > 0) {
        var $ = jQuery; // Do not use "jQuery" in this closure.
        var srv_data = {
            'app_uuid': '{{app.uuid}}',
            'user_uuid': '{{user.uuid}}',
            'instance_uuid': '{{instance.uuid}}',
            'store_url': 'http://' + document.domain,
        };
        var _willet_css = {% include stylesheet %} // pre-quoted
        var _willet_app_css = '{{ app_css }}';

        // detect just safari: http://api.jquery.com/jQuery.browser/
        $.browser.safari = ( $.browser.safari && 
            /chrome/.test(navigator.userAgent.toLowerCase()) ) ? false : true;

        // array.map()
        if (!Array.prototype.map) {
            Array.prototype.map = function(fun /*, thisp*/) {
	            var len = this.length;
	            if (typeof fun != "function")
	                throw new TypeError();

	            var res = new Array(len);
	            var thisp = arguments[1];
	            for (var i = 0; i < len; i++) {
	                if (i in this) res[i] = fun.call(thisp, this[i], i, this);
	            }
	            return res;
	        };
        }

        // Add scripts to DOM
        var _willet_load_script = function (script) {
            var dom_el = document.createElement('script'); 
            dom_el.type = 'text/javascript'; 
            dom_el.src = script;
            return _willet_insert_head_element (dom_el);
        };

        var _willet_load_css = function (script) {
            var dom_el = document.createElement('link'); 
            dom_el.type = 'text/css'; 
            dom_el.rel = 'stylesheet';
            dom_el.href = script;
            return _willet_insert_head_element (dom_el);
        };

        var _willet_insert_head_element = function (element) {
            document.getElementsByTagName('head')[0].appendChild(element); 
            return element;
        }

        // load the cockamamy CSS ASAP
        var _willet_style = document.createElement('style');
            var _willet_head  = document.getElementsByTagName('head')[0];
            _willet_style.type = 'text/css';
            _willet_style.setAttribute('charset','utf-8');
            _willet_style.setAttribute('media','all');
            if (_willet_style.styleSheet) {
                _willet_style.styleSheet.cssText = _willet_css + _willet_app_css;
            } else {
                var rules = document.createTextNode(_willet_css + _willet_app_css);
                _willet_style.appendChild(rules);
            }
            document.getElementsByTagName('head')[0].appendChild(_willet_style);

        /*  NO
            _willet_load_css ("{{ URL }}/w/button.css?app_uuid=" + srv_data.app_uuid);
            _willet_load_css ("{{ URL }}/w/colorbox.css?app_uuid=" + srv_data.app_uuid);*/

        var scripts = [
            /**
            * Scripts to load into the dom
            *   name - name of the script
            *   url - url of script
            *   dom_el - dom element once inserted
            *   loaded - script has been loaded
            *   test - method to test if it has been loaded
            *   callback - callback after test is success
            */
            {   'name': 'Modernizr',
                'url': '{{ URL }}/static/js/modernizr.custom.js',
                'dom_el': null,
                'loaded': false,
                'test': function() {
                    return (typeof Modernizr == 'object');
                }, 'callback': function() {
                    return;
                }
            },{ 'name': 'jQuery Colorbox',
                'url': '{{ URL }}/w/js/jquery.colorbox.js?' + 
                         "app_uuid=" + srv_data.app_uuid + 
                         "&user_uuid=" + srv_data.user_uuid + 
                         "&instance_uuid=" + srv_data.instance_uuid + 
                         "&target_url=" + window.location.href,
                'dom_el': null,
                'loaded': false,
                'test': function() {
                    return typeof $.willet_colorbox == 'function';
                }, 'callback': function() {
                    $.willet_colorbox.init ();
                }
            }
        ];

        var _willet_check_scripts = function() {
            var all_loaded = true;
            for (i = 0; i < scripts.length; i++) {
                var row  = scripts[i];
                if (row.dom_el == null) { // insert the script into the dom
                    if (row.test()) { // script is already loaded!
                        row.callback();
                        row.loaded = true;
                        row.dom_el = true;
                    } else {
                        row.dom_el = _willet_load_script(row.url);
                    }
                }
                if (row.loaded == false) {
                    if (row.test ()) { // script is now loaded!
                        row.callback ();
                        row.loaded = true;
                    } else {
                        all_loaded = false;
                    }
                }
            }

            if (all_loaded) {
                run (); // good job
            } else {
                window.setTimeout (_willet_check_scripts, 100);
            }
        };
        
        // Send action to server.
        var _willet_store_analytics = function (message) {
            var message = message || '{{ evnt }}';
            //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
            var random_id = 'a' + String((new Date()).getTime()).replace(/\D/gi,'');
            $("body").append($('<iframe />',{
                'style': 'display:none',
                'src': "{{ URL }}{% url TrackWOSIBShowAction %}?evnt=" + message + 
                             "&app_uuid=" + srv_data.app_uuid + 
                             "&user_uuid=" + srv_data.user_uuid + 
                             "&instance_uuid=" + srv_data.instance_uuid + 
                             "&target_url=" + window.location.href,
                'id': random_id
            }));
            $('#' + random_id).load(function () {
                try { // on load, unload itself
                    var iframe_handle = document.getElementById (random_id);
                    iframe_handle.parentNode.removeChild (iframe_handle);
                } catch (e) {} // do nothing
            });
        };
        
        var _willet_show_ask = function () {
            var url = "{{URL}}/w/preask?store_url=" + encodeURI(srv_data.store_url) + 
                      "&variants=" +
                      _willet_cart_items.map(function (x) {
                          // func collects all variant IDs for the cart items.
                          return x.variant_id;
                      }).join(',');
            $.willet_colorbox({
                href: url,
                transition: 'fade',
                close: '',
                scrolling: false,
                iframe: true, 
                initialWidth: 0, 
                initialHeight: 0, 
                innerWidth: '790px',
                innerHeight: '490px', 
                fixed: true,
                onClosed: function () {
                    // derp
                }
            });
        };

        var run = function () {
            // add the button onto the page right now
            var button_script = $('<input />', {
                'type': "button",
                'value': "Need help deciding?",
                'id': "show_wosib",
                // 'class': "button _willet_button",
            });
            button_script.insertAfter (
                $('form[name="cartform"] table')
            );
            $('#show_wosib').click (function () {
                _willet_store_analytics ("WOSIBShowingAskIframe"); // log show iframe
                // iframe for asker to set up voting page
                _willet_show_ask ();
            });
            _willet_store_analytics ("WOSIBShowingButton"); // log show button
            
            // analytics to record the amount of time this script has been loaded
            $("body").append($('<iframe />',{
                'style': 'display:none',
                'src': "{{ URL }}{% url ShowWOSIBUnloadHook %}?evnt=WOSIBVisitLength" + 
                         "&app_uuid=" + srv_data.app_uuid + 
                         "&user_uuid=" + srv_data.user_uuid + 
                         "&instance_uuid=" + srv_data.instance_uuid + 
                         "&target_url=" + window.location.href
            }));
        };

        _willet_check_scripts (); // eventually run()s it
    }
});
