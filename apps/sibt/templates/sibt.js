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
        {% include '../../plugin/templates/js/jquery.cookie.js' %}

        jQuery(document).ready(function($) {
            // wait for DOM elements to appear + $ closure!
            var _willet_ask_success = false,
                _willet_is_asker = ('{{ is_asker }}' == 'True'), // did they ask?
                _willet_show_votes = ('{{ show_votes }}' == 'True'),
                _willet_has_voted = ('{{ has_voted }}' == 'True'),
                sibt_button_enabled = ('{{ app.button_enabled }}' == 'True'),
                sibt_version = {{sibt_version|default:"2"}},
                is_live = ('{{ is_live }}' == 'True'),
                show_top_bar_ask = ('{{ show_top_bar_ask }}' == 'True'),
                _willet_topbar = null,
                _willet_padding = null,
                _willet_topbar_hide_button = null,
                willt_code = null,
                hash_index = -1;

            // events

            var is_scrolled_into_view = function (elem) {
                // http://stackoverflow.com/questions/487073
                var docViewTop = $(window).scrollTop();
                var docViewBottom = docViewTop + $(window).height();
                var elemTop = $(elem).offset().top;
                var elemBottom = elemTop + $(elem).height();
                return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
            }
            
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
                            "&app_uuid={{app.uuid}}" +
                            "&user_uuid={{user.uuid}}" +
                            "&instance_uuid={{instance.uuid}}" +
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

            var _willet_topbar_onclick = function(e) {
                // Onclick event handler for the 'sibt' button
                _willet_button_onclick(e, 'SIBTUserClickedTopBarAsk');
            };

            var _willet_button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                try {
                    $('#_willet_padding').hide();
                    _willet_topbar.fadeOut('fast');
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
            
            var _willet_toggle_results = function() {
                // Used to toggle the results view
                // iframe has no source, hasnt been loaded yet
                // and we are FOR SURE showing it
                _willet_do_vote(-1);
            };

            var _willet_unhide_topbar = function() {
                // When a user hides the top bar, it shows the little
                // "Show" button in the top right. This handles the clicks to that
                $.cookie('_willet_topbar_closed', false);
                _willet_topbar_hide_button.slideUp('fast');
                //_willet_padding.show();
                if (_willet_topbar == null) {
                    if (_willet_show_votes || hash_index != -1) {
                        _willet_show_topbar();
                        _willet_store_analytics('SIBTUserReOpenedTopBar');
                    } else {
                        _willet_show_topbar_ask();
                        _willet_store_analytics('SIBTShowingTopBarAsk');
                    }
                } else {
                    _willet_topbar.slideDown('fast'); 
                    _willet_store_analytics('SIBTUserReOpenedTopBar');
                }
            };

            var _willet_close_top_bar = function() {
                // Hides the top bar and padding
                $.cookie('_willet_topbar_closed', true);
                _willet_topbar.slideUp('fast'); 
                _willet_topbar_hide_button.slideDown('fast');
                _willet_store_analytics('SIBTUserClosedTopBar');
            };

            // Expand the top bar and load the results iframe
            var _willet_do_vote_yes = function() { _willet_do_vote(1);};
            var _willet_do_vote_no = function() { _willet_do_vote(0);};
            var _willet_do_vote = function(vote) {
                // detecting if we just voted or not
                var doing_vote = (vote != -1);
                var vote_result = (vote == 1);

                // getting the neccesary dom elements
                var iframe_div = _willet_topbar.find('div.iframe');
                var iframe = _willet_topbar.find('div.iframe iframe');

                // constructing the iframe src
                var hash        = window.location.hash;
                var hash_search = '#code=';
                var hash_index  = hash.indexOf(hash_search);
                var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
                var results_src = "{{ URL }}/s/results.html?" +
                    "willt_code=" + willt_code + 
                    "&user_uuid={{user.uuid}}" + 
                    "&doing_vote=" + doing_vote + 
                    "&vote_result=" + vote_result + 
                    "&is_asker={{is_asker}}" +
                    "&store_id={{store_id}}" +
                    "&store_url={{store_url}}" +
                    "&instance_uuid={{instance.uuid}}" + 
                    "&url=" + window.location.href; 

                // show/hide stuff
                _willet_topbar.find('div.vote').hide();
                if (doing_vote || _willet_has_voted) {
                    _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
                } else if (_willet_is_asker) {
                    _willet_topbar.find('div.message').html('Your friends say:   ').fadeIn();
                }

                // start loading the iframe
                iframe_div.show();
                iframe.attr('src', ''); 
                iframe.attr('src', results_src); 
            
                iframe.fadeIn('medium');
            };
            
            var build_top_bar_html = function (is_ask_bar) {
                // Builds the top bar html
                // is_ask_bar option boolean
                // if true, loads ask_in_the_bar iframe

                if (is_ask_bar || false) {
                    var bar_html = "<div class='_willet_wrapper'><p style='font-size: 15px'>Decisions are hard to make." + AB_CTA_text + "</p>" +
                        "<div id='_willet_close_button' style='position: absolute;right: 13px;top: 1px; cursor: pointer;'>" +
                        "   <img src='{{ URL }}/static/imgs/fancy_close.png' width='30' height='30' />" +
                        "</div>" +
                    "</div>";
                } else {
                    var asker_text = '';
                    var message = 'Should <em>{{ asker_name }}</em> Buy This?';
                    var image_src = '{{ asker_pic }}';
                    
                    var bar_html = "<div class='_willet_wrapper'> " +
                        "<div class='asker'>" +
                            "<div class='pic'><img src='" + image_src + "' /></div>" +
                        "</div>" +
                        "<div class='message'>" + message + "</div>" +
                        "<div class='vote last' style='display: none'>" +
                        "    <button id='yesBtn' class='yes'>Yes</button> "+
                        "    <button id='noBtn' class='no'>No</button> "+
                        "</div> "+
                        "<div class='iframe last' style='display: none; margin-top: 1px;' width='600px'> "+
                        "    <iframe id='_willet_results' height='40px' frameBorder='0' width='600px' style='background-color: #3b5998'></iframe>"+ 
                        "</div>" +
                        "<div id='_willet_close_button' style='position: absolute;right: 13px;top: 13px;cursor: pointer;'>" +
                        "   <img src='{{ URL }}/static/imgs/fancy_close.png' width='30' height='30' />" +
                        "</div>" +
                    "</div>";
                }
                return bar_html;
            };

            var _willet_show_topbar = function() {
                // Shows the vote top bar
                var body = $('body'); 

                // create the padding for the top bar
                _willet_padding = document.createElement('div');
                _willet_padding = $(_willet_padding)
                    .attr('id', '_willet_padding')
                    .css('display', 'none');

                _willet_topbar  = document.createElement('div');
                _willet_topbar = $(_willet_topbar)
                    .attr('id', '_willet_sibt_bar')
                    .css('display', "none")
                    .html(build_top_bar_html());
                body.prepend(_willet_padding);
                body.prepend(_willet_topbar);

                // bind event handlers
                $('#_willet_close_button').unbind().bind('click', _willet_close_top_bar);
                $('#yesBtn').click(_willet_do_vote_yes);
                $('#noBtn').click(_willet_do_vote_no);

                _willet_padding.show(); 
                _willet_topbar.slideDown('slow');

                if (!is_live) {
                    // voting is over folks!
                    _willet_topbar.find('div.message').html('Voting is over!');
                    _willet_toggle_results();
                } else if (_willet_show_votes && !_willet_has_voted && !_willet_is_asker) {
                    // show voting!
                    _willet_topbar.find('div.vote').show();
                } else if (_willet_has_voted && !_willet_is_asker) {
                    // someone has voted && not the asker!
                    _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
                    _willet_toggle_results();
                } else if (_willet_is_asker) {
                    // showing top bar to asker!
                    _willet_topbar.find('div.message').html('Your friends say:   ').fadeIn();
                    _willet_toggle_results();
                }
            };

            var _willet_show_topbar_ask = function() {
                //Shows the ask top bar

                // create the padding for the top bar
                _willet_padding = document.createElement('div');

                _willet_padding = $(_willet_padding)
                    .attr('id', '_willet_padding')
                    .css('display', 'none');

                _willet_topbar  = document.createElement('div');
                _willet_topbar = $(_willet_topbar)
                    .attr('id', '_willet_sibt_ask_bar')
                    .attr('class', 'willet_reset')
                    .css('display', "none")
                    .html(build_top_bar_html(true));

                $("body").prepend(_willet_padding).prepend(_willet_topbar);

                var iframe = _willet_topbar.find('div.iframe iframe');
                var iframe_div = _willet_topbar.find('div.iframe');

                $('#_willet_close_button').unbind().bind('click', _willet_close_top_bar);
                
                _willet_topbar.find( '._willet_wrapper p' )
                    .css('cursor', 'pointer')
                    .click(_willet_topbar_onclick);
                _willet_padding.show(); 
                _willet_topbar.slideDown('slow'); 
            };

            var _willet_topbar_ask_success = function () {
                // if we get a postMessage from the iframe
                // that the share was successful
                _willet_store_analytics('SIBTTopBarShareSuccess');
                var iframe = _willet_topbar.find('div.iframe iframe');
                var iframe_div = _willet_topbar.find('div.iframe');
                
                _willet_is_asker = true;

                iframe_div.fadeOut('fast', function() {
                    _willet_topbar.animate({height: '40'}, 500);
                    iframe.attr('src', ''); 
                    _willet_toggle_results();
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
                var cookie_topbar_closed = ($.cookie('_willet_topbar_closed') == 'true');

                // create the hide button
                _willet_topbar_hide_button = $(document.createElement('div'));
                _willet_topbar_hide_button.attr('id', '_willet_topbar_hide_button')
                    .css('display', 'none')
                    .click(_willet_unhide_topbar);
                
                if ( show_top_bar_ask ) {
                    _willet_topbar_hide_button.html('Get advice!');
                } else if( _willet_is_asker ) {
                    _willet_topbar_hide_button.html('See your results!');
                } else {
                    _willet_topbar_hide_button.html('Help {{ asker_name }}!');
                }

                $('body').prepend(_willet_topbar_hide_button);

                if (_willet_show_votes || hash_index != -1) {
                    // if we are showing votes (user has click action)
                    // or if there is a willet hash
                    if (cookie_topbar_closed) {
                        // user has hidden the top bar
                        _willet_topbar_hide_button.slideDown('fast');
                    } else {
                        _willet_show_topbar();
                    }
                } else {
                    // check if we are showing top bar ask too
                    if (show_top_bar_ask) {
                        if (cookie_topbar_closed) {
                            // user has hidden the top bar
                            _willet_topbar_hide_button.slideDown('fast');
                        } else {
                            _willet_store_analytics('SIBTShowingTopBarAsk');
                            _willet_show_topbar_ask();
                        }
                    } 

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
                        }
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
                    
                } 
                
                // analytics to record the amount of time this script has been loaded
                $('<iframe />', {
                    css : {'display': 'none'},
                    src : "{{ URL }}{% url ShowOnUnloadHook %}?evnt=SIBTVisitLength" + 
                                 "&app_uuid={{app.uuid}}" +
                                 "&user_uuid={{user.uuid}}" +
                                 "&instance_uuid={{instance.uuid}}" +
                                 "&target_url=" + window.location.href
                }).appendTo("body");
                
                var $wbtn = $('#_willet_button_v3 .button');
                console.log ($wbtn);
                if ($wbtn.length > 0) {
                    $wbtn = $($wbtn[0]);
                }
                if ($wbtn && show_top_bar_ask) { // show_top_bar_ask is also the key for wiggling
                    var shaken_yet = false;
                    $(window).scroll (function () {
                        if (is_scrolled_into_view ($wbtn) && !shaken_yet) {
                            setTimeout (function () {
                                $($wbtn).shaker();
                                setTimeout (function () {
                                    $($wbtn).shaker.stop();
                                    shaken_yet = true;
                                }, 400); // shake duration
                            }, 750); // wait for ?ms until it shakes
                        }
                    });
                }
                
                // Load jQuery colorbox
                manage_script_loading(['{{ URL }}/s/js/jquery.colorbox.js?' + 
                    'app_uuid={{app.uuid}}&' + 
                    'user_uuid={{user.uuid}}&' + 
                    'instance_uuid={{instance.uuid}}&' + 
                    'target_url=' + window.location.href],
                    function () {
                        // init colorbox last
                        // $.willet_colorbox = jQuery.willet_colorbox;
                        window.jQuery.willet_colorbox.init ();
                });
            }
        });
    };

    var scripts_to_load = ['{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}',
                           '{{ URL }}/static/js/jquery.shaker.js'];

    if (!window.jQuery || window.jQuery.fn.jquery < "1.4.0") { // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js');
    }

    // Go time! Load script dependencies
    manage_script_loading( scripts_to_load, _init_sibt);
})();
