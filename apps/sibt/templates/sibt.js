;(function (w, d) {
    /*
     * Willet's "Should I Buy This"
     * Copyright Willet Inc, 2012
     *
     * This script serves SIBTShopify, SIBT Connection (SIBT in ShopConnection),
     * and SIBT-JS (for outside Shopify).
     *
     * w and d are aliases of window and document.
     */

    var $_conflict = !(w.$ && w.$.fn && w.$.fn.jquery);

    // These ('???' === 'True') guarantee missing tag, ('' === 'True') = false
    var ask_success = false;
    var debug = ('{{ debug }}' === 'True');
    var is_asker = ('{{ is_asker }}' === 'True'); // did they ask?
    var is_live = ('{{ is_live }}' === 'True');
    var show_votes = ('{{ show_votes }}' === 'True');
    var has_voted = ('{{ has_voted }}' === 'True');
    var button_enabled = ('{{ app.button_enabled }}' === 'True');
    var topbar_enabled = ('{{ app.top_bar_enabled }}' === 'True');
    var sibt_version = {{sibt_version|default:"3"}};
    var has_results = ('{{ has_results }}' === 'True');
    var show_top_bar_ask = ('{{ show_top_bar_ask }}' === 'True');

    // true when visitor on page more than (4 times)
    var unsure_multi_view = ('{{ unsure_multi_view }}' === 'True');

    // true when SIBT needs to be disabled on the same page as Buttons
    var detect_shopconnection = ('{{ detect_shopconnection }}' === 'True');
    var padding_elem = topbar = topbar_hide_button = willt_code = null;
    var hash_index = -1;

    try { // debug if available
        if (debug) {
            if (!(typeof(w.console) === 'object' &&
                (typeof(w.console.log) === 'function' ||
                 typeof(w.console.log) === 'object') &&
                (typeof(w.console.error) ==='function' ||
                 typeof(w.console.error) === 'object'))) {
                throw new Error("Invalid console object");
            }
        } else {
            // if not debugging, proceed to make empty console
            throw new Error("I'm sorry, Dave. I'm afraid I can't do that.");
        }
    } catch (e) {
        w.console = {
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
            var script = d.createElement('script');
            var loaded = false;
            script.setAttribute('type', 'text/javascript');
            script.setAttribute('src', url);
            script.onload = script.onreadystatechange = function() {
                var rs = this.readyState;
                if (loaded || (rs && rs !== 'complete' && rs !== 'loaded')) return;
                loaded = true;
                d.body.removeChild(script); // Clean up DOM
                // console.log('loaded ' + url);
                script_loaded(); // Script done, update manager
            };
            d.body.appendChild(script);
        };

        // Start asynchronously loading all scripts
        while (i--) {
            load(scripts[i], i);
        }
    };


    // Stores user_uuid for all browsers - differently for Safari.
    var setCookieStorageFlag = function() {
        w.cookieSafariStorageReady = true;
    };

    // Safari cookie storage backup
    var firstTimeSession = 0;
    var doSafariCookieStorage = function () {
        if (firstTimeSession === 0) {
            firstTimeSession = 1;
            d.getElementById('sessionform').submit()
            setTimeout(setCookieStorageFlag, 2000);
        }
    };

    // "Fixes" Safari's problems with XD-storage.
    if (navigator.userAgent.indexOf('Safari') !== -1) {
        var holder = d.createElement('div');
        var storageIFrameLoaded = false;
        var storageIFrame = d.createElement('iframe');
        storageIFrame.setAttribute('src', "{{URL}}{% url UserCookieSafariHack %}");
        storageIFrame.setAttribute('id', "sessionFrame");
        storageIFrame.setAttribute('name', "sessionFrame");
        storageIFrame.setAttribute('onload', "doSafariCookieStorage();");
        storageIFrame.onload = storageIFrame.onreadystatechange = function() {
            var rs = this.readyState;
            if(rs && rs !== 'complete' && rs !== 'loaded') return;
            if(storageIFrameLoaded) return;
            storageIframeLoaded = true;
            doSafariCookieStorage();
        };
        storageIFrame.style.display = 'none';

        var storageForm = d.createElement('form');
        storageForm.setAttribute('id', 'sessionform');
        storageForm.setAttribute('action', "{{URL}}{% url UserCookieSafariHack %}" );
        storageForm.setAttribute('method', 'post');
        storageForm.setAttribute('target', 'sessionFrame');
        storageForm.setAttribute('enctype', 'application/x-www-form-urlencoded');
        storageForm.style.display = 'none';

        var storageInput = d.createElement('input');
        storageInput.setAttribute('type', 'text');
        storageInput.setAttribute('value', '{{user.uuid}}');
        storageInput.setAttribute('name', 'user_uuid');

        holder.appendChild( storageIFrame );
        storageForm.appendChild( storageInput );
        holder.appendChild(storageForm);
        d.body.appendChild(holder);
    } else {
        setCookieStorageFlag();
    }

    // set up a list of scripts to load asynchronously.
    var scripts_to_load = ['{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}'];
    // turns out we need at least 1.4 for the $(<tag>,{props}) notation
    if (!w.jQuery || w.jQuery.fn.jquery < "1.4.0") {
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js');
    }

    // Once all dependencies are loading, fire this function
    var init = function () {

        // load CSS for colorbox as soon as possible!!
        var _willet_css = {% include stylesheet %}
        var _willet_app_css = '{{ app_css }}';
        var _willet_style = d.createElement('style');
        var _willet_head  = d.getElementsByTagName('head')[0];
        _willet_style.type = 'text/css';
        _willet_style.setAttribute('charset','utf-8');
        _willet_style.setAttribute('media','all');
        if (_willet_style.styleSheet) {
            _willet_style.styleSheet.cssText = _willet_css + _willet_app_css;
        } else {
            var rules = d.createTextNode(_willet_css + _willet_app_css);
            _willet_style.appendChild(rules);
        }
        _willet_head.appendChild(_willet_style);

        if ($_conflict) {
            jQuery.noConflict(); // Suck it, Prototype!
        }

        // wait for DOM elements to appear + $ closure!
        jQuery(d).ready(function($) {

            // jQuery shaker plugin
            (function(a){var b={};var c=5;a.fn.shaker=function(){b=a(this);b.css("position","relative");b.run=true;b.find("*").each(function(b,c){a(c).css("position","relative")});var c=function(){a.fn.shaker.animate(a(b))};setTimeout(c,25)};a.fn.shaker.animate=function(c){if(b.run==true){a.fn.shaker.shake(c);c.find("*").each(function(b,c){a.fn.shaker.shake(c)});var d=function(){a.fn.shaker.animate(c)};setTimeout(d,25)}};a.fn.shaker.stop=function(a){b.run=false;b.css("top","0px");b.css("left","0px")};a.fn.shaker.shake=function(b){var d=a(b).position();a(b).css("left",d["left"]+Math.random()<.5?Math.random()*c*-1:Math.random()*c)}})(jQuery);
            // jQuery cookie plugin (included to solve lagging requests)
            {% include '../../plugin/templates/js/jquery.cookie.js' %}

            var willet_metadata = function (more) {
                // constructs the 'willet' query string - no prefixing ? will be added for you.
                // add more query properties with the "more" param.
                return $.param($.extend ({}, // blank original
                    {
                        'app_uuid': '{{ app.uuid }}',
                        'user_uuid': '{{ user.uuid }}',
                        'instance_uuid': '{{ instance.uuid }}',
                        'store_url': '{{ store_url }}', // registration url
                        'target_url': '{{ page_url }}' || w.location.href // window.location
                    },
                    more || {}
                ));
            };

            var is_scrolled_into_view = function (elem) {
                // http://stackoverflow.com/questions/487073
                // returns true if elem has dimensions within the viewport.
                var docViewTop = $(w).scrollTop();
                var docViewBottom = docViewTop + $(w).height();
                var elemTop = $(elem).offset().top;
                var elemBottom = elemTop + $(elem).height();
                return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
            }

            var get_largest_image = function (within) {
                // Returns <img>.src for the largest <img> in <elem>within
                // source: http://stackoverflow.com/questions/3724738
                within = within || d;
                var nMaxDim = 0;
                var largest_image = '';
                $(within).find('img').each (function () {
                    var $this = $(this);
                    var nDim = parseFloat ($this.width()) * parseFloat ($this.height());
                    if (nDim > nMaxDim) {
                        largest_image = $this.prop('src');
                        nMaxDim = nDim;
                    }
                });
                return largest_image;
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
                    css: {'display': 'none'},
                    src: "{{ URL }}{% url TrackSIBTShowAction %}?evnt=" +
                          encodeURIComponent(message) + "&" + willet_metadata(),
                    load: function () {
                        try {
                            var iframe_handle = d.getElementById(random_id);
                            iframe_handle.parentNode.removeChild ( iframe_handle );
                        } catch (e) {
                            console.log(e.message);
                        }
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
                    console.log(err.message);
                }
                if (is_asker || show_votes) {
                    // we are no longer showing results with the topbar.
                    show_results ();
                } else {
                    store_analytics(message);
                    show_ask ();
                }
            };

            var show_colorbox = function (options) {
                var defaults = {
                    transition: 'fade',
                    close: '',
                    scrolling: false,
                    iframe: true,
                    initialWidth: 0,
                    initialHeight: 0,
                    innerWidth: '600px',
                    innerHeight: '400px',
                    fixed: true
                };
                options = $.extend({}, defaults, options);
                if ($.willet_colorbox) {
                    $.willet_colorbox(options);
                } else { // backup
                    console.log("opening window");
                    var width = parseInt(options.innerWidth);
                    var height = parseInt(options.innerHeight);
                    var left = (screen.width - width) /2;
                    var top = (screen.height - height) /2;
                    var new_window = window.open(
                        options.href, // url
                        '_blank', // name
                        'width=' + width + ',' +
                        'height=' + height + ',' +
                        'left=' + left + ',' +
                        'top=' + top,
                        true //.preserve history
                    );
                    new_window.focus();
                }
            }

            var show_results = function () {
                // show results if results are done.
                // this can be detected if a finished flag is raised.
                show_colorbox({
                    href: "{{URL}}/s/results.html?" +
                           willet_metadata ({'refer_url': w.location.href}),
                    onClosed: function () {}
                });
            };

            var show_ask = function ( message ) {
                // shows the ask your friends iframe
                show_colorbox({
                    href: "{{URL}}/s/ask.html?user_uuid={{ user.uuid }}" +
                                             "&url=" + ('{{ page_url }}' || w.location.href),
                    onClosed: ask_callback
                });
            };

            var save_product = function(data) {
                // auto-create product objects using page info, using
                // (<div class='_willet_...' data-....>) or otherwise
                // server decides if the input supplied is good to save.
                // does not guarantee saving; does not have return value; asynchronous.
                try {
                    // do NOT send .data() directly! Will cause unexpected func calls.
                    var data = {
                        'client_uuid': data.client_uuid || '{{ client.uuid }}', // REQUIRED
                        'sibtversion': data.sibtversion || sibt_version,
                        'title': data.title || '{{ product.title }}' || get_page_title(),
                        'description': data.description || '{{ product.description }}',
                        'images': data.images || '',
                        'image': data.image || get_largest_image(d),
                        'price': data.price || '0.0',
                        'tags': data.tags || '',
                        'type': data.type || '',
                        'resource_url': '{{ page_url }}' || w.location.href
                    };
                    if (data.client_uuid) {
                        $.ajax({
                            url: '{{ URL }}{% url CreateProduct %}',
                            type: "POST",
                            data: data,
                            dataType: 'json',
                            success: function () {}, // good job; I don't care
                            error: function () {}
                        });
                        console.log('sent product request');
                    }
                } catch (e) {
                    console.log(e.message);
                }
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
                    topbar_hide_button.slideUp('fast');
                    if (topbar === null) {
                        if (show_votes || hash_index !== -1) {
                            show_topbar();
                            store_analytics('SIBTUserReOpenedTopBar');
                        } else {
                            show_topbar_ask();
                            store_analytics('SIBTShowingTopBarAsk');
                        }
                    } else {
                        topbar.slideDown('fast');
                        store_analytics('SIBTUserReOpenedTopBar');
                    }
                };

                var close_top_bar = function() {
                    // Hides the top bar and padding
                    $.cookie('_willet_topbar_closed', true);
                    topbar.slideUp('fast');
                    topbar_hide_button.slideDown('fast');
                    store_analytics('SIBTUserClosedTopBar');
                };

                // Expand the top bar and load the results iframe
                var do_vote = function(vote) {
                    // detecting if we just voted or not
                    var doing_vote = (vote !== -1);
                    var vote_result = (vote === 1);

                    // getting the neccesary dom elements
                    var iframe_div = topbar.find('div.iframe');
                    var iframe = topbar.find('div.iframe iframe');

                    // constructing the iframe src
                    var hash        = w.location.hash;
                    var hash_search = '#code=';
                    var hash_index  = hash.indexOf(hash_search);
                    var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
                    var results_src = "{{ URL }}/s/results.html?" +
                        "willt_code=" + encodeURIComponent(willt_code) +
                        "&user_uuid={{user.uuid}}" +
                        "&doing_vote=" + encodeURIComponent(doing_vote) +
                        "&vote_result=" + encodeURIComponent(vote_result) +
                        "&is_asker={{is_asker}}" +
                        "&store_id={{store_id}}" +
                        "&store_url={{store_url}}" +
                        "&instance_uuid={{instance.uuid}}" +
                        "&url=" + encodeURIComponent(w.location.href);

                    // show/hide stuff
                    topbar.find('div.vote').hide();
                    if (doing_vote || has_voted) {
                        topbar.find('div.message').html('Thanks for voting!').fadeIn();
                    } else if (is_asker) {
                        topbar.find('div.message').html('Your friends say:   ').fadeIn();
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
                    padding_elem = d.createElement('div');
                    padding_elem = $(padding_elem)
                        .attr('id', '_willet_padding')
                        .css('display', 'none');

                    topbar = d.createElement('div');
                    topbar = $(topbar)
                        .attr('id', '_willet_sibt_bar')
                        .css('display', "none")
                        .html(build_top_bar_html());
                    body.prepend(padding_elem);
                    body.prepend(topbar);

                    // bind event handlers
                    $('#_willet_close_button').unbind().bind('click', close_top_bar);
                    $('#yesBtn').click(do_vote_yes);
                    $('#noBtn').click(do_vote_no);

                    padding_elem.show();
                    topbar.slideDown('slow');

                    if (!is_live) {
                        // voting is over folks!
                        topbar.find('div.message').html('Voting is over!');
                        toggle_results();
                    } else if (show_votes && !has_voted && !is_asker) {
                        // show voting!
                        topbar.find('div.vote').show();
                    } else if (has_voted && !is_asker) {
                        // someone has voted && not the asker!
                        topbar.find('div.message').html('Thanks for voting!').fadeIn();
                        toggle_results();
                    } else if (is_asker) {
                        // showing top bar to asker!
                        topbar.find('div.message').html('Your friends say:   ').fadeIn();
                        toggle_results();
                    }
                };

                var show_topbar_ask = function() {
                    //Shows the ask top bar

                    // create the padding for the top bar
                    padding_elem = d.createElement('div');

                    padding_elem = $(padding_elem)
                        .attr('id', '_willet_padding')
                        .css('display', 'none');

                    topbar  = d.createElement('div');
                    topbar = $(topbar)
                        .attr('id', '_willet_sibt_ask_bar')
                        .attr('class', 'willet_reset')
                        .css('display', "none")
                        .html(build_top_bar_html(true));

                    $("body").prepend(padding_elem).prepend(topbar);

                    var iframe = topbar.find('div.iframe iframe');
                    var iframe_div = topbar.find('div.iframe');

                    $('#_willet_close_button').unbind().bind('click', close_top_bar);

                    topbar.find( '._willet_wrapper p')
                        .css('cursor', 'pointer')
                        .click(topbar_onclick);
                    padding_elem.show();
                    topbar.slideDown('slow');
                };

                var topbar_ask_success = function () {
                    // if we get a postMessage from the iframe
                    // that the share was successful
                    store_analytics('SIBTTopBarShareSuccess');
                    var iframe = topbar.find('div.iframe iframe');
                    var iframe_div = topbar.find('div.iframe');

                    is_asker = true;

                    iframe_div.fadeOut('fast', function() {
                        topbar.animate({height: '40'}, 500);
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
                    'cursor': 'pointer',
                    'display': 'inline-block'
                });

                // shake ONLY the SIBT button when scrolled into view
                var shaken_yet = false;
                $(w).scroll (function () {
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

                save_product(sibtjs_elem.data());
            }

            // SIBT Connection
            if (sibt_elem.length > 0) { // is the div there?
                console.log('#mini_sibt_button exists');
                store_analytics();

                sibt_elem.click(button_onclick);

                if (has_results) {
                    sibt_elem.css ({
                        'background': "url('{{ URL }}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent",
                        'cursor': 'pointer',
                        'width': '80px'
                    });
                }
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

                save_product(sibt_elem.data());
            }

            // SIBT standalone
            if (!(detect_shopconnection && sibt_elem.length) && // if SIBT can show, and
                purchase_cta.length > 0) {                      // if SIBT *should* show
                console.log('#_willet_shouldIBuyThisButton exists');
                store_analytics();

                // run our scripts
                var hash = w.location.hash;
                var hash_search = '#code=';
                hash_index = hash.indexOf(hash_search);
                willt_code = hash.substring(hash_index + hash_search.length , hash.length);

                {% if app.top_bar_enabled %} // add this topbar code only if necessary
                    console.log('topbar enabled');
                    var cookie_topbar_closed = ($.cookie('_willet_topbar_closed') === 'true');

                    // create the hide button
                    topbar_hide_button = $(d.createElement('div'));
                    topbar_hide_button.attr('id', '_willet_topbar_hide_button')
                        .css('display', 'none')
                        .click(unhide_topbar);

                    if ( show_top_bar_ask ) {
                        topbar_hide_button.html('Get advice!');
                    } else if( is_asker ) {
                        topbar_hide_button.html('See your results!');
                    } else {
                        topbar_hide_button.html('Help {{ asker_name }}!');
                    }

                    $('body').prepend(topbar_hide_button);

                    if (show_top_bar_ask) {
                        if (cookie_topbar_closed) {
                            // user has hidden the top bar
                            topbar_hide_button.slideDown('fast');
                        } else {
                            store_analytics('SIBTShowingTopBarAsk');
                            show_topbar_ask();
                        }
                    }
                {% endif %} ; // app.top_bar_enabled

                {% if app.button_enabled %} // add this button code only if necessary
                    if (sibt_version <= 2) {
                        console.log('v2 button is enabled');
                        var button = d.createElement('a');
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
                    } else if (sibt_version >= 3) { // this should be changed to == 3 if SIBT standalone of a higher version will exist
                        console.log('v3 button is enabled');
                        if ($('#_willet_button_v3').length === 0) { // if the v3 button isn't there already
                            var button = $("<div />", {
                                'id': '_willet_button_v3'
                            });
                            button
                                .html ("<p>Should you buy this? Can\'t decide?</p>" +
                                        "<div class='button' " +
                                            "title='Ask your friends if you should buy this!'>" +
                                            "<img src='{{URL}}/static/plugin/imgs/logo_button_25x25.png' alt='logo' />" +
                                            "<div id='_willet_button' class='title'>Ask Trusted Friends</div>" +
                                         "</div>")
                                .css({'clear': 'both'});
                            $(purchase_cta).append(button);
                        } else {
                            var button = $('#_willet_button_v3');
                        }
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
                            $(w).scroll (function () { // shake ONLY the SIBT button when scrolled into view
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
                {% endif %} // app.button_enabled
            } // if #_willet_shouldIBuyThisButton

            // Load jQuery colorbox
            if (!$.willet_colorbox) {
                manage_script_loading(
                    ['{{ URL }}/s/js/jquery.colorbox.js?' + willet_metadata ()], function () {
                        $.willet_colorbox.init (); // init colorbox last

                        // watch for message; Create IE + others compatible event handler
                        $(w).bind('onmessage message', function(e) {
                            var message = e.originalEvent.data;
                            if (message === 'shared') {
                                ask_success = true;
                            } else if (message === 'close') {
                                $.willet_colorbox.close();
                            }
                        });

                        // auto-show results on hash
                        var hash = w.location.hash;
                        var hash_search = '#open_sibt=';
                        hash_index = hash.indexOf(hash_search);
                        if (has_results && hash_index !== -1) {
                            // if vote has results and voter came from an email
                            console.log("has results?");
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
