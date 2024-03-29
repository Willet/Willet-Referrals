var _willet = _willet || {};  // ensure namespace is there

// Should I Buy This
// requires server-side template vars:
// - app
// - asker_name
// - asker_pic
// - has_product
// - has_voted
// - instance
// - is_asker
// - page_url
// - product
// - product_description
// - product_history_count
// - product_title
// - show_top_bar_ask
// - sibt_version
// - store_id
// - store_url
// - unsure_multi_view
// - URL
// - vendor

// requires modules:
// - storage (localStorage)

// The hasjQuery event starts off automatic initialisation.
// product_title and product_description django tags require their own
// double quotes!
_willet.sibt = (function (me) {
    var wm = _willet.mediator || {};
    var $ = window.jQuery || {};  // I want jQuery here, but it won't be available
                                  // until mediator says so.

    _willet.storage || function () {  // something twitter does
        var moduleMethods = ["get", "set", "del"];
        _willet.storage = {};
        for (var i = 0; i < moduleMethods.length; ++i) {
            _willet.storage[moduleMethods[i]] = function () {};
        }
    }();

    var SMALL_SIBT = 1, LARGE_SIBT = 2,
        SMALL_WOSIB = 3, LARGE_WOSIB = 4,
        SMALL_SIBT_VENDOR = 5, LARGE_SIBT_VENDOR = 6,
        selectors = {
            '#mini_sibt_button': SMALL_SIBT, // SIBT for ShopConnection (SIBT Connection)
            '#_willet_shouldIBuyThisButton': LARGE_SIBT, // SIBT standalone (v2, v3, v10)
            '#_vendor_shouldIBuyThisButton': LARGE_SIBT_VENDOR,
            '._willet_sibt': SMALL_SIBT, // SIBT-JS
            '._vendor_sibt': SMALL_SIBT_VENDOR,
            '#_willet_WOSIB_Button': LARGE_WOSIB // WOSIB mode
        },
        cart_items = cart_items || window._willet_cart_items || [],
        PRODUCT_HISTORY_COUNT = {{ product_history_count|default:10 }};

    // declare vars in this scope
    var popup, products;

    // These ('???' === 'True') guarantee missing tag, ('' === 'True') = false
    var app = {
        // true when SIBT needs to be disabled on the same page as Buttons
        'bottom_popup_trigger': 0.5, // 1.0 = bottom of page
        'features': {
            'bottom_popup': ('{{app.bottom_popup_enabled}}' === 'True'),
            'button': ('{{app.button_enabled}}' === 'True'),
            'topbar': ('{{app.top_bar_enabled}}' === 'True')
        },
        'show_top_bar_ask': ('{{show_top_bar_ask}}' === 'True'),
        // true when visitor on page more than (3) times
        'unsure_multi_view': ('{{unsure_multi_view}}' === 'True'),
        'visited_urls_count': parseInt(_willet.storage.get('visited_urls_count', 0)),
        'uuid': '{{ app.uuid }}',
        'version': '{{sibt_version|default:"11"}}'
    }, instance = {
        'has_product': ('{{has_product}}' === 'True'), // product exists in DB?
        'has_results': ('{{has_results}}' === 'True'),
        'is_live': ('{{is_live}}' === 'True'),
        'show_votes': ('{{show_votes}}' === 'True'),
        'uuid': '{{ instance.uuid }}'
    }, user = {
        'has_voted': ('{{has_voted}}' === 'True'), // did they vote?
        'is_asker': ('{{is_asker}}' === 'True'), // did they ask?
        'uuid': '{{ user.uuid }}'
    };

    me.init = me.init || function (jQueryObject) {
        // this function may be called only once. use reInit afterwards
        // to update the UI.

        if (!jQueryObject) {
            wm.fire('error', 'init() must be called with jQuery as param1.');
            return;
        }

        $ = jQueryObject;  // throw $ into module scope
        wm.fire('log', 'Let the (SIBT) games begin!');

        me.updateProductHistory(); // generates the required variable, 'products'

        me.updateUI();
    };

    me.updateUI = me.updateUI || function (instance_uuid) {
        // requires $. call init() first.

        if (instance_uuid) {  // server side update value
            instance.uuid = instance_uuid;
            instance.is_live = true;
        }

        for(var prop in selectors) {
            if(!selectors.hasOwnProperty(prop)) {
                continue;
            }
            var matches = $(prop);
            if (matches.length >= 1) {  // found
                try {
                    me.setButton(
                        $(matches.eq(0)), // set my button
                        selectors[prop]   // as this kind
                    );
                    // me.saveProduct($(matches.eq(0)).data());
                } catch (err) {  // don't fail all buttons on the page
                    wm.fire('error', 'error setting button: ' + err);
                }
            }
        }

        if (app.features.bottom_popup) {
            wm.fire('SIBTSetBottomPopup');
        }
    };

    me.vendorMode = me.vendorMode || function () {
        // returns true or false on whether this script is running on
        // a vendor's website.
        // function can be called only after init() is.
        wm.fire('log', 'checking vendor mode');
        if ('{{ vendor }}') {
            wm.fire('log', 'vendorMode == true');
            return true;
        }
        if (!$) {
            return false;
        }
        return Boolean($('._vendor_sibt').length) ||
               Boolean($('#_vendor_shouldIBuyThisButton').length);
    };

    me.showPopupWindow = me.showPopupWindow || function (url) {
        var new_window = window.open(url, '_blank');
        new_window.focus();
    };

    me.showAsk = me.showAsk || function (message) {
        // shows the ask your friends iframe
        wm.fire('storeAnalytics', message || 'SIBTShowingAsk');
        var shopify_ids = [];
        if (cart_items) {
            // WOSIB exists on page; send extra data
            for (var i = 0; i < cart_items.length; i++) {
                shopify_ids.push(cart_items[i].id);
            }
        }

        return me.showPopupWindow(
            "{{URL}}{% url AskPageDynamicLoader %}" +
            // do not merge with metadata(): it escapes commas
            "?products=" + me.getProductUUIDs().join(',') +
            // if instance exists, it will be shown, not made!
            "&instance_uuid={{ instance.uuid }}" +
            "&shopify_ids=" + shopify_ids.join(',') +
            "&" + me.metadata()
        );

        // else if no products: do nothing
        wm.fire('log', "no products! cancelling dialogue.");
    };

    me.showVote = me.showVote || function (message) {
        wm.fire('storeAnalytics', message || 'SIBTShowingVote');
        var shopify_ids = [];
        if (cart_items) {
            // WOSIB exists on page; send extra data
            for (var i = 0; i < cart_items.length; i++) {
                shopify_ids.push(cart_items[i].id);
            }
        }

        return me.showPopupWindow(
            "{{URL}}{% url VoteDynamicLoader %}" +
            // do not merge with metadata(): it escapes commas
            "?products=" + me.getProductUUIDs().join(',') +
            // if instance exists, it will be shown, not made!
            "&instance_uuid={{ instance.uuid }}" +
            "&shopify_ids=" + shopify_ids.join(',') +
            "&" + me.metadata()
        );

        // else if no products: do nothing
        wm.fire('log', "no products! cancelling dialogue.");
    };

    me.showResults = me.showResults || function () {
        wm.fire('storeAnalytics', 'SIBTShowingResults');
        // show results if results are done.
        // this can be detected if a finished flag is raised.
        wm.fire('showColorbox', {
            href: "{{URL}}/s/results.html?" +
                me.metadata({  // force page_url to be the current location
                    'page_url': me.getCanonicalURL(window.location.href)
                })
        });
    };

    // turn a $(elem) into a SIBT button of (SMALL_SIBT/LARGE_SIBT/...) mode.
    me.setButton = me.setButton || function (jqElem, mode) {
        if (mode === SMALL_SIBT) {
            if (me.vendorMode()) { // double check
                me.setSmallSIBTVendorButton(jqElem);
            } else {
                me.setSmallSIBTButton(jqElem);
            }
        } else if (mode === LARGE_SIBT) {
            if (me.vendorMode()) { // double check
                me.setLargeSIBTVendorButton(jqElem);
            } else {
                me.setLargeSIBTButton(jqElem);
            }
        } else if (mode === SMALL_WOSIB) {
            // there is no small wosib button.
        } else if (mode === LARGE_WOSIB) {
            me.setLargeWOSIBButton(jqElem);
        } else if (mode === SMALL_SIBT_VENDOR) {
            me.setSmallSIBTVendorButton(jqElem);
        } else if (mode === LARGE_SIBT_VENDOR) {
            me.setLargeSIBTVendorButton(jqElem);
        }
    };

    // small buttons are smaller than the large ones.
    me.setSmallSIBTButton = me.setSmallSIBTButton || function (jqElem) {
        wm.fire('log', 'setting a small SIBT button');
        wm.fire('storeAnalytics');

        me.saveProduct(jqElem.data());

        if (   app.visited_urls_count >= 2
            && me.getProductUUIDs().length >= 2) {  // wosib threshold detection
            jqElem.click(me.button_onclick);
            jqElem.css ({
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
                wm.fire('log', "product did not exist here; hiding button. " +
                            "(if product detection succeeds, refreshing this " +
                            "page will make the button show again.)");
                jqElem.css ({
                    'display': 'none'
                });
            }
        } else {
            wm.fire('log', "View count too low; hiding button.");
        }
    };

    // large buttons are larger than the small ones.
    me.setLargeSIBTButton = me.setLargeSIBTButton || function (jqElem) {
        wm.fire('log', 'setting a large SIBT button');
        wm.fire('storeAnalytics');

        // run our scripts
        var hash = window.location.hash;
        var hash_search = '#code=';
        var hash_index = hash.indexOf(hash_search);
        var willt_code = hash.substring(hash_index + hash_search.length , hash.length);

        var v3data = jqElem.data();

        me.saveProduct({
            'title': v3data.title || false,
            'image': v3data.image_url || false
        });

        // if no product, try to detect one, but don't show button
        if (!instance.has_product) {
            wm.fire('log', "product does not exist here; hiding button.");
            return;
        }

        if (   app.features.button
            && app.visited_urls_count >= 2
            && me.getProductUUIDs().length >= 2) {  // wosib threshold detection
            wm.fire('storeAnalytics', 'buttonEnabled');
            if (parseInt(app.version) <= 2) {
                wm.fire('log', 'v2 button is enabled');
                wm.fire('storeAnalytics', 'v2ButtonEnabled');
                var button = document.createElement('a');
                var button_html = '';
                // only add button if it's enabled in the app
                if (user.is_asker) {
                    wm.fire('storeAnalytics', 'userIsAsker');
                    button_html = 'See what your friends said!';
                } else if (instance.show_votes) {
                    wm.fire('storeAnalytics', 'userIsNotAsker');
                    button_html = 'Help {{ asker_name }} by voting!';
                } else {
                    wm.fire('storeAnalytics', 'userIsNew');
                    var AB_CTA_text = AB_CTA_text || 'Ask your friends for advice!'; // AB lag
                    button_html = AB_CTA_text;
                }

                button = $(button)
                    .html(button_html)
                    .css('display', 'inline-block')
                    .attr('title', 'Ask your friends if you should buy this!')
                    .attr('id','_willet_button')
                    .attr('class','_willet_button willet_reset')
                    .click(me.button_onclick);
                jqElem.append(button);
            } else if (parseInt(app.version) >= 3) { // this should be changed to == 3 if SIBT standalone of a higher version will exist
                wm.fire('log', 'v3+ button is enabled');
                wm.fire('storeAnalytics', 'v3ButtonEnabled');
                if ($('#_willet_button_v3').length === 0) { // if the v3 button isn't there already
                    var button = $("<div />", {
                        'id': '_willet_button_v3'
                    });
                    button
                        .html ("<p>Need help deciding?</p>" +
                                	"<div class='button' " +
                                    "title='Ask your friends if you should buy this!'>" +
                                    "<img src='{{URL}}/static/plugin/imgs/chat_button_25x25.png' alt='logo' />" +
                                    "<div id='_willet_button' class='title'>Ask Trusted Friends</div>" +
                                    "</div>")
                        .css({'clear': 'both', 'background':'none'});
                    jqElem.append(button);
                } else {
                    var button = $('#_willet_button_v3');
                }
                $('#_willet_button').click(me.button_onclick);

                // if server sends a flag that indicates "results available"
                // (not necessarily "finished") then show finished button
                if (instance.is_live) {
                    wm.fire('storeAnalytics', 'SIBTShowingResultsButton');
                    $('#_willet_button_v3 .button').hide();
                    $('<div />', {
                        'id': "_willet_SIBT_results",
                        'class': "button"
                    })
                    .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                    .appendTo(button)
                    .css('display', 'inline-block')
                    .click(me.showVote);
                }

                var $wbtn = $('#_willet_button_v3 .button');
                if ($wbtn.length > 0) {
                    $wbtn = $($wbtn[0]);
                }
            }
        } else {
            wm.fire('log', "no product / view count too low; hiding button.");
        }
    };

    // Vendor-specific procedures
    me.setSmallSIBTVendorButton = me.setSmallSIBTVendorButton || function (jqElem) {
        wm.fire('log', 'setting a small vendor-specific SIBT button');
        wm.fire('storeAnalytics');

        // process vendor info on server side
        {% ifequal client.name "Shu Uemura USA" %}
            jqElem.css ({
                'background': "url('{{URL}}/static/sibt/imgs/sibt-shu-askfriends-blue.png') 3% 20% no-repeat transparent",
                'width': '92px',
                'height': '24px',
                'margin-top': '3px',
                'cursor': 'pointer',
                'display': 'block',
                'clear': 'both'
            })
            .click(function (message) {
                // shows the ask your friends iframe
                wm.fire('storeAnalytics', message || 'SIBTShowingAsk');
                var shopify_ids = [];
                if (cart_items) {
                    // WOSIB exists on page; send extra data
                    for (var i = 0; i < cart_items.length; i++) {
                        shopify_ids.push(cart_items[i].id);
                    }
                }

                return wm.fire('showColorbox', {
                    href: "{{URL}}{% url AskDynamicLoader %}" +
                        // do not merge with metadata(): it escapes commas
                        "?products=" + me.getProductUUIDs().join(',') +
                        "&shopify_ids=" + shopify_ids.join(',') +
                        "&instance_uuid={{ instance.uuid }}" +
                        "&" + me.metadata()
                });

                // else if no products: do nothing
                wm.fire('log', "no products! cancelling dialogue.");
            });

            if (!instance.has_product) {
                // if no product, try to detect one, but don't show button
                wm.fire('log', "product does not exist here; hiding button.");
                jqElem.css ({
                    'display': 'none'
                });
            }

            // Shu Uemura special data scraping
            var img_src = '';
            try {
                img_src = $('#ProductMagicZoomImg img')[0].src;
            } catch (e) { /*don't give a single s***/ }
            me.saveProduct({
                'title': $('#productdetailsName').text() || me.getPageTitle(),
                'description': $('#RightContainer h2').text() || '',
                'image': img_src || me.getLargestImage()
            });
        {% else %}
             wm.fire('log', 'Requested a Vendor-level SIBT button, ' +
                            'but no vendor-specific routine has been ' +
                            'defined for this client. Reverting to ' +
                            'Small SIBT button.');
             me.setSmallSIBTButton(jqElem);
        {% endifequal %}
    };

    me.setLargeSIBTVendorButton = me.setLargeSIBTVendorButton || function (jqElem) {
        // there is no large sibt vendor button.
        // well, there will be one, but I won't be writing it right now.
        wm.fire('log', 'setting a large vendor-specific SIBT button');
        wm.fire('storeAnalytics');

        me.setLargeSIBTButton(jqElem);
    };

    me.setLargeWOSIBButton = me.setLargeWOSIBButton || function (jqElem) {
        wm.fire('log', 'setting a large WOSIB button');
        wm.fire('storeAnalytics', 'WOSIBShowingButton');
        var button = $("<div />", {
                'id': '_willet_button_v3'
            });
            button.html("<p>Which ones should you buy?</p>\
                         <div id='_willet_button' class='button' \
                             title='Ask your friends if you should buy this!'>\
                             <img alt='logo' src='{{URL}}/static/plugin/imgs/chat_button_25x25.png' />\
                             <div class='title'>Ask Trusted Friends</div>\
                         </div>")
            .css({
                'clear': 'both',
                'display': 'inline-block'
            })
            .appendTo(jqElem);

        $('#_willet_button').click(me.button_onclick);

        // if server sends a flag that indicates "results available"
        // (not necessarily "finished") then show finished button
        if (instance.is_live) {
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
            // .click(me.showResults);
            .click(me.showVote);
        }
    };

    // there is no small WOSIB button.
    me.setSmallWOSIBButton = me.setSmallWOSIBButton || me.setLargeWOSIBButton;

    me.cleanArray = me.cleanArray || function (actual) {
        var i;
        var new_array = [];
        for(i = 0; i < actual.length; i++) {
            if (Boolean(actual[i]) === true) {
                new_array.push(actual[i]);
            }
        }
        return new_array;
    };

    me.randomString = me.randomString || function () {
        //http://fyneworks.blogspot.com/2008/04/random-string-in-javascript.html
        return String((new Date()).getTime()).replace(/\D/gi,'');
    };

    me.isScrolledIntoView = me.isScrolledIntoView || function (elem) {
        // http://stackoverflow.com/questions/487073
        // returns true if elem has dimensions within the viewport.
        var docViewTop = $(window).scrollTop();
        var docViewBottom = docViewTop + $(window).height();
        var elemTop = $(elem).offset().top;
        var elemBottom = elemTop + $(elem).height();
        return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
    };

    me.getCanonicalURL = me.getCanonicalURL || function (default_url) {
        // Tries to retrieve a canonical link from the header
        // Otherwise, returns default_url
        var links = document.getElementsByTagName('link'),
            i = links.length;
        while (i--) {
            if (links[i].rel === 'canonical' && links[i].href) {
                return links[i].href;
            }
        }
        return default_url;
    };

    me.getLargestImage = me.getLargestImage || function (within) {
        // Returns <img>.src for the largest <img> in <elem>within
        // source: http://stackoverflow.com/questions/3724738
        within = within || document; // defaults to document
        var nMaxDim = 0;
        var largest_image = '';
        $(within).find('img').each(function () {
            try {
                var $this = $(this),
                    $prop = $this.prop || $this.attr;  // low-level jQuery fallback
                if (this && $this && $prop) {
                    var nDim = parseFloat($this.width()) * parseFloat($this.height());
                    if (nDim > nMaxDim) {
                        largest_image = this.src || '';
                        nMaxDim = nDim;
                    }
                }
            } catch (err) {  // is DOM traversal being stupid today?
                wm.fire('log', "Yes, DOM traversal IS being stupid today.");
            }
        });
        return largest_image;
    };

    me.getPageTitle = me.getPageTitle || function () {
        return document.title || '';
    };

    me.getProductUUIDs = me.getProductUUIDs || function () {
        // currently, products are just their UUIDs (to save space)
        return me.cleanArray(products);
    };

    me.metadata = me.metadata || function (more) {
        // constructs the 'willet' query string - no prefixing ?
        // will be added for you.
        // add more query properties with the "more" param.
        var metabuilder = {},
            page_url = '{{ page_url }}' || me.getCanonicalURL(window.location.href);
        if ('{{ app.uuid }}') {
            metabuilder.app_uuid = '{{ app.uuid }}';
        }
        if ('{{ user.uuid }}') {
            metabuilder.user_uuid = '{{ user.uuid }}';
        }
        if ('{{ instance.uuid }}') {
            metabuilder.instance_uuid = '{{ instance.uuid }}';
        }
        if ('{{ store_url }}') {
            metabuilder.store_url = '{{ store_url }}'; // registration url
        }
        if ('{{ app.uuid }}') {
            metabuilder.app_uuid = '{{ app.uuid }}';
        }
        if (page_url) {
            metabuilder.target_url = page_url;
        }
        if ('{{ vendor }}') {
            // activate vendor mode for asks and results
            metabuilder.vendor = '{{ vendor }}';
        }

        return $.param($.extend(
            {}, // blank original
            metabuilder,
            more || {}
        ));
    };

    me.updateProductHistory = me.updateProductHistory || function () {
        // save past products' images
        // check if page is visited twice or more in a row
        if (me.getLargestImage() !== _willet.storage.get('product1_image', '') &&
            me.getLargestImage() !== _willet.storage.get('product2_image', '')) {
            // image 1 is more recent; shift products
            _willet.storage.set('product2_image', _willet.storage.get('product1_image', ''));
            _willet.storage.set('product1_image', me.getLargestImage());
        }

        // track number of pages the visitor had interacted
        _willet.storage.set(
            'visited_urls_count',  // exact URLs not tracked for privacy
            parseInt(_willet.storage.get('visited_urls_count', 0)) + 1
        );
        if (parseInt(_willet.storage.get('visited_urls_count', 0)) > 3) {  // UNSURE_MULTI_VIEW trigger
            // must be changed before initBottomPopup
            wm.fire('log', 'unsure_multi_view was turned on from the client side.');
            app.unsure_multi_view = true;
        }

        // load product currently on page
        var ptemp = _willet.storage.get('products', '');
        // wm.fire('log', "read product cookie, got " + ptemp);
        products = ptemp.split(','); // load
        if ($.inArray("{{product.uuid}}", products) === -1) { // unique
            products.unshift("{{product.uuid}}"); // insert as products[0]
            products = products.splice(0, PRODUCT_HISTORY_COUNT); // limit count (to 4kB!)
            products = me.cleanArray(products); // remove empties
            _willet.storage.set('products', products.join(',')); // save
            wm.fire('log', "saving product cookie " + products.join(','));
        } else {
            // wm.fire('log', "product already in cookie");
        }
        return products;
    };

    me.saveProduct = me.saveProduct || function(fill) {
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
                wm.fire('log', 'product already in DB, it seems.');
                return;
            }

            var data = {
                'client_uuid': fill.client_uuid || '{{ client.uuid }}', // REQUIRED
                'description': fill.description || '',
                'sibtversion': fill.sibtversion || app.version,
                'title': fill.title || me.getPageTitle(),
                'image': fill.image || me.getLargestImage(document),
                'images': fill.images || '',
                'price': fill.price || 0,
                'tags': fill.tags || '',
                'type': fill.type || '',
                'resource_url': '{{ page_url }}' || me.getCanonicalURL(window.location.href)
            };

            // don't send empty params over the network.
            data = me.filterFalsyProps(data);

            if (data.client_uuid) {
                // Chrome Access-Control-Allow-Origin: must use GET here.
                $('<img />', {
                    src: '{{URL}}{% url CreateProduct %}?' + $.param(data),
                    css: {'display':'none'}
                }).appendTo(document);
                // wm.fire('log', 'sent product request'); // reverse once shu uemura is done testing
                try {
                    console.log('sent product request');
                } catch (e) {}
            }
        } catch (e) {
            wm.fire('error', "failed to save product! " + e);
        }
    };

    me.ask_callback = me.ask_callback || function (fb_response) {
        user.is_asker = true;
        $('#_willet_button').html('Refresh the page to see your results!');
    };

    me.button_onclick = me.button_onclick || function(e, message) {
        var message = message || 'SIBTUserClickedButtonAsk';
        $('#_willet_padding').hide(); // if any
        me.showAsk(message);
    };

    me.filterFalsyProps = me.filterFalsyProps || function (obj) {
        // return a copy of obj with falsy values removed.
        var new_obj = {};
        for (var i in obj) {
            if (obj.hasOwnProperty(i) && i) {
                new_obj[i] = obj[i];
            }
        }
        return new_obj;
    };

    me.autoShowResults = me.autoShowResults || function () {
        // auto-show results on hash
        var hash = window.location.hash;
        var hash_search = '#open';
        var hash_index = hash.indexOf(hash_search);
        if (instance.has_results && hash_index !== -1) {
            // if vote has results and voter came from an email
            wm.fire('log', "has results?");
            me.showResults();
        }
    };

    me.changeUIStatus = me.changeUIStatus || function (cb) {
        // using stored cookie, determine if a user's SIBT instance is still
        // active. if at least one instance is active, change the UI to match
        // our finding.

        // if user has no instances, the ajax call is skipped entirely.
        var instances = _willet.storage.get('sibt_instances');
        if (!instances) {
            // return '';
            wm.fire('sibt_has_no_instances');
        }
        $.ajax({
            url: '{{ URL }}{% url SIBTInstanceStatusChecker %}',
            dataType: 'json',
            data: {
                'instance_uuids': instances
            },
            success: function (data) {
                if (data && data.uuid !== '') {
                    wm.fire('updateUI', data.uuid);
                }
            }
        });
    };

    // ==================== bottom popup functions ============================
    {% if app.bottom_popup_enabled %}
        me.buildBottomPopup = me.buildBottomPopup || function () {
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

        me.showBottomPopup = me.showBottomPopup || function () {
            if (_willet.storage.get('_willet_bottom_popup_closed')) {
                wm.fire('storeAnalytics', 'SIBTUserCancelledBottomPopupWithCookie');
                return;
            }
            if (popup) {
                wm.fire('storeAnalytics', 'SIBTUserShowedBottomPopup');
                popup.fadeIn('slow');
            }
        };
        me.hideBottomPopup = me.hideBottomPopup || function (permanently) {
            if (popup) {
                wm.fire('storeAnalytics', 'SIBTUserHidBottomPopup');
                popup.fadeOut('slow');
            }
            if (permanently) {
                // save that preference.
                wm.fire('storeAnalytics', 'SIBTUserHidBottomPopupWithCookie');
                _willet.storage.set('_willet_bottom_popup_closed', '1');
            }
        };

        me.initBottomPopup = me.initBottomPopup || function () {
            // if user visited at least two different product pages
            if (_willet.storage.get('product1_image') &&
                _willet.storage.get('product2_image') &&
                app.features.bottom_popup && app.unsure_multi_view) {
                wm.fire('log', 'bottom popup enabled');
                wm.fire('storeAnalytics', 'SIBTBottomPopupEnabled');
                var clickedOff = false;

                popup = me.buildBottomPopup();

                var product1_image = _willet.storage.get('product1_image', '');
                var product2_image = _willet.storage.get('product2_image', '');
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

                $(window).scroll(function () {
                    var pageHeight, scrollPos, threshold, windowHeight;

                    pageHeight = $(document).height();
                    scrollPos = $(window).scrollTop() + $(window).height();
                    threshold = pageHeight * app.bottom_popup_trigger;
                    windowHeight = $(window).height();

                    // popup will show only for pages sufficiently long.
                    if (pageHeight > windowHeight * 1.5) {
                        // wm.fire('storeAnalytics', 'popupEnabled');
                        if (scrollPos >= threshold) {
                            if (!popup.is(':visible') && !clickedOff) {
                                me.showBottomPopup();
                            }
                        } else {
                            if (popup.is(':visible')) {
                                me.hideBottomPopup();
                            }
                        }
                    } else {
                        wm.fire('storeAnalytics', 'SIBTBottomPopupDisabled');
                        wm.fire('log', "page too short");
                    }
                });
                $('#willet_sibt_popup .cta').click(function () {
                    me.showAsk('SIBTUserClickedBottomPopupAsk');
                    // me.showVote('SIBTUserClickedBottomPopupAsk');
                    me.hideBottomPopup();
                });
                $('#willet_sibt_popup #anti_cta').click(function (e) {
                    wm.fire('storeAnalytics', 'SIBTUserCancelledBottomPopup');
                    clickedOff = true;
                    e.preventDefault();
                    me.hideBottomPopup(clickedOff);
                });
            } else {
                wm.fire('log', 'cookies not populated / not unsure yet: ',
                        _willet.storage.get('product1_image', ''),
                        _willet.storage.get('product2_image', ''),
                        app.features.bottom_popup,
                        app.unsure_multi_view);
            }
        };
    {% endif %}

    // set up your module hooks
    if (wm) {
        wm.on('hasjQuery', me.init);

        // auto-show results on hash
        wm.on('updateUI', me.updateUI);

        // hooks for other libraries
        wm.on('setSmallSIBTButton', me.setSmallSIBTButton);
        wm.on('setLargeSIBTButton', me.setLargeSIBTButton);
        wm.on('setSmallWOSIBButton', me.setSmallWOSIBButton);
        wm.on('setLargeWOSIBButton', me.setLargeWOSIBButton);
        wm.on('setSmallSIBTVendorButton', me.setSmallSIBTVendorButton);
        wm.on('setLargeSIBTVendorButton', me.setLargeSIBTVendorButton);

        // others
        // we don't know if initBottomPopup is always there
        wm.on('SIBTSetBottomPopup', me.initBottomPopup || function () {});
    }

    return me;
} (_willet.sibt || {}));
