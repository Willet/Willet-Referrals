/** 
  * Willet's "Which One[s] Should I Buy?" Shopify App
  * Copyright 2012, Willet, Inc.
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
    var _init_wosib = function () {
        // load CSS for colorbox as soon as possible!!
        var _willet_css = {% include stylesheet %}
        var _willet_app_css = '{{ app_css }}';
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
        _willet_head.appendChild(_willet_style);

        jQuery.noConflict(); // Suck it, Prototype!

        // jQuery cookie plugin (included to solve lagging requests)
        jQuery.cookie=function(a,b,c){if(arguments.length>1&&String(b)!=="[object Object]"){c=jQuery.extend({},c);if(b===null||b===undefined){c.expires=-1}if(typeof c.expires==="number"){var d=c.expires,e=c.expires=new Date;e.setDate(e.getDate()+d)}b=String(b);return document.cookie=[encodeURIComponent(a),"=",c.raw?b:encodeURIComponent(b),c.expires?"; expires="+c.expires.toUTCString():"",c.path?"; path="+c.path:"",c.domain?"; domain="+c.domain:"",c.secure?"; secure":""].join("")}c=b||{};var f,g=c.raw?function(a){return a}:decodeURIComponent;return(f=(new RegExp("(?:^|; )"+encodeURIComponent(a)+"=([^;]*)")).exec(document.cookie))?g(f[1]):null};

        jQuery(document).ready(function($) { // wait for DOM elements to appear + $ closure!

            // if cart is empty, do nothing
            if (_willet_cart_items && _willet_cart_items.length > 0) {
                var purchase_cta = $('#_willet_WOSIB_Button');
                
                var srv_data = {
                    'app_uuid': '{{app.uuid}}',
                    'user_uuid': '{{user.uuid}}',
                    'instance_uuid': '{{instance.uuid}}',
                    'store_url': '{{shop_url}}',
                    'has_results': {{has_results|default:"false"}} // true || false
                };
                var _willet_css = {% include stylesheet %} // pre-quoted
                var _willet_app_css = '{{ app_css }}';

                // detect just safari: http://api.jquery.com/jQuery.browser/
                $.browser.safari = ( $.browser.safari && 
                    /chrome/.test(navigator.userAgent.toLowerCase()) ) ? false : true;

                // array.map()
                if (!Array.prototype.map) {
                    Array.prototype.map = function(fcn /*, thisp*/) {
    	                var len = this.length;
    	                if (typeof fcn != "function")
    	                    throw new TypeError();

    	                var res = new Array(len);
    	                var thisp = arguments[1];
    	                for (var i = 0; i < len; i++) {
    	                    if (i in this) res[i] = fcn.call(thisp, this[i], i, this);
    	                }
    	                return res;
    	            };
                }
                
                // The usual things. Does NOT include first amperssand.
                var _willet_metadata = function () {
                    return "app_uuid=" + srv_data.app_uuid + 
                          "&user_uuid=" + srv_data.user_uuid + 
                          "&instance_uuid=" + srv_data.instance_uuid + 
                          "&refer_url=" + window.location.href;
                };

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

                // Send action to server.
                var _willet_store_analytics = function (message) {
                    var message = message || '{{ evnt }}';
                    //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
                    var random_id = 'a' + String((new Date()).getTime()).replace(/\D/gi,'');
                    $("body").append($('<iframe />',{
                        'style': 'display:none',
                        'src': "{{ URL }}{% url TrackWOSIBShowAction %}?" + 
                               "evnt=" + message + 
                               "&" + _willet_metadata(),
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
                    var url = "{{URL}}/w/ask.html?store_url=" + encodeURIComponent(srv_data.store_url) + 
                              "&variants=" +
                              _willet_cart_items.map(function (x) {
                                  // func collects all variant IDs for the cart items.
                                  return x.variant_id;
                              }).join(',') +
                              "&ids=" +
                              _willet_cart_items.map(function (x) {
                                  // func collects all variant IDs for the cart items.
                                  return x.id;
                              }).join(',') +
                              "&" + _willet_metadata();
                    $.willet_colorbox({
                        href: url,
                        transition: 'fade',
                        close: '',
                        scrolling: false,
                        iframe: true, 
                        initialWidth: 0, 
                        initialHeight: 0, 
                        innerWidth: '790px',
                        innerHeight: '550px', 
                        fixed: true,
                        onClosed: function () { }
                    });
                };

                var _willet_show_results = function () {
                    // show results if results are done.
                    // this can be detected if a srv_data.finished flag is raised.
                    var url = "{{URL}}/w/results.html" + 
                              "?" + _willet_metadata();
                    $.willet_colorbox({
                        href: url,
                        transition: 'fade',
                        close: '',
                        scrolling: false,
                        iframe: true, 
                        initialWidth: 0, 
                        initialHeight: 0, 
                        innerWidth: '790px',
                        innerHeight: '450px', 
                        fixed: true,
                        onClosed: function () { }
                    });
                };

                // add the button onto the page right now
                var button = $("<div />", {
                        'id': '_willet_button_v3'
                    });
                    button.html ("<p>Should you buy this? Can\'t decide?</p>" +
    		                     "<div id='_willet_button' class='button' " +
    		                         "title='Ask your friends if you should buy this!'>" +
    			                     "<img src='{{URL}}/static/plugin/imgs/logo_button_25x25.png' alt='logo' />" +
    			                     "<div class='title'>Ask Trusted Friends</div>" +
    		                     "</div>")
                    .css({
                        'clear': 'both'
                    });
    		                     
                button.appendTo (purchase_cta).css('display', 'inline-block');
                $('#_willet_button').click (function () {
                    _willet_store_analytics ("WOSIBShowingAskIframe"); // log show iframe
                    // iframe for asker to set up voting page
                    _willet_show_ask ();
                });
                _willet_store_analytics ("WOSIBShowingButton"); // log show button
                
                // if server sends a flag that indicates "results available"
                // (not necessarily "finished") then show finished button
                if (srv_data.has_results) {
                    $('#_willet_button').hide ();
                    $('<div />', {
                        'id': "_willet_WOSIB_results",
                        'class': "button"
                    })
                    .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                    .appendTo(button)
                    .css({
                        'display': 'inline-block'
                    })
                    .click (_willet_show_results);
                }

                // watch for message
                // Create IE + others compatible event handler
                $(window).bind('onmessage message', function(e) {
                    var message = e.originalEvent.data;
                    if (message == 'shared') {
                        _willet_ask_success = true;
                    } else if (message == 'top_bar_shared') {
                        _willet_topbar_ask_success();
                    } else if (message == 'close') {
                        $.willet_colorbox.close();
                    }
                });
                
                // init colorbox.
                manage_script_loading([
                    '{{ URL }}/s/js/jquery.colorbox.js?' + 
                    'app_uuid={{app.uuid}}&' + 
                    'user_uuid={{user.uuid}}&' + 
                    'instance_uuid={{instance.uuid}}&' + 
                    'target_url=' + window.location.href ],
                    function () {
                        // init colorbox last
                        if (window.jQuery.willet_colorbox) {
                            // some browsers ("Opera") loads colorbox onto window's
                            // jQuery instead of the closed $
                            $.willet_colorbox = window.jQuery.willet_colorbox;
                            $.willet_colorbox.init ();
                            window.jQuery.willet_colorbox.init ();
                        }
                    });
            }
        });
    };

    // Go time! Load script dependencies
    manage_script_loading(['https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js'],
        _init_wosib );
})();
