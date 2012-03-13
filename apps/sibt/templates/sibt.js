/** 
 * Willet's "Should I Buy This" Shopify App
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

    var setCookieStorageFlag = function() {
        window.cookieSafariStorageReady = true;
    };
    
    // Safari cookie storage backup
    var firstTimeSession = 0;
    var doSafariCookieStorage = function () {
        if (firstTimeSession == 0) {
            firstTimeSession = 1;
            document.getElementById('sessionform').submit()
            setTimeout(setCookieStorageFlag, 2000);
        }
    };

    // Let's be dumb about this ... this'll fire on more than just Safari
    // BUT it will fire on Safari, which is what we need.
    // TODO: Fix this. Apparently, there is no easy way to determine strictly 'Safari'.
    if ( navigator.userAgent.indexOf('Safari') != -1 ) {
        var holder = document.createElement('div'),
            storageIFrameLoaded = false;
        var storageIFrame = document.createElement( 'iframe' );
        storageIFrame.setAttribute( 'src', "{{URL}}{% url UserCookieSafariHack %}" );
        storageIFrame.setAttribute( 'id', "sessionFrame" );
        storageIFrame.setAttribute( 'name', "sessionFrame" );
        storageIFrame.setAttribute( 'onload', "doSafariCookieStorage();" );
        storageIFrame.onload = storageIFrame.onreadystatechange = function() {
            var rs = this.readyState;
            if (rs && rs!='complete' && rs!='loaded') return;
            if (storageIFrameLoaded) return;
            storageIframeLoaded = true;
            doSafariCookieStorage();
        };
        storageIFrame.style.display = 'none';

        var storageForm = document.createElement( 'form' );
        storageForm.setAttribute( 'id', 'sessionform' );
        storageForm.setAttribute( 'action', "{{URL}}{% url UserCookieSafariHack %}" );
        storageForm.setAttribute( 'method', 'post' );
        storageForm.setAttribute( 'target', 'sessionFrame' );
        storageForm.setAttribute( 'enctype', 'application/x-www-form-urlencoded' );
        storageForm.style.display = 'none';

        var storageInput = document.createElement( 'input' );
        storageInput.setAttribute( 'type', 'text' );
        storageInput.setAttribute( 'value', '{{user.uuid}}' );
        storageInput.setAttribute( 'name', 'user_uuid' );

        holder.appendChild( storageIFrame );
        storageForm.appendChild( storageInput );
        holder.appendChild(storageForm);
        document.body.appendChild(holder);
    } else {
        setCookieStorageFlag();
    }

    // Once all dependencies are loading, fire this function
    var _init_sibt = function () {
        // wait for DOM elements to appear + $ closure!
        jQuery(document).ready(function($) {
            // server-side variables
            jQuery.noConflict(); // Suck it, Prototype!
            var _willet_ask_success = false,
                _willet_is_asker = ('{{ is_asker }}' == 'True'), // did they ask?
                _willet_show_votes = ('{{ show_votes }}' == 'True'),
                _willet_has_voted = ('{{ has_voted }}' == 'True'),
                sibt_button_enabled = ('{{ app.button_enabled }}' == 'True'),
                sibt_version = {{sibt_version|default:"2"}},
                is_live = ('{{ is_live }}' == 'True'),
                has_results = {{ has_results }},
                _willet_padding = null,
                _willet_topbar_hide_button = null,
                willt_code = null,
                hash_index = -1;
            
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

            // jQuery cookie plugin (included to solve lagging requests)
            {% include '../../plugin/templates/js/jquery.cookie.js' %}

            var _willet_metadata = function () {
                return "app_uuid={{app_uuid}}" + 
                      "&user_uuid={{user_uuid}}" + 
                      "&instance_uuid={{instance_uuid}}" + 
                      "&refer_url=" + window.location.href;
            };

            // events
            var _willet_vote_callback = function () {
                /**
                * Called when the vote iframe is closed
                */
                var button = $('#_willet_button'),
                    original_shadow = button.css('box-shadow'),
                    glow_timeout = 400;

                var resetGlow = function() {
                    button.css('box-shadow', original_shadow);
                };
                if (_willet_show_votes && !_willet_is_asker) {
                    // closing box but not the asker!
                    var button = $('#_willet_button');
                    button.css('box-shadow', '0px 0px 15px red');
                    setTimeout(resetGlow, glow_timeout)
                }
                return;
            };

            // Send action to server
            var _willet_store_analytics = function (message) {
                var message = message || '{{ evnt }}';
                var iframe = document.createElement( 'iframe' );
                //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
                var random_id = 'a' + String((new Date()).getTime()).replace(/\D/gi,'');
                iframe.style.display = 'none';
                //iframe.src = "{{URL}}/s/storeAnalytics?evnt=" + message + 
                iframe.src = "{{ URL }}{% url TrackSIBTShowAction %}?evnt=" + message + 
                            "&" + _willet_metadata () + 
                            "&target_url=" + window.location.href;
                iframe.id = random_id;
                iframe.name = random_id;
                iframe.onload = function () {
                    try {
                        var iframe_handle = document.getElementById(random_id);
                        iframe_handle.parentNode.removeChild ( iframe_handle );
                    } catch (e) { }
                }
                document.body.appendChild( iframe );
            };
            
            /**
            * Called when ask iframe is closed
            */
            var _willet_ask_callback = function( fb_response ) {
                if (_willet_ask_success) {
                    _willet_is_asker = true;
                    $('#_willet_button').html('Refresh the page to see your results!');
                }
            };

            var _willet_button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                try {
                    $('#_willet_padding').hide();
                } catch (err) {
                    // pass!
                }
                if (_willet_is_asker || _willet_show_votes) {
                    window.location.reload(true);
                } else {
                    _willet_store_analytics(message);
                    _willet_show_ask();
                }
            };
            
            var _willet_show_results = function () {
                // show results if results are done.
                // this can be detected if a finished flag is raised.
                var url = "{{URL}}/s/results.html" + 
                          "?" + _willet_metadata () + 
                          "&refer_url=" + window.location.href;
                $.willet_colorbox({
                    href: url,
                    transition: 'fade',
                    close: '',
                    scrolling: false,
                    iframe: true, 
                    initialWidth: 0, 
                    initialHeight: 0, 
                    innerWidth: '600px',
                    innerHeight: '400px', 
                    fixed: true,
                    onClosed: function () { }
                });
            };

            var _willet_show_ask = function ( message ) {
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

            var purchase_cta = $('#_willet_shouldIBuyThisButton');
            if (purchase_cta.length > 0) {
                // is the div there?
                // actually running it
                _willet_store_analytics();

                // run our scripts
                var hash        = window.location.hash;
                var hash_search = '#code=';
                hash_index  = hash.indexOf(hash_search);
                willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
                if (sibt_button_enabled) {
                    if (sibt_version <= 2) {
                        var button = document.createElement('a');
                        var button_html = '';
                        // only add button if it's enabled in the app 
                        if (_willet_is_asker) {
                            button_html = 'See what your friends said!';
                        } else if (_willet_show_votes) {
                            button_html = 'Help {{ asker_name }} by voting!';
                        } else {
                            button_html = AB_CTA_text;
                        }

                        button = $(button)
                            .html(button_html)
                            .css('display', 'inline-block')
                            .attr('title', 'Ask your friends if you should buy this!')
                            .attr('id','_willet_button')
                            .attr('class','_willet_button willet_reset')
                            .click(_willet_button_onclick);
                        $(purchase_cta).append(button);
                    } else if (sibt_version == 3) {
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
                        $(purchase_cta).append(button);
                        $('#_willet_button').click(_willet_button_onclick);
                        
                        // if server sends a flag that indicates "results available"
                        // (not necessarily "finished") then show finished button
                        if (has_results) {
                            $('#_willet_button_v3 .button').hide ();
                            $('<div />', {
                                'id': "_willet_SIBT_results",
                                'class': "button"
                            })
                            .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                            .appendTo(button)
                            .css({
                                'display': 'inline-block'
                            })
                            .click (_willet_show_results);
                        }
                    }
                    
                    // watch for message
                    // Create IE + others compatible event handler
                    $(window).bind('onmessage message', function(e) {
                        var message = e.originalEvent.data;
                        if (message == 'shared') {
                            _willet_ask_success = true;
                        } else if (message == 'close') {
                            $.willet_colorbox.close();
                        }
                    });
                    
                } 
                
                // analytics to record the amount of time this script has been loaded
                $('<iframe />', {
                    css : {'display': 'none'},
                    src : "{{ URL }}{% url ShowOnUnloadHook %}?evnt=SIBTVisitLength" + 
                                 "&" + _willet_metadata ()
                }).appendTo("body");

                // Load jQuery colorbox
                manage_script_loading(['{{ URL }}/s/js/jquery.colorbox.js?' + _willet_metadata ()],
                    function () {
                        // init colorbox last
                        // $.willet_colorbox = jQuery.willet_colorbox;
                        window.jQuery.willet_colorbox.init ();
                        var hash        = window.location.hash;
                        var hash_search = '#open_sibt=';
                        hash_index  = hash.indexOf(hash_search);
                        if (has_results && hash_index != -1) { // if vote has results and voter came from an email
                            _willet_show_results ();
                        }
                    }
                );
            }
        });
    };

    var scripts_to_load = ['{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}'];

    if (!window.jQuery || window.jQuery.fn.jquery < "1.4.0") { // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js');
    }

    // Go time! Load script dependencies
    manage_script_loading( scripts_to_load, _init_sibt);
})();