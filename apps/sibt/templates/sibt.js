(function (w, d) {
    "use strict";
    /*
     * Willet's "Should I Buy This"
     * Copyright Willet Inc, 2012
     *
     * This script serves SIBTShopify, SIBT Connection (SIBT in ShopConnection),
     * and SIBT-JS (for outside Shopify).
     *
     * w and d are aliases of window and document.
     */

    // declare vars
    var app, instance, products, sys, topbar, user;

    var hash_index = -1;
    var padding_elem = null;
    var PRODUCT_HISTORY_COUNT = {{ product_history_count|default:10 }}; // keep track of this many products, max
    var topbar = null;
    var topbar_hide_button = null;
    var willt_code = null;
    // CSS rules (except colorbox_css, which includes its own 'quotes';)
    var colorbox_css = '{% include "../../plugin/templates/css/colorbox.css" %}';
    var popup_css = '{% include "../../plugin/templates/css/popup.css" %}';
    var app_css = '{{ app_css }}';

    // set up a list of scripts to load asynchronously.
    var scripts_to_load = ['{{URL}}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}'];
    // turns out we need at least 1.4 for the $(<tag>,{props}) notation
    if (!w.jQuery || w.jQuery.fn.jquery < "1.4.0") { // str comparison is OK
        scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js');
    }

    // These ('???' === 'True') guarantee missing tag, ('' === 'True') = false
    sys = {
        'debug': ('{{debug}}' === 'True'),
        '$_conflict': !(w.$ && w.$.fn && w.$.fn.jquery)
    };
    app = {
        // true when SIBT needs to be disabled on the same page as Buttons
        'bottom_popup_trigger': 0.5, // 1.0 = bottom of page
        'detect_shopconnection': ('{{detect_shopconnection}}' === 'True'),
        'features': {
            'bottom_popup': ('{{app.bottom_popup_enabled}}' === 'True'),
            'button': ('{{app.button_enabled}}' === 'True'),
            'topbar': ('{{app.top_bar_enabled}}' === 'True')
        },
        'show_top_bar_ask': ('{{show_top_bar_ask}}' === 'True'),
        // true when visitor on page more than (4 times)
        'unsure_multi_view': ('{{unsure_multi_view}}' === 'True'),
        'version': {{sibt_version|default:"11"}}
    };
    instance = {
        'has_results': ('{{has_results}}' === 'True'),
        'is_live': ('{{is_live}}' === 'True'),
        'show_votes': ('{{show_votes}}' === 'True')
    };
    user = {
        'has_voted': ('{{has_voted}}' === 'True'), // did they vote?
        'is_asker': ('{{is_asker}}' === 'True') // did they ask?
    };

    try { // debug if available
        if (sys.debug) {
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
        var i, scripts_not_ready;
        i = scripts_not_ready = scripts.length;
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
        storageForm.setAttribute('action', "{{URL}}{% url UserCookieSafariHack %}");
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

    // Once all dependencies are loading, fire this function
    var init = function () {

        // load CSS for colorbox as soon as possible!!
        var styles = colorbox_css + popup_css + app_css;
        var willet_style = d.createElement('style');
        var head_elem = d.getElementsByTagName('head')[0];
            willet_style.type = 'text/css';
            willet_style.setAttribute('charset','utf-8');
            willet_style.setAttribute('media','all');
        if (willet_style.styleSheet) {
            willet_style.styleSheet.cssText = styles;
        } else {
            willet_style.appendChild(d.createTextNode(styles));
        }
        head_elem.appendChild(willet_style);

        if (sys.$_conflict) {
            jQuery.noConflict(); // Suck it, Prototype!
        }

        // wait for DOM elements to appear + $ closure!
        jQuery(d).ready(function($) {

            // jQuery shaker plugin
            (function(a){var b={};var c=5;a.fn.shaker=function(){b=a(this);b.css("position","relative");b.run=true;b.find("*").each(function(b,c){a(c).css("position","relative")});var c=function(){a.fn.shaker.animate(a(b))};setTimeout(c,25)};a.fn.shaker.animate=function(c){if(b.run==true){a.fn.shaker.shake(c);c.find("*").each(function(b,c){a.fn.shaker.shake(c)});var d=function(){a.fn.shaker.animate(c)};setTimeout(d,25)}};a.fn.shaker.stop=function(a){b.run=false;b.css("top","0px");b.css("left","0px")};a.fn.shaker.shake=function(b){var d=a(b).position();a(b).css("left",d["left"]+Math.random()<.5?Math.random()*c*-1:Math.random()*c)}})($);
            // jQuery cookie plugin (included to solve lagging requests)
            {% include '../../plugin/templates/js/jquery.cookie.js' %}
            
            // jQuery image derpdown plugin (shows image dropdown box)
            {% include '../../plugin/templates/js/jquery.imagedropdown.js' %}

            var metadata = function (more) {
                // constructs the 'willet' query string - no prefixing ? will be added for you.
                // add more query properties with the "more" param.
                return $.param($.extend (
                    {}, // blank original
                    {
                        'app_uuid': '{{ app.uuid }}',
                        'user_uuid': '{{ user.uuid }}',
                        'instance_uuid': '{{ instance.uuid }}',
                        'target_url': '{{ PAGE }}' || w.location.href
                    },
                    more || {}
                ));
            };

            var clean_array = function (actual) {
                var i;
                var new_array = [];
                for(i = 0; i < actual.length; i++) {
                    if (!!actual[i]) {
                        new_array.push(actual[i]);
                    }
                }
                return new_array;
            };

            var random_string = function () {
                //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
                return String((new Date()).getTime()).replace(/\D/gi,'');
            }

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
                within = within || d; // defaults to document
                var nMaxDim = 0;
                var largest_image = '';
                $(within).find('img').each(function () {
                    var $this = $(this);
                    var nDim = parseFloat($this.width()) * parseFloat($this.height());
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

            var get_product_uuids = function () {
                // currently, products are just their UUIDs (to save space)
                return clean_array(products);
            }

            // Send action to server
            var store_analytics = function (message) {
                var message = message || '{{ evnt }}';
                var random_id = 'a' + random_string();

                $('<iframe />', {
                    id: random_id,
                    name: random_id,
                    css: {'display': 'none'},
                    src: "{{URL}}{% url TrackSIBTShowAction %}?evnt=" +
                          encodeURIComponent(message) + "&" + metadata(),
                    load: function () {
                        try {
                            var iframe_handle = d.getElementById(random_id);
                            iframe_handle.parentNode.removeChild (iframe_handle);
                        } catch (e) {
                            console.log(e.message);
                        }
                    }
                }).appendTo("body");
            };

            var button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                $('#_willet_padding').hide();
                if (user.is_asker || instance.show_votes) {
                    // we are no longer showing results with the topbar.
                    show_results();
                } else {
                    store_analytics(message);
                    show_ask();
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
                    innerWidth: '620px',
                    innerHeight: '460px',
                    fixed: true,
                    onClosed: function () {}
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
                           metadata({'refer_url': w.location.href})
                });
            };

            var show_ask = function (message) {
                // shows the ask your friends iframe
                show_colorbox({
                    href: "{{URL}}{% url AskDynamicLoader %}" +
                          "?products=" + get_product_uuids().join(',') +
                          "&" + metadata()
                });
            };

            var add_scroll_shaking = function (elem) {
                var $elem = $(elem);
                $(w).scroll(function () {
                    if (is_scrolled_into_view($elem) && !$elem.data('shaken_yet')) {
                        setTimeout(function () {
                            $elem.shaker();
                            setTimeout(function () {
                                $elem.shaker.stop();
                                $elem.data('shaken_yet', true);
                            }, 600); // shake duration
                        }, 700); // wait for ?ms until it shakes
                    }
                });
            }

            var update_product_history = function () {
                // save past products' images
                // check if page is visited twice or more in a row
                if (get_largest_image() !== $.cookie('product1_image') &&
                    get_largest_image() !== $.cookie('product2_image')) {
                    // image 1 is more recent; shift products
                    $.cookie('product2_image', $.cookie('product1_image'));
                    $.cookie('product1_image', get_largest_image());
                }

                // load product currently on page
                var ptemp = $.cookie('products') || '';
                products = ptemp.split(','); // load
                if ($.inArray("{{product.uuid}}", products) === -1) { // unique
                    products.push("{{product.uuid}}"); // insert as products[0]
                    products.splice(PRODUCT_HISTORY_COUNT); // limit count (to 4kB!)
                    products = clean_array(products); // remove empties
                    $.cookie('products', products.join(',')); // save
                }
                return products;
            };

            var save_product = function(data) {
                // auto-create product objects using page info, using
                // (<div class='_willet_...' data-....>) or otherwise
                // server decides if the input supplied is good to save.
                // does not guarantee saving; no return value; asynchronous.
                try {
                    // do NOT send .data() directly! Will cause unexpected func calls.
                    var data = {
                        'client_uuid': data.client_uuid || '{{ client.uuid }}', // REQUIRED
                        'sibtversion': data.sibtversion || app.version,
                        'title': data.title || '{{ product.title }}' || get_page_title(),
                        'description': data.description || '{{ product.description }}',
                        'images': data.images || '',
                        'image': data.image || get_largest_image(d),
                        'price': data.price || '0.0',
                        'tags': data.tags || '',
                        'type': data.type || '',
                        'resource_url': '{{ PAGE }}' || w.location.href
                    };
                    if (data.client_uuid) {
                        $.ajax({
                            url: '{{URL}}{% url CreateProduct %}',
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
                {% include 'sibt_topbar_funcs.inc.js' %}
            {% endif %} ; // app.top_bar_enabled


            // Check page and load requested SIBT styles.
            var sibt_elem = $('#mini_sibt_button').eq(0); // SIBT for ShopConnection (SIBT Connection)
            var purchase_cta = $('#_willet_shouldIBuyThisButton').eq(0); // SIBT standalone (v2, v3)
            var sibtjs_elem = $('._willet_sibt').eq(0); // SIBT-JS

            // combine current product with past products history from cookie
            // products can be read from func return or just the var, products
            update_product_history();

            // SIBT-JS
            if (sibtjs_elem.length > 0) { // is the div there?
                console.log('at least one ._willet_sibt exists');
                store_analytics();

                sibtjs_elem.click(button_onclick);
                sibtjs_elem.css ({
                    'background': (instance.has_results?
                                    "url('{{URL}}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent":
                                    "url('{{URL}}/static/sibt/imgs/button_bkg.png') 3% 20% no-repeat transparent"),
                    'width': '80px',
                    'height': '21px',
                    'cursor': 'pointer',
                    'display': 'inline-block'
                });

                // shake ONLY the SIBT button when scrolled into view
                add_scroll_shaking(sibtjs_elem);
                save_product(sibtjs_elem.data());
            }

            // SIBT Connection
            if (sibt_elem.length > 0) { // is the div there?
                console.log('#mini_sibt_button exists');
                store_analytics();

                sibt_elem.click(button_onclick);

                if (instance.has_results) {
                    sibt_elem.css ({
                        'background': "url('{{URL}}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent",
                        'cursor': 'pointer',
                        'width': '80px'
                    });
                }
                // shake ONLY the SIBT button when scrolled into view
                add_scroll_shaking(sibt_elem);
                save_product(sibt_elem.data());
            }

            // SIBT standalone
            if (!(app.detect_shopconnection && sibt_elem.length) && // if SIBT can show, and
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
                    
                    if (app.show_top_bar_ask) {
                        topbar_hide_button.html('Get advice!');
                    } else if(user.is_asker) {
                        topbar_hide_button.html('See your results!');
                    } else {
                        topbar_hide_button.html('Help {{ asker_name }}!');
                    }

                    $('body').prepend(topbar_hide_button);

                    if (app.show_top_bar_ask) {
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
                    if (app.version <= 2) {
                        console.log('v2 button is enabled');
                        var button = d.createElement('a');
                        var button_html = '';
                        // only add button if it's enabled in the app 
                        if (user.is_asker) {
                            button_html = 'See what your friends said!';
                        } else if (instance.show_votes) {
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
                    } else if (app.version >= 3) { // this should be changed to == 3 if SIBT standalone of a higher version will exist
                        console.log('v3+ button is enabled');
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
                        if (instance.has_results) {
                            $('#_willet_button_v3 .button').hide ();
                            $('<div />', {
                                'id': "_willet_SIBT_results",
                                'class': "button"
                            })
                            .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                            .appendTo(button)
                            .css('display', 'inline-block')
                            .click (show_results);
                        }
                        
                        var $wbtn = $('#_willet_button_v3 .button');
                        if ($wbtn.length > 0) {
                            $wbtn = $($wbtn[0]);
                        }
                        add_scroll_shaking($wbtn);
                    }
                {% endif %} // app.button_enabled
            } // if #_willet_shouldIBuyThisButton

            {% if app.bottom_popup_enabled %}
                var build_bottom_popup = function () {
                    var AB_CTA_text = AB_CTA_text || 'Ask your friends for advice!'; // AB lag
                    var popup = $('<div />', {
                        'id': 'willet_sibt_popup',
                        'css': {'display': 'none'}
                    });
                    popup
                        .append('<h2 class="title">Hey! Need help deciding?</h2>')
                        .append($('<div />', {'id': 'product_selector'}))
                        .append(
                            '<button class="cta">' + AB_CTA_text + '</button>' +
                            '<a id="anti_cta" href="#">No thanks</a>'
                        );
                    return popup;
                }

                // if user visited at least two different product pages
                if ($.cookie('product1_image') && $.cookie('product2_image')) {
                    console.log('bottom popup enabled');
                    var clickedOff = false;

                    var popup = build_bottom_popup();
                    var show_popup = function () { popup.fadeIn('slow'); };
                    var hide_popup = function () { popup.fadeOut('slow'); };

                    var product1_image = $.cookie('product1_image') || '';
                    var product2_image = $.cookie('product2_image') || '';
                    $('body').prepend(popup);
                    $('#product_selector').append(
                        '<img class="quote" src="{{URL}}/static/imgs/quote-up.png" />' +
                        '<div class="product">' +
                            '<img class="image" src="' + product1_image + '" />' +
                        '</div>' +
                        '<span class="or">OR</span>' +
                        '<div class="product">' +
                            '<img class="image" src="' + product2_image + '"/>' +
                        '</div>' +
                        '<img class="quote down" src="{{URL}}/static/imgs/quote-down.png" />'
                    );

                    $(w).scroll(function () {
                        var pageHeight, scrollPos, threshold;

                        pageHeight = $(d).height();
                        scrollPos = $(w).scrollTop() + $(w).height();
                        threshold = pageHeight * app.bottom_popup_trigger;

                        if (scrollPos >= threshold) {
                            if (!popup.is(':visible') && !clickedOff) {
                                show_popup();
                            }
                        } else {
                            if (popup.is(':visible')) {
                                hide_popup();
                            }
                        }
                    });
                    $('#willet_sibt_popup .cta').click(function () {
                        console.log('did something');
                        show_ask();
                        hide_popup();
                    });
                    $('#willet_sibt_popup #anti_cta').click(function (e) {
                        clickedOff = true;
                        e.preventDefault();
                        hide_popup();
                    });
                } else {
                    console.log('cookies not populated yet');
                }
            {% endif %} ; // app.bottom_popup_enabled

            // Load jQuery colorbox last
            if (!$.willet_colorbox) {
                $.getScript('{{URL}}/s/js/jquery.colorbox.js?' + metadata(), function () {
                    $.willet_colorbox.init(); // init colorbox last

                    // watch for message; Create IE + others compatible event handler
                    $(w).bind('onmessage message', function(e) {
                        if (e.originalEvent.data === 'close') {
                            $.willet_colorbox.close();
                        }
                    });

                    // auto-show results on hash
                    var hash = w.location.hash;
                    var hash_search = '#open_sibt=';
                    hash_index = hash.indexOf(hash_search);
                    if (instance.has_results && hash_index !== -1) {
                        // if vote has results and voter came from an email
                        console.log("has results?");
                        show_results();
                    }
                });
            }

            // analytics to record the amount of time this script has been loaded
            $('<iframe />', {
                css: {'display': 'none'},
                src: "{{URL}}{% url ShowOnUnloadHook %}?" +
                      metadata({'evnt': 'SIBTVisitLength'})
            }).appendTo("body");
        });
    };

    // Go time! Load script dependencies
    manage_script_loading(scripts_to_load, init);
})(window, document);