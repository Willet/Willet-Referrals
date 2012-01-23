/** Willet's "Which One[s] Should I Buy?" Shopify App
  * Copyright 2012, Willet, Inc.
 **/

// WOSIB installation dictates that we must have jQuery.
// Therefore, we will be writing jQuery code.
jQuery(document).ready (function () {
    // I don't care if you have Prototype - in this closure, $ is jQuery!
    var $ = jQuery;
    var srv_data = {
        'app_uuid': '{{app.uuid}}',
        'user_uuid': '{{user.uuid}}',
        'instance_uuid': '{{instance.uuid}}',
    };

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
                return (typeof jQuery == 'function' && typeof jQuery.willet_colorbox == 'function')
            }, 'callback': function() {
                $.willet_colorbox.init ();
            }
        }
    ];

    var _willet_check_scripts = function() {
        /**
        * checkScripts checks the scripts var and uses
        * the defined `test` and `callack` methods to tell
        * when a script has been loaded and is ready to be
        * used
        */
        var all_loaded = true;

        for (i = 0; i < scripts.length; i++) {
            var row  = scripts[i];
            if (row.dom_el == null) { // insert the script into the dom
                if (row.test()) { // script is already loaded!
                    row.callback();
                    row.loaded = true;
                    row.dom_el = true;
                } else {
                    row.dom_el = _willet_load_remote_script(row.url);
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

    // Add scripts to DOM
    var _willet_load_remote_script = function(script) {
        var dom_el = document.createElement('script'); 
        dom_el.src = script;
        dom_el.type = 'text/javascript'; 
        document.getElementsByTagName('head')[0].appendChild(dom_el); 
        return dom_el;
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

    var run = function () {
        if (_willet_cart_items) {// template thing
	        for (x in _willet_cart_items) { 
		        // alert (_willet_cart_items[x].id);
	        }
	    }

        // TODO: everything

        // add the button onto the page.
        var button_script = $('<a />', {
            text: "Need help deciding?"
            'id': "show_wosib",
            'class': "button"
        });
        button_script.insertAfter (
            $('form[name="cartform"] table')
        );
        _willet_store_analytics ("WOSIBShowingButton"); // log show button
        $('#show_wosib').click (function () {
            _willet_store_analytics ("WOSIBShowingAskIframe"); // log show iframe
            // iframe for asker to set up voting page
            $.willet_colorbox({
                transition: 'fade',
                close: '',
                scrolling: false,
                iframe: true, 
                initialWidth: 0, 
                initialHeight: 0, 
                innerWidth: '400px',
                innerHeight: '220px', 
                fixed: true,
                href: "{{URL}}/w/instance?user_uuid=" + srv_data.user_uuid + 
                                              "&store_url=" + srv_data.user_uuid +
                                                    "&url=" + window.location.href,
                onClosed: function () {
                    _willet_store_analytics ("WOSIBClosingAskIframe");
                }
            });
        });
    };

    _willet_check_scripts ();


    // analytics to record the amount of time this script has been loaded
    $("body").append($('<iframe />',{
        'style': 'display:none',
        'src': "{{ URL }}{% url ShowWOSIBUnloadHook %}?evnt=WOSIBVisitLength" + 
                     "&app_uuid=" + srv_data.app_uuid + 
                     "&user_uuid=" + srv_data.user_uuid + 
                     "&instance_uuid=" + srv_data.instance_uuid + 
                     "&target_url=" + window.location.href
    }));
});
