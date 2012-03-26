;(function (w, d) {
    /** 
     * Willet's "Should I Buy This"
     * Copyright Willet Inc, 2012
     *
     * This script serves SIBTShopify, SIBT Connection (SIBT in ShopConnection),
     * and SIBT-JS (for outside Shopify).
     *
     * w and d are aliases of window and document.
    **/

    var $_conflict = !(window.$ && window.$.fn && window.$.fn.jquery);

    // These ('???' == 'True') guarantees missing tag, ('' == 'True') = false
    var ask_success = false;
    var is_asker = ('{{ is_asker }}' == 'True'); // did they ask?
    var is_live = ('{{ is_live }}' == 'True');
    var show_votes = ('{{ show_votes }}' == 'True');
    var has_voted = ('{{ has_voted }}' == 'True');
    var sibt_button_enabled = ('{{ app.button_enabled }}' == 'True');
    var topbar_enabled = ('{{ app.top_bar_enabled }}' == 'True');
    var sibt_version = {{sibt_version|default:"3"}};
    var has_results = ('{{ has_results }}' == 'True');
    var show_top_bar_ask = ('{{ show_top_bar_ask }}' == 'True');
    var unsure_mutli_view = ('{{ unsure_mutli_view }}' == 'True');
    var detect_shopconnection = ('{{ detect_shopconnection }}' == 'True'); // set this flag on if SIBT needs to be disabled on the same page as Buttons
    var _willet_topbar = null;
    var _willet_padding = null;
    var _willet_topbar_hide_button = null;
    var willt_code = null;
    var hash_index = -1;

    try { // debug if available
        window.console = (typeof(window.console) === 'object' && (
                (typeof(window.console.log) === 'function' && typeof(window.console.error) ==='function') ||
                (typeof(window.console.log) === 'object' && typeof(window.console.error) ==='object')
            )) ? window.console : { log: function () {}, error: function () {} };
    } catch (e) {
        window.console = {
            log: function () {},
            error: function () {}
        };
    }

    var manage_script_loading = function (scripts, ready_callback) {
        // Loads scripts in parallel, and executes ready_callback when all are finished loading
        var i = scripts_not_ready = scripts.length;
        var ready_callback = ready_callback || function () {};

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
                if (loaded || (rs && rs!='complete' && rs!='loaded')) return;
                loaded = true;
                document.body.removeChild(script); // Clean up DOM
                // console.log('loaded ' + url);
                script_loaded(); // Script done, update manager
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
        var holder = document.createElement('div');
        var storageIFrameLoaded = false;
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

    var scripts_to_load = ['{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}'];
    if (!window.jQuery || window.jQuery.fn.jquery < "1.4.0") { // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js');
    }

    // Once all dependencies are loading, fire this function
    var init = function () {
        // console.log('called init');

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

        if ($_conflict) {
            jQuery.noConflict(); // Suck it, Prototype!
            // console.log('noConflicted');
        }
        
        jQuery(document).ready(function($) { // wait for DOM elements to appear + $ closure!
            // console.log('jQuery ready');

            // jQuery shaker plugin
            (function(a){var b={};var c=4;a.fn.shaker=function(){b=a(this);b.css("position","relative");b.run=true;b.find("*").each(function(b,c){a(c).css("position","relative")});var c=function(){a.fn.shaker.animate(a(b))};setTimeout(c,25)};a.fn.shaker.animate=function(c){if(b.run==true){a.fn.shaker.shake(c);c.find("*").each(function(b,c){a.fn.shaker.shake(c)});var d=function(){a.fn.shaker.animate(c)};setTimeout(d,25)}};a.fn.shaker.stop=function(a){b.run=false;b.css("top","0px");b.css("left","0px")};a.fn.shaker.shake=function(b){var d=a(b).position();a(b).css("left",d["left"]+Math.random()<.5?Math.random()*c*-1:Math.random()*c)}})(jQuery);
            
            // jQuery cookie plugin (included to solve lagging requests)
            {% include '../../plugin/templates/js/jquery.cookie.js' %}

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
                var docViewTop = $(window).scrollTop();
                var docViewBottom = docViewTop + $(window).height();
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
            
            // Called when ask iframe is closed
            var ask_callback = function( fb_response ) {
                if (ask_success) {
                    is_asker = true;
                    $('#_willet_button').html('Refresh the page to see your results!');
                }
            };

            var button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                try {
                    $('#_willet_padding').hide();
                } catch (err) {
                    // pass!
                }
                if (is_asker || show_votes) {
                    // we are no longer showing results with the topbar.
                    show_results ();
                } else {
                    store_analytics(message);
                    show_ask ();
                }
            };
            
            var show_results = function () {
                // show results if results are done.
                // this can be detected if a finished flag is raised.
                var url = "{{URL}}/s/results.html" + 
                          "?" + willet_metadata () + 
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
                    onClosed: ask_callback
                });
            };


            {% if app.top_bar_enabled %} // add this topbar code only if necessary
                var topbar_onclick = function(e) {
                    // Onclick event handler for the 'sibt' button
                    button_onclick(e, 'SIBTUserClickedTopBarAsk');
                };

                var unhide_topbar = function() {
                    // When a user hides the top bar, it shows the little
                    // "Show" button in the top right. This handles the clicks to that
                    $.cookie('_willet_topbar_closed', false);
                    _willet_topbar_hide_button.slideUp('fast');
                    //_willet_padding.show();
                    if (_willet_topbar == null) {
                        if (show_votes || hash_index != -1) {
                            show_topbar();
                            store_analytics('SIBTUserReOpenedTopBar');
                        } else {
                            show_topbar_ask();
                            store_analytics('SIBTShowingTopBarAsk');
                        }
                    } else {
                        _willet_topbar.slideDown('fast'); 
                        store_analytics('SIBTUserReOpenedTopBar');
                    }
                };

                var close_top_bar = function() {
                    // Hides the top bar and padding
                    $.cookie('_willet_topbar_closed', true);
                    _willet_topbar.slideUp('fast'); 
                    _willet_topbar_hide_button.slideDown('fast');
                    store_analytics('SIBTUserClosedTopBar');
                };

                // Expand the top bar and load the results iframe
                var do_vote = function(vote) {
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
                    if (doing_vote || has_voted) {
                        _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
                    } else if (is_asker) {
                        _willet_topbar.find('div.message').html('Your friends say:   ').fadeIn();
                    }

                    // start loading the iframe
                    iframe_div.show();
                    iframe.attr('src', ''); 
                    iframe.attr('src', results_src); 
                
                    iframe.fadeIn('medium');
                };
                var do_vote_yes = function() { do_vote(1);};
                var do_vote_no = function() { do_vote(0);};
                
                var build_top_bar_html = function (is_ask_bar) {
                    // Builds the top bar html
                    // is_ask_bar option boolean
                    // if true, loads ask_in_the_bar iframe

                    if (is_ask_bar || false) {
                        var AB_CTA_text = AB_CTA_text || 'Ask your friends for advice!'; // AB lag
                        var bar_html = "<div class='_willet_wrapper'><p style='font-size: 15px'>Decisions are hard to make. " + AB_CTA_text + "</p>" +
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
                
                var show_topbar = function() {
                    // Shows the vote top bar
                    var body = $('body'); 

                    // create the padding for the top bar
                    _willet_padding = document.createElement('div');
                    _willet_padding = $(_willet_padding)
                        .attr('id', '_willet_padding')
                        .css('display', 'none');

                    _willet_topbar = document.createElement('div');
                    _willet_topbar = $(_willet_topbar)
                        .attr('id', '_willet_sibt_bar')
                        .css('display', "none")
                        .html(build_top_bar_html());
                    body.prepend(_willet_padding);
                    body.prepend(_willet_topbar);

                    // bind event handlers
                    $('#_willet_close_button').unbind().bind('click', close_top_bar);
                    $('#yesBtn').click(do_vote_yes);
                    $('#noBtn').click(do_vote_no);

                    _willet_padding.show(); 
                    _willet_topbar.slideDown('slow');

                    if (!is_live) {
                        // voting is over folks!
                        _willet_topbar.find('div.message').html('Voting is over!');
                        toggle_results();
                    } else if (show_votes && !has_voted && !is_asker) {
                        // show voting!
                        _willet_topbar.find('div.vote').show();
                    } else if (has_voted && !is_asker) {
                        // someone has voted && not the asker!
                        _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
                        toggle_results();
                    } else if (is_asker) {
                        // showing top bar to asker!
                        _willet_topbar.find('div.message').html('Your friends say:   ').fadeIn();
                        toggle_results();
                    }
                };

                var show_topbar_ask = function() {
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

                    $('#_willet_close_button').unbind().bind('click', close_top_bar);
                    
                    _willet_topbar.find( '._willet_wrapper p' )
                        .css('cursor', 'pointer')
                        .click(topbar_onclick);
                    _willet_padding.show(); 
                    _willet_topbar.slideDown('slow'); 
                };

                var topbar_ask_success = function () {
                    // if we get a postMessage from the iframe
                    // that the share was successful
                    store_analytics('SIBTTopBarShareSuccess');
                    var iframe = _willet_topbar.find('div.iframe iframe');
                    var iframe_div = _willet_topbar.find('div.iframe');
                    
                    is_asker = true;

                    iframe_div.fadeOut('fast', function() {
                        _willet_topbar.animate({height: '40'}, 500);
                        iframe.attr('src', ''); 
                        toggle_results();
                    });
                };
                
                var toggle_results = function() {
                    // Used to toggle the results view
                    // iframe has no source, hasnt been loaded yet
                    // and we are FOR SURE showing it
                    do_vote(-1);
                };
            {% endif %} ; // app.top_bar_enabled

            // SIBT Connection will be prioritised and show if both SIBT and SIBT Connection exist on page.
            var sibt_elem = $('#mini_sibt_button').eq(0); // SIBT for ShopConnection (SIBT Connection)
            var purchase_cta = $('#_willet_shouldIBuyThisButton').eq(0); // SIBT standalone (v2, v3)
            var sibtjs_elem = $('._willet_sibt').eq(0); // SIBT-JS

            // SIBT-JS
            if (sibtjs_elem.length > 0) { // is the div there?
                console.log('at least one ._willet_sibt exists');
                store_analytics();

                sibtjs_elem.click(button_onclick);
                sibtjs_elem.css ({
                    'background': (has_results? "url('{{ URL }}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent":
                                                "url('{{ URL }}/static/sibt/imgs/button_bkg.png') 3% 20% no-repeat transparent"),
                    'width': '80px',
                    'height': '21px',
                    'display': 'inline-block'
                });
                
                // shake ONLY the SIBT button when scrolled into view
                var shaken_yet = false;
                $(window).scroll (function () {
                    if (is_scrolled_into_view (sibtjs_elem) && !shaken_yet) {
                        setTimeout (function () {
                            $(sibtjs_elem).shaker();
                            setTimeout (function () {
                                $(sibtjs_elem).shaker.stop();
                                shaken_yet = true;
                            }, 600); // shake duration
                        }, 700); // wait for ?ms until it shakes
                    }
                });
            }

            // SIBT Connection
            if (sibt_elem.length > 0) { // is the div there?
                console.log('#mini_sibt_button exists');
                store_analytics();

                sibt_elem.click(button_onclick);
                
                if (has_results) {
                    sibt_elem.css ({
                        'background': "url('{{ URL }}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent",
                        'width': '80px'
                    });
                }
                // shake ONLY the SIBT button when scrolled into view
                var shaken_yet = false;
                $(window).scroll (function () {
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
            }

            // SIBT standalone
            if (!(detect_shopconnection && sibt_elem.length) && // if SIBT can show, and
                purchase_cta.length > 0) {                      // if SIBT *should* show
                console.log('#_willet_shouldIBuyThisButton exists');
                store_analytics();

                // run our scripts
                var hash        = window.location.hash;
                var hash_search = '#code=';
                hash_index  = hash.indexOf(hash_search);
                willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
                

                {% if app.top_bar_enabled %} // add this topbar code only if necessary
                    console.log('topbar enabled');
                    var cookie_topbar_closed = ($.cookie('_willet_topbar_closed') == 'true');

                    // create the hide button
                    _willet_topbar_hide_button = $(document.createElement('div'));
                    _willet_topbar_hide_button.attr('id', '_willet_topbar_hide_button')
                        .css('display', 'none')
                        .click(unhide_topbar);
                    
                    if ( show_top_bar_ask ) {
                        _willet_topbar_hide_button.html('Get advice!');
                    } else if( is_asker ) {
                        _willet_topbar_hide_button.html('See your results!');
                    } else {
                        _willet_topbar_hide_button.html('Help {{ asker_name }}!');
                    }

                    $('body').prepend(_willet_topbar_hide_button);

                    if (show_top_bar_ask) {
                        if (cookie_topbar_closed) {
                            // user has hidden the top bar
                            _willet_topbar_hide_button.slideDown('fast');
                        } else {
                            store_analytics('SIBTShowingTopBarAsk');
                            show_topbar_ask();
                        }
                    }
                {% endif %} ; // app.top_bar_enabled


                if (sibt_button_enabled) {
                    if (sibt_version <= 2) {
                        console.log('v2 button is enabled');
                        var button = document.createElement('a');
                        var button_html = '';
                        // only add button if it's enabled in the app 
                        if (is_asker) {
                            button_html = 'See what your friends said!';
                        } else if (show_votes) {
                            button_html = 'Help {{ asker_name }} by voting!';
                        } else {
                            var AB_CTA_text = AB_CTA_text || 'Ask your friends for advice!'; // AB lag
                            button_html = AB_CTA_text;
                        }

                        button = $(button)
                            .html(button_html)
                            .css('display', 'inline-block')
                            .attr('title', 'Ask your friends if you should buy this!')
                            .attr('id','_willet_button')
                            .attr('class','_willet_button willet_reset')
                            .click(button_onclick);
                        $(purchase_cta).append(button);
                    } else if (sibt_version == 3) {
                        console.log('v3 button is enabled');
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
                        $('#_willet_button').click(button_onclick);
                        
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
                            .click (show_results);
                        }
                        
                        var $wbtn = $('#_willet_button_v3 .button');
                        if ($wbtn.length > 0) {
                            $wbtn = $($wbtn[0]);
                        }
                        if ($wbtn) {
                            var shaken_yet = false;
                            $(window).scroll (function () { // shake ONLY the SIBT button when scrolled into view
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
                    }
                } // if sibt_button_enabled
            } // if #_willet_shouldIBuyThisButton

            // Load jQuery colorbox
            if (!$.willet_colorbox) {
                manage_script_loading(
                    ['{{ URL }}/s/js/jquery.colorbox.js?' + willet_metadata ()],
                    function () {
                        $.willet_colorbox.init (); // init colorbox last
                        
                        // watch for message; Create IE + others compatible event handler
                        $(window).bind('onmessage message', function(e) {
                            var message = e.originalEvent.data;
                            if (message == 'shared') {
                                ask_success = true;
                            } else if (message == 'close') {
                                $.willet_colorbox.close();
                            }
                        });

                        var hash = window.location.hash;
                        var hash_search = '#open_sibt=';
                        hash_index = hash.indexOf(hash_search);
                        if (has_results && hash_index != -1) { // if vote has results and voter came from an email
                            show_results ();
                        }
                    }
                );
            }

            // analytics to record the amount of time this script has been loaded
            $('<iframe />', {
                css : {'display': 'none'},
                src : "{{ URL }}{% url ShowOnUnloadHook %}?" + willet_metadata ({'evnt': 'SIBTVisitLength'})
            }).appendTo("body");
        });
    };

    // Go time! Load script dependencies
    manage_script_loading(scripts_to_load, init);
})(window, document);
