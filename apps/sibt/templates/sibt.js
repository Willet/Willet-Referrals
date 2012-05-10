(function (w, d) {
    "use strict";
    /*
     * Willet's "Should I Buy This"
     * Copyright Willet Inc, 2012
     *
     * w and d are aliases of window and document.
     */

    var _willet = w._willet || {};
    {% include "js/willet.mediator.js" %}
    {% include "js/willet.debug.js" %}
    {% include "js/willet.loader.js" %}
    {% include "js/willet.analytics.js" %}
    {% include "js/willet.colorbox.js" %}

    // declare vars
    var app, instance, products, sys, topbar, user;

    // keep track of this many products, max
    var PRODUCT_HISTORY_COUNT = {{ product_history_count|default:10 }};
    var SHAKE_DURATION = 600; // ms
    var SHAKE_WAIT = 700; // ms

    var padding_elem = null;
    var topbar = null;
    var topbar_hide_button = null;

    // CSS rules
    var colorbox_css = '{% spaceless %}{% include "../../plugin/templates/css/colorbox.css" %}{% endspaceless %}';
    var popup_css = '{% spaceless %}{% include "../../plugin/templates/css/popup.css" %}{% endspaceless %}';
    var app_css = '{% spaceless %}{{ app_css }}{% endspaceless %}';

    // WOSIB: get this thing inside the closure
    var _willet_cart_items = _willet_cart_items || w._willet_cart_items || [];

    // load CSS for colorbox as soon as possible!!
    var styles = [app_css, colorbox_css, popup_css];
    for (var i = 0; i < styles.length; i++) {
        _willet.Mediator.fire('loadCSSText', styles[i]);
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
        // true when visitor on page more than (5) times
        'unsure_multi_view': ('{{unsure_multi_view}}' === 'True'),
        'uuid': '{{ app.uuid }}',
        'version': '{{sibt_version|default:"10"}}'
    };
    instance = {
        'has_product': ('{{has_product}}' === 'True'), // product exists in DB?
        'has_results': ('{{has_results}}' === 'True'),
        'is_live': ('{{is_live}}' === 'True'),
        'show_votes': ('{{show_votes}}' === 'True'),
        'uuid': '{{ instance.uuid }}'
    };
    user = {
        'has_voted': ('{{has_voted}}' === 'True'), // did they vote?
        'is_asker': ('{{is_asker}}' === 'True'), // did they ask?
        'uuid': '{{ user.uuid }}'
    };

    // Stores user_uuid for all browsers - differently for Safari.
    var setCookieStorageFlag = function () {
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
        var storageIframeLoaded = false;
        var storageIFrame = d.createElement('iframe');
        storageIFrame.setAttribute('src', "{{URL}}{% url UserCookieSafariHack %}");
        storageIFrame.setAttribute('id', "sessionFrame");
        storageIFrame.setAttribute('name', "sessionFrame");
        storageIFrame.setAttribute('onload', "doSafariCookieStorage();");
        storageIFrame.onload = storageIFrame.onreadystatechange = function() {
            var rs = this.readyState;
            if(rs && rs !== 'complete' && rs !== 'loaded') return;
            if(storageIframeLoaded) return;
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

        holder.appendChild(storageIFrame);
        storageForm.appendChild( storageInput );
        holder.appendChild(storageForm);
        d.body.appendChild(holder);
    } else {
        setCookieStorageFlag();
    }

    // Once all dependencies are loading, fire this function
    _willet.Mediator.on('scriptsReady', function () {

        if (sys.$_conflict) {
            jQuery.noConflict(); // Suck it, Prototype!
        }

        // wait for DOM elements to appear + $ closure!
        jQuery(d).ready(function($) {
            _willet.Mediator.fire('hasjQuery', $);  // not currently handled

            // jQuery shaker plugin
            (function(a){var b={};var c=5;a.fn.shaker=function(){b=a(this);b.css("position","relative");b.run=true;b.find("*").each(function(b,c){a(c).css("position","relative")});var c=function(){a.fn.shaker.animate(a(b))};setTimeout(c,25)};a.fn.shaker.animate=function(c){if(b.run==true){a.fn.shaker.shake(c);c.find("*").each(function(b,c){a.fn.shaker.shake(c)});var d=function(){a.fn.shaker.animate(c)};setTimeout(d,25)}};a.fn.shaker.stop=function(a){b.run=false;b.css("top","0px");b.css("left","0px")};a.fn.shaker.shake=function(b){var d=a(b).position();a(b).css("left",d["left"]+Math.random()<.5?Math.random()*c*-1:Math.random()*c)}})($);

            // jQuery cookie plugin (included to solve lagging requests)
            {% include '../../plugin/templates/js/jquery.cookie.js' %}

            var cleanArray = function (actual) {
                var i;
                var new_array = [];
                for(i = 0; i < actual.length; i++) {
                    if (Boolean(actual[i]) === true) {
                        new_array.push(actual[i]);
                    }
                }
                return new_array;
            };

            var randomString = function () {
                //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
                return String((new Date()).getTime()).replace(/\D/gi,'');
            };

            var isScrolledIntoView = function (elem) {
                // http://stackoverflow.com/questions/487073
                // returns true if elem has dimensions within the viewport.
                var docViewTop = $(w).scrollTop();
                var docViewBottom = docViewTop + $(w).height();
                var elemTop = $(elem).offset().top;
                var elemBottom = elemTop + $(elem).height();
                return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
            };

            var getCanonicalURL = function (default_url) {
                // Tries to retrieve a canonical link from the header
                // Otherwise, returns default_url
                var links = d.getElementsByTagName('link'),
                    i = links.length;
                while (i--) {
                    if (links[i].rel === 'canonical' && links[i].href) {
                        return links[i].href;
                    }
                }
                return default_url;
            };

            var getLargestImage = function (within) {
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

            var getPageTitle = function () {
                return d.title || '';
            };

            var getProductUUIDs = function () {
                // currently, products are just their UUIDs (to save space)
                return cleanArray(products);
            };

            var metadata = function (more) {
                // constructs the 'willet' query string - no prefixing ?
                // will be added for you.
                // add more query properties with the "more" param.
                return $.param($.extend (
                    {}, // blank original
                    {
                        'app_uuid': '{{ app.uuid }}',
                        'user_uuid': '{{ user.uuid }}',
                        'instance_uuid': '{{ instance.uuid }}',
                        'store_url': '{{ store_url }}', // registration url
                        'target_url': '{{ page_url }}' || getCanonicalURL(w.location.href) // window.location
                    },
                    more || {}
                ));
            };

            // Send action to server
            var storeAnalytics = function (message) {
                _willet.Mediator.fire('storeAnalytics', message);
            };

            // Called when ask iframe is closed
            var ask_callback = function( fb_response ) {
                if (ask_success) {
                    user.is_asker = true;
                    $('#_willet_button').html('Refresh the page to see your results!');
                }
            };

            var button_onclick = function(e, message) {
                var message = message || 'SIBTUserClickedButtonAsk';
                $('#_willet_padding').hide();
                if (user.is_asker || instance.show_votes) {
                    // we are no longer showing results with the topbar.
                    showResults();
                } else {
                    storeAnalytics(message);
                    showAsk();
                }
            };

            var showColorbox = function (options) {
                storeAnalytics('showColorbox');
                var defaults = {
                    transition: 'fade',
                    close: '',
                    scrolling: false,
                    iframe: true,
                    initialWidth: 0,
                    initialHeight: 0,
                    innerWidth: '600px',
                    innerHeight: '420px',
                    fixed: true,
                    onClosed: function () {}
                };
                options = $.extend({}, defaults, options);
                _willet.Mediator.fire('openColorbox', options);
            }

            var showResults = function () {
                storeAnalytics('showResults');
                // show results if results are done.
                // this can be detected if a finished flag is raised.
                showColorbox({
                    href: "{{URL}}/s/results.html?" +
                           metadata({
                               'refer_url': getCanonicalURL(w.location.href)
                           })
                });
            };

            var showAsk = function (message) {
                // shows the ask your friends iframe
                storeAnalytics('showAsk');
                var shopify_ids = [];
                if (_willet_cart_items) {
                    // WOSIB exists on page; send extra data
                    for (var i = 0; i < _willet_cart_items.length; i++) {
                        shopify_ids.push(_willet_cart_items[i].id);
                    }
                }

                _willet.Mediator.fire('log', shopify_ids);
                _willet.Mediator.fire('log', products);

                return showColorbox({
                    href: "{{URL}}{% url AskDynamicLoader %}" +
                        // do not merge with metadata(): it escapes commas
                        "?products=" + getProductUUIDs().join(',') +
                        "&ids=" + shopify_ids.join(',') +
                        "&" + metadata()
                });

                // else if no products: do nothing
                _willet.Mediator.fire('log', "no products! cancelling dialogue.");
            };

            var addScrollShaking = function (elem) {
                var $elem = $(elem);
                $(w).scroll(function () {
                    if (isScrolledIntoView($elem) && !$elem.data('shaken_yet')) {
                        setTimeout(function () {
                            $elem.shaker();
                            setTimeout(function () {
                                $elem.shaker.stop();
                                $elem.data('shaken_yet', true);
                            }, SHAKE_DURATION);
                        }, SHAKE_WAIT); // wait for ?ms until it shakes
                    }
                });
            }

            var updateProductHistory = function () {
                // save past products' images
                // check if page is visited twice or more in a row
                if (getLargestImage() !== $.cookie('product1_image') &&
                    getLargestImage() !== $.cookie('product2_image')) {
                    // image 1 is more recent; shift products
                    $.cookie('product2_image', $.cookie('product1_image'));
                    $.cookie('product1_image', getLargestImage());
                }

                // load product currently on page
                var ptemp = $.cookie('products') || '';
                _willet.Mediator.fire('log', "read product cookie, got " + ptemp);
                products = ptemp.split(','); // load
                if ($.inArray("{{product.uuid}}", products) === -1) { // unique
                    products.unshift("{{product.uuid}}"); // insert as products[0]
                    products = products.splice(0, PRODUCT_HISTORY_COUNT); // limit count (to 4kB!)
                    products = cleanArray(products); // remove empties
                    $.cookie('products', products.join(',')); // save
                    _willet.Mediator.fire('log', "saving product cookie " + products.join(','));
                } else {
                    _willet.Mediator.fire('log', "product already in cookie");
                }
                return products;
            };

            var saveProduct = function(fill) {
                // auto-create product objects using page info, using
                // (<div class='_willet_...' data-....>) or otherwise
                // server decides if the input supplied is good to save.
                // does not guarantee saving; no return value; asynchronous.

                // 2012-05-08: hit max HTTP GET length; minimizing request length.
                try {
                    // do NOT send .data() directly! Will cause unexpected func calls.

                    // boolean test if empty
                    // product_title and product_description are json dumps, so
                    // they already come with their own double quotes.
                    if ({{ product_title }} || {{ product_description }}) {
                        _willet.Mediator.fire('log', 'product already in DB, it seems.');
                        return;
                    }

                    var data = {
                        'client_uuid': fill.client_uuid || '{{ client.uuid }}', // REQUIRED
                        'sibtversion': fill.sibtversion || app.version,
                        'title': fill.title || getPageTitle(),
                        'image': fill.image || getLargestImage(d),
                        'resource_url': '{{ page_url }}' || getCanonicalURL(w.location.href)
                    };

                    // optional fields
                    if (fill.description) {
                        data.description = fill.description;
                    }
                    if (fill.images) {
                        data.images = fill.images;
                    }
                    if (fill.price) {
                        data.price = fill.price;
                    }
                    if (fill.tags) {
                        data.tags = fill.tags;
                    }
                    if (fill.type) {
                        data.type = fill.type;
                    }
                    if (data.client_uuid) {
                        // Chrome Access-Control-Allow-Origin: must use GET here.
                        $('<img />', {
                            src: '{{URL}}{% url CreateProduct %}?' + $.param(data),
                            css: {'display':'none'}
                        }).appendTo(d);
                        _willet.Mediator.fire('log', 'sent product request');
                    }
                } catch (e) {
                    _willet.Mediator.fire('log', e.message);
                }
            };


            {% if app.top_bar_enabled %} // add this topbar code only if necessary
                {% include 'sibt_topbar_funcs.inc.js' %}
            {% endif %} ; // app.top_bar_enabled


            // Check page and load requested SIBT styles.
            var sibt_elem = $('#mini_sibt_button').eq(0); // SIBT for ShopConnection (SIBT Connection)
            var purchase_cta = $('#_willet_shouldIBuyThisButton').eq(0); // SIBT standalone (v2, v3)
            var sibtjs_elem = $('._willet_sibt').eq(0); // SIBT-JS
            var wosib_elem = $('#_willet_WOSIB_Button'); // WOSIB mode

            // combine current product with past products history from cookie
            // products can be read from func return or just the var, products
            updateProductHistory();

            // SIBT-JS
            if (sibtjs_elem.length > 0) { // is the div there?
                _willet.Mediator.fire('log', 'at least one ._willet_sibt exists');
                storeAnalytics();
                sibtjs_elem.click(button_onclick);
                sibtjs_elem.css ({
                    'background': ((instance.is_live || instance.has_results)?
                                    "url('{{URL}}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent":
                                    "url('{{URL}}/static/sibt/imgs/button_bkg.png') 3% 20% no-repeat transparent"),
                    'width': '80px',
                    'height': '21px',
                    'cursor': 'pointer',
                    'display': 'inline-block'
                });

                if (!instance.has_product) {
                    // if no product, try to detect one, but don't show button
                    _willet.Mediator.fire('log', "product does not exist here; hiding button.");
                    sibtjs_elem.css ({
                        'display': 'none'
                    });
                }

                // shake ONLY the SIBT button when scrolled into view
                addScrollShaking(sibtjs_elem);
                saveProduct(sibtjs_elem.data());
            }

            // SIBT Connection
            if (sibt_elem.length > 0) { // is the div there?
                _willet.Mediator.fire('log', '#mini_sibt_button exists');
                storeAnalytics();

                sibt_elem
                    .css('height', '20px')
                    .click(button_onclick);

                if (instance.is_live || instance.has_results) {
                    sibt_elem.css ({
                        'background': "url('{{URL}}/static/sibt/imgs/button_bkg_see_results.png') 3% 20% no-repeat transparent",
                        'cursor': 'pointer',
                        'width': '80px'
                    });
                }

                if (!instance.has_product) {
                    // if no product, try to detect one, but don't show button
                    _willet.Mediator.fire('log', "product does not exist here; hiding button.");
                    sibt_elem.css ({
                        'display': 'none'
                    });
                }

                // shake ONLY the SIBT button when scrolled into view
                addScrollShaking(sibt_elem);
                saveProduct(sibt_elem.data());
            }

            // WOSIB
            // requires _willet_cart_items to be present in global scope
            // (a sign that the WOSIB snippet ran on this page)
            if (wosib_elem.length > 0 && _willet_cart_items) {
                // add the button onto the page right now
                storeAnalytics('WOSIB');
                var button = $("<div />", {
                        'id': '_willet_button_v3'
                    });
                    button.html("<p>Which ones should you buy?</p>\
                                 <div id='_willet_button' class='button' \
                                      title='Ask your friends if you should buy this!'>\
                                   <img alt='logo' src='{{URL}}/static/plugin/imgs/logo_button_25x25.png' />\
                                   <div class='title'>Ask Trusted Friends</div>\
                                 </div>")
                    .css({
                        'clear': 'both',
                        'display': 'inline-block'
                    })
                    .appendTo(wosib_elem);

                $('#_willet_button').click(showAsk);
                storeAnalytics("WOSIBShowingButton"); // log show button

                // if server sends a flag that indicates "results available"
                // (not necessarily "finished") then show finished button
                if (instance.is_live || instance.has_results) {
                    $('#_willet_button').hide();
                    $('<div />', {
                        'id': "_willet_WOSIB_results",
                        'class': "button"
                    })
                    .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                    .appendTo(button)
                    .css({
                        'display': 'inline-block'
                    })
                    .click(showResults);
                }
            }

            // SIBT standalone
            if (!(app.detect_shopconnection && sibt_elem.length) && // if SIBT can show, and
                purchase_cta.length > 0) {                      // if SIBT *should* show
                _willet.Mediator.fire('log', '#_willet_shouldIBuyThisButton exists');
                storeAnalytics();

                // run our scripts
                var hash = w.location.hash;
                var hash_search = '#code=';
                var hash_index = hash.indexOf(hash_search);
                var willt_code = hash.substring(hash_index + hash_search.length , hash.length);

                var v3data = purchase_cta.data();
                try {
                    saveProduct({
                        'title': v3data.title || false,
                        'image': v3data.image_url || false
                    });
                } catch (e) {
                    _willet.Mediator.fire('log', "failed to let v3 button save product!");
                }

                // if no product, try to detect one, but don't show button
                if (instance.has_product) {
                    {% if app.top_bar_enabled %} // add this topbar code only if necessary
                        storeAnalytics('topbarEnabled');
                        _willet.Mediator.fire('log', 'topbar enabled');

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
                                storeAnalytics('SIBTShowingTopBarAsk');
                                show_topbar_ask();
                            }
                        }
                    {% endif %} ; // app.top_bar_enabled

                    {% if app.button_enabled %} // add this button code only if necessary
                        storeAnalytics('buttonEnabled');
                        if (parseInt(app.version) <= 2) {
                            _willet.Mediator.fire('log', 'v2 button is enabled');
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
                        } else if (parseInt(app.version) >= 3) { // this should be changed to == 3 if SIBT standalone of a higher version will exist
                            _willet.Mediator.fire('log', 'v3+ button is enabled');
                            if ($('#_willet_button_v3').length === 0) { // if the v3 button isn't there already
                                var button = $("<div />", {
                                    'id': '_willet_button_v3'
                                });
                                button
                                    .html ("<p>Should you buy this? Can't decide?</p>" +
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
                            if (instance.is_live || instance.has_results) {
                                $('#_willet_button_v3 .button').hide ();
                                $('<div />', {
                                    'id': "_willet_SIBT_results",
                                    'class': "button"
                                })
                                .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                                .appendTo(button)
                                .css('display', 'inline-block')
                                .click (showResults);
                            }

                            var $wbtn = $('#_willet_button_v3 .button');
                            if ($wbtn.length > 0) {
                                $wbtn = $($wbtn[0]);
                            }
                            addScrollShaking($wbtn);
                        }
                    {% endif %} // app.button_enabled
                } else {
                    _willet.Mediator.fire('log', "product does not exist here; hiding button.");
                }
            } // if #_willet_shouldIBuyThisButton

            {% if app.bottom_popup_enabled %}
                _willet.Mediator.fire('log', "bottom_popup_enabled! yay!");

                var buildBottomPopup = function () {
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
                if ($.cookie('product1_image') &&
                    $.cookie('product2_image') &&
                    app.unsure_multi_view) {
                    _willet.Mediator.fire('log', 'bottom popup enabled');
                    var clickedOff = false;

                    var popup = buildBottomPopup();
                    var showPopup = function () {
                        storeAnalytics('showPopup');
                        popup.fadeIn('slow');
                    };
                    var hidePopup = function () { popup.fadeOut('slow'); };

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
                        var pageHeight, scrollPos, threshold, windowHeight;

                        pageHeight = $(d).height();
                        scrollPos = $(w).scrollTop() + $(w).height();
                        threshold = pageHeight * app.bottom_popup_trigger;
                        windowHeight = $(w).height();

                        // popup will show only for pages sufficiently long.
                        if (pageHeight > windowHeight * 1.5) {
                            storeAnalytics('popupEnabled');
                            if (scrollPos >= threshold) {
                                if (!popup.is(':visible') && !clickedOff) {
                                    showPopup();
                                }
                            } else {
                                if (popup.is(':visible')) {
                                    hidePopup();
                                }
                            }
                        } else {
                            _willet.Mediator.fire('log', "page too short");
                            storeAnalytics('popupDisabled.pageHeight');
                        }
                    });
                    $('#willet_sibt_popup .cta').click(function () {
                        showAsk();
                        hidePopup();
                    });
                    $('#willet_sibt_popup #anti_cta').click(function (e) {
                        clickedOff = true;
                        e.preventDefault();
                        hidePopup();
                    });
                } else {
                    storeAnalytics('popupDisabled.unsureFailed');
                    _willet.Mediator.fire(
                        'log',
                        'did not activate bottom popup because: ' +
                        [
                            Boolean($.cookie('product1_image')),
                            Boolean($.cookie('product2_image')),
                            app.unsure_multi_view
                        ]
                    );
                }
            {% endif %} ; // app.bottom_popup_enabled

            // auto-show results on hash
            var hash = window.location.hash;
            var hash_search = '#open';
            var hash_index = hash.indexOf(hash_search);
            if (instance.has_results && hash_index !== -1) {
                // if vote has results and voter came from an email
                _willet.Mediator.fire('log', "has results?");
                showResults();
            }

            // analytics to record the amount of time this script has been loaded
            // this must be an iframe to time it + send synchronous requests
            $('<iframe />', {
                css: {'display': 'none'},
                src: "{{URL}}{% url ShowOnUnloadHook %}?" +
                      metadata({'evnt': 'SIBTVisitLength'})
            }).appendTo("body");
        });
    });

    // Go time! Load script dependencies
    try {
        // set up a list of scripts to load asynchronously.
        var scripts_to_load = [
            '{{ URL }}{% url SIBTShopifyServeAB %}?jsonp=1&store_url={{ store_url }}',  // AB call to action text
            ('https:' == d.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js' // Google analytics
        ];

        // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        if (!w.jQuery || w.jQuery.fn.jquery < "1.4.0") {
            scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js');
        }

        _willet.Mediator.fire('loadJS', {
            'scripts': scripts_to_load,
            'callback': _willet.Mediator.callback('scriptsReady')
        });
    } catch (e) {
        var error   = encodeURIComponent("SIBT Error");
        var line    = e.number || e.lineNumber || "Unknown";
        var script  = encodeURIComponent("sibt.js: " + line);
        var message = e.stack || e.toString();
        var st      = encodeURIComponent(message);
        var params  = "error=" + error + "&script=" + script + "&st=" + st;
        var err_img = d.createElement("img");
        err_img.src = "{{URL}}{% url ClientSideMessage %}?" + params;
        err_img.style.display = "none";
        d.body.appendChild(err_img);

        _willet.Mediator.fire('log', "Error:", line, message);
    }
})(window, document);
