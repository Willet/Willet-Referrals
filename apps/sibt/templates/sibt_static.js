;(function (w, d) {
    /** 
     * Willet's "Should I Buy This" for everyone else
     * Copyright Willet Inc, 2012
     *
     * w and d are aliases of window and document.
    **/

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
            var script = d.createElement('script'), loaded = false;
            script.setAttribute('type', 'text/javascript');
            script.setAttribute('src', url);
            script.onload = script.onreadystatechange = function() {
                var rs = this.readyState;
                if (loaded || (rs && rs!='complete' && rs!='loaded')) return;
                loaded = true;
                d.body.removeChild(script); // Clean up DOM
                script_loaded(); // Script done, update manager
            };
            d.body.appendChild(script);
        };

        // Start asynchronously loading all scripts
        while (i--) {
            load(scripts[i], i);
        }
    };

    var $_conflict = !(w.$ && w.$.fn && w.$.fn.jquery);

    var scripts_to_load = []; // ['{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}']
    if (!w.jQuery || w.jQuery.fn.jquery < "1.4.0") { // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js');
    }

    // Go time! Load script dependencies, then fire this function
    manage_script_loading( scripts_to_load,  function () {
        if ($_conflict) jQuery.noConflict(); // Suck it, Prototype!
        
        jQuery(d).ready(function($) { // wait for DOM elements to appear + $ closure!

            // load CSS for colorbox as soon as possible!!
            var wil_css = {% include stylesheet %};
            var app_css = '{{ app_css }}';
            var _willet_style = d.createElement('style');
            var _willet_head  = d.getElementsByTagName('head')[0];
            _willet_style.type = 'text/css';
            if (_willet_style.styleSheet) {
                _willet_style.styleSheet.cssText = wil_css + app_css;
            } else {
                var rules = d.createTextNode(wil_css + app_css);
                _willet_style.appendChild(rules);
            }
            _willet_head.appendChild(_willet_style);
            
            // jQuery shaker plugin
            (function(a){var b={};var c=4;a.fn.shaker=function(){b=a(this);b.css("position","relative");b.run=true;b.find("*").each(function(b,c){a(c).css("position","relative")});var c=function(){a.fn.shaker.animate(a(b))};setTimeout(c,25)};a.fn.shaker.animate=function(c){if(b.run==true){a.fn.shaker.shake(c);c.find("*").each(function(b,c){a.fn.shaker.shake(c)});var d=function(){a.fn.shaker.animate(c)};setTimeout(d,25)}};a.fn.shaker.stop=function(a){b.run=false;b.css("top","0px");b.css("left","0px")};a.fn.shaker.shake=function(b){var d=a(b).position();a(b).css("left",d["left"]+Math.random()<.5?Math.random()*c*-1:Math.random()*c)}})($);

            var ask_success = false,
                is_asker = ('{{ is_asker }}' == 'True'), // did they ask?
                is_live = ('{{ is_live }}' == 'True'), // most logically, true
                has_results = ('{{ has_results }}' == 'True'),
                unsure_mutli_view = ('{{ unsure_mutli_view }}' == 'True');
            
            var willet_metadata = function (more) {
                var metadata = { // add more properties with the "more" param.
                    'app_uuid': '{{ app.uuid }}',
                    'user_uuid': '{{ user.uuid }}',
                    'instance_uuid': '{{ instance.uuid }}',
                    
                     // this should be escaped for single quotes, but who has single quotes in URLs?
                    'target_url': '{{ PAGE }}' || window.location.href
                };
                return $.param($.extend ({}, metadata, more || {})); // no beginning ?
            };
            
            var is_scrolled_into_view = function (elem) {
                // http://stackoverflow.com/questions/487073
                var docViewTop = $(w).scrollTop();
                var docViewBottom = docViewTop + $(w).height();
                var elemTop = $(elem).offset().top;
                var elemBottom = elemTop + $(elem).height();
                return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
            }

            // find largest image on page: http://stackoverflow.com/questions/3724738
            var get_largest_image = function (within) {
                within = within || d;
                var largest_image = '';
                $(within).find('img').each (function () {
                    var $this = $(this);
                    var nDim = parseFloat ($this.width()) * parseFloat ($this.height());
                    if (nDim > nMaxDim) {
                        largest_image = $this.prop('src');
                        nMaxDim = nDim;
                    }
                });
            };
            
            var get_page_title = function () {
                return d.title || '';
            };

            // Send action to server
            var store_analytics = function (message) {
                var message = message || '{{ evnt }}';
                var random_id = 'a' + String((new Date()).getTime()).replace(/\D/gi,''); //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
                
                $('<iframe />', {
                    id: random_id,
                    name: random_id,
                    css : {'display': 'none'},
                    src : "{{ URL }}{% url TrackSIBTShowAction %}?" + willet_metadata ({
                            'evnt': message
                        })
                    ,
                    load: function () {
                        try {
                            var iframe_handle = d.getElementById(random_id);
                            iframe_handle.parentNode.removeChild ( iframe_handle );
                        } catch (e) { }
                    }
                }).appendTo("body");
            };
            
            // Called when ask iframe is closed
            var ask_callback = function( fb_response ) {
                // this callback currently needs to do nothing
            };

            var button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                if (is_asker) {
                    show_results ();
                } else {
                    store_analytics(message);
                    show_ask ();
                }
            };
            
            var show_results = function () {
                // show results if results are done.
                // this can be detected if a finished flag is raised.
                var url = "{{URL}}/s/results.html?" + willet_metadata ({
                    'refer_url': '{{ PAGE }}'
                });
                $.willet_colorbox({
                    href: url,
                    transition: 'fade',
                    close: '',
                    scrolling: false,
                    iframe: true, 
                    innerWidth: '600px',
                    innerHeight: '400px', 
                    fixed: true,
                    onClosed: function () { }
                });
            };

            var show_ask = function ( message ) {
                // shows the ask your friends iframe

                var url =  "{{URL}}/s/ask.html?user_uuid={{ user.uuid }}" + 
                                             "&store_url={{ store_url }}" +
                                             "&url={{ PAGE }}";
                $.willet_colorbox({
                    transition: 'fade',
                    close: '',
                    scrolling: false,
                    iframe: true, 
                    innerWidth: '600px',
                    innerHeight: '400px', 
                    fixed: true,
                    href: url,
                    onClosed: ask_callback
                });
            };
            
            var sibt_elem = $('._willet_sibt').eq(0); // the first sibt box
            if (sibt_elem) { // is the div there?
                store_analytics();

                sibt_elem.click(button_onclick);
                
                sibt_elem.css ({
                    'background': (has_results? "url('{{ URL }}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent":
                                                "url('{{ URL }}/static/sibt/imgs/button_bkg.png') 3% 20% no-repeat transparent"),
                    'width': '80px',
                    'height': '21px',
                    'display': 'inline-block'
                });
                
                // watch for message
                // Create IE + others compatible event handler
                $(w).bind('onmessage message', function(e) {
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
                    src : "{{ URL }}{% url ShowOnUnloadHook %}?" + willet_metadata ({'evnt': 'SIBTVisitLength'})
                }).appendTo("body");
                
                // shake ONLY the SIBT button when scrolled into view
                var shaken_yet = false;
                $(w).scroll (function () {
                    if (is_scrolled_into_view (sibt_elem) && !shaken_yet) {
                        setTimeout (function () {
                            $(sibt_elem).shaker();
                            setTimeout (function () {
                                $(sibt_elem).shaker.stop();
                                shaken_yet = true;
                            }, 600); // shake duration
                        }, 700); // wait for ?ms until it shakes
                    }
                });

                // Load jQuery colorbox
                if (w && w.jQuery && !w.jQuery.willet_colorbox) {
                    manage_script_loading(
                        ['{{ URL }}/s/js/jquery.colorbox.js?' + willet_metadata ()],
                        function () {
                            w.jQuery.willet_colorbox.init (); // init colorbox last
                            var hash = w.location.hash;
                            var hash_search = '#open_sibt=';
                            hash_index = hash.indexOf(hash_search);
                            if (has_results && hash_index != -1) { // if vote has results and voter came from an email
                                show_results ();
                            }
                        }
                    );
                }
            }
        });
    });
})(window, document);
