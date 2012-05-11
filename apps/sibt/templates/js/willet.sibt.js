var _willet = _willet || {};  // ensure namespace is there

// Should I Buy This
// The hasjQuery event starts off automatic initialisation.
_willet.SIBT = (function (me) {
    var wm = _willet.Mediator || {};
    var $ = jQuery || {};  // I want jQuery here, but it won't be available
                           // until Mediator says so.

    var SMALL_SIBT = 1, LARGE_SIBT = 2,
        SMALL_WOSIB = 3, LARGE_WOSIB = 4,
        selectors = {
            '#mini_sibt_button': SMALL_SIBT, // SIBT for ShopConnection (SIBT Connection)
            '#_willet_shouldIBuyThisButton': LARGE_SIBT, // SIBT standalone (v2, v3, v10)
            '._willet_sibt': SMALL_SIBT, // SIBT-JS
            '#_willet_WOSIB_Button': LARGE_WOSIB // WOSIB mode
        },
        PRODUCT_HISTORY_COUNT = {{ product_history_count|default:10 }},
        SHAKE_DURATION = 600, // ms
        SHAKE_WAIT = 700; // ms

    // these are required variables from outside the scope
    var sys = sys || {},
        app = app || {},
        instance = instance || {},
        products = products || [],
        user = user || {},
        cart_items = cart_items || window._willet_cart_items || [];


    me.init = me.init || function (jQueryObject) {
        $ = jQueryObject;  // throw $ into module scope
        wm.fire('log', 'initialisating SIBT!');

        for(var prop in selectors) {
            if(!selectors.hasOwnProperty(prop)) {
                continue;
            }
            var matches = $(prop);
            if (matches.length >= 1) {  // found
                wm.fire('log', 'setting button type ' + selectors[prop] + '!');
                me.setButton(
                    $(matches.eq(0)), // set my button
                    selectors[prop]   // as this kind
                );
            }
        }
    };

    me.showAsk = me.showAsk || function (message) {
        // shows the ask your friends iframe
        wm.fire('storeAnalytics', 'showAsk');
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
                "?products=" + getProductUUIDs().join(',') +
                "&ids=" + shopify_ids.join(',') +
                "&" + metadata()
        });

        // else if no products: do nothing
        wm.fire('log', "no products! cancelling dialogue.");
    };

    me.showResults = me.showResults || function () {
        wm.fire('storeAnalytics', 'showResults');
        // show results if results are done.
        // this can be detected if a finished flag is raised.
        wm.fire('showColorbox', {
            href: "{{URL}}/s/results.html?" +
                    metadata({
                        'refer_url': getCanonicalURL(w.location.href)
                    })
        });
    };

    // turn a $(elem) into a SIBT button of (SMALL_SIBT/LARGE_SIBT/...) mode.
    me.setButton = me.setButton || function (jqElem, mode) {
        if (mode === SMALL_SIBT) {
            me.setSmallSIBTButton(jqElem);
        } else if (mode === LARGE_SIBT) {
            me.setLargeSIBTButton(jqElem);
        } else if (mode === SMALL_WOSIB) {
            // there is no small wosib button.
        } else if (mode === LARGE_WOSIB) {
            me.setLargeWOSIBButton(jqElem);
        }
    };

    // small buttons are smaller than the large ones.
    me.setSmallSIBTButton = me.setSmallSIBTButton || function (jqElem) {
        wm.fire('log', 'setting a small SIBT button');
        wm.fire('storeAnalytics');

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
            wm.fire('log', "product does not exist here; hiding button.");
            jqElem.css ({
                'display': 'none'
            });
        }

        // shake ONLY the SIBT button when scrolled into view
        me.addScrollShaking(jqElem);
        me.saveProduct(jqElem.data());
    };

    // large buttons are larger than the small ones.
    me.setLargeSIBTButton = me.setLargeSIBTButton || function (jqElem) {
        wm.fire('log', 'setting a small SIBT button');
        wm.fire('storeAnalytics');

        // run our scripts
        var hash = w.location.hash;
        var hash_search = '#code=';
        var hash_index = hash.indexOf(hash_search);
        var willt_code = hash.substring(hash_index + hash_search.length , hash.length);

        var v3data = jqElem.data();
        try {
            me.saveProduct({
                'title': v3data.title || false,
                'image': v3data.image_url || false
            });
        } catch (e) {
            wm.fire('log', "failed to let v3 button save product!");
        }

        // if no product, try to detect one, but don't show button
        if (instance.has_product) {
            if (app.features.topbar) {
                wm.fire('storeAnalytics', 'topbarEnabled');
                wm.fire('log', 'topbar enabled');

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
            }

            if (app.features.button) {
                wm.fire('storeAnalytics', 'buttonEnabled');
                if (parseInt(app.version) <= 2) {
                    wm.fire('log', 'v2 button is enabled');
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
                    jqElem.append(button);
                } else if (parseInt(app.version) >= 3) { // this should be changed to == 3 if SIBT standalone of a higher version will exist
                    wm.fire('log', 'v3+ button is enabled');
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
                        jqElem.append(button);
                    } else {
                        var button = $('#_willet_button_v3');
                    }
                    $('#_willet_button').click(button_onclick);

                    // if server sends a flag that indicates "results available"
                    // (not necessarily "finished") then show finished button
                    if (instance.is_live || instance.has_results) {
                        $('#_willet_button_v3 .button').hide();
                        $('<div />', {
                            'id': "_willet_SIBT_results",
                            'class': "button"
                        })
                        .append("<div class='title' style='margin-left:0;'>Show results</div>") // if no button image, don't need margin
                        .appendTo(button)
                        .css('display', 'inline-block')
                        .click(me.showResults);
                    }

                    var $wbtn = $('#_willet_button_v3 .button');
                    if ($wbtn.length > 0) {
                        $wbtn = $($wbtn[0]);
                    }
                    me.addScrollShaking($wbtn);
                }
            }
        } else {
            wm.fire('log', "product does not exist here; hiding button.");
        }
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
                            <img alt='logo' src='{{URL}}/static/plugin/imgs/logo_button_25x25.png' />\
                            <div class='title'>Ask Trusted Friends</div>\
                            </div>")
            .css({
                'clear': 'both',
                'display': 'inline-block'
            })
            .appendTo(jqElem);

        $('#_willet_button').click(me.showAsk);

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
            .click(me.showResults);
        }
    };

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
        var docViewTop = $(w).scrollTop();
        var docViewBottom = docViewTop + $(w).height();
        var elemTop = $(elem).offset().top;
        var elemBottom = elemTop + $(elem).height();
        return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
    };

    me.getCanonicalURL = me.getCanonicalURL || function (default_url) {
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

    me.getLargestImage = me.getLargestImage || function (within) {
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
        return $.param($.extend (
            {}, // blank original
            {
                'app_uuid': '{{ app.uuid }}',
                'user_uuid': '{{ user.uuid }}',
                'instance_uuid': '{{ instance.uuid }}',
                'store_url': '{{ store_url }}', // registration url
                'target_url': '{{ page_url }}' || me.getCanonicalURL(w.location.href) // window.location
            },
            more || {}
        ));
    };

    me.addScrollShaking = me.addScrollShaking || function (elem) {
        // needs the shaker jQuery plugin.
        var $elem = $(elem);
        $(window).scroll(function () {
            if (me.isScrolledIntoView($elem) && !$elem.data('shaken_yet')) {
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

    me.updateProductHistory = me.updateProductHistory || function () {
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
        wm.fire('log', "read product cookie, got " + ptemp);
        products = ptemp.split(','); // load
        if ($.inArray("{{product.uuid}}", products) === -1) { // unique
            products.unshift("{{product.uuid}}"); // insert as products[0]
            products = products.splice(0, PRODUCT_HISTORY_COUNT); // limit count (to 4kB!)
            products = me.cleanArray(products); // remove empties
            $.cookie('products', products.join(',')); // save
            wm.fire('log', "saving product cookie " + products.join(','));
        } else {
            wm.fire('log', "product already in cookie");
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
                'sibtversion': fill.sibtversion || app.version,
                'title': fill.title || me.getPageTitle(),
                'image': fill.image || me.getLargestImage(d),
                'resource_url': '{{ page_url }}' || me.getCanonicalURL(w.location.href)
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
                wm.fire('log', 'sent product request');
            }
        } catch (e) {
            wm.fire('log', e.message);
        }
    };

    me.ask_callback = me.ask_callback || function (fb_response) {
        user.is_asker = true;
        $('#_willet_button').html('Refresh the page to see your results!');
    };

    me.button_onclick = me.button_onclick || function(e, message) {
        var message = message || 'SIBTUserClickedButtonAsk';
        $('#_willet_padding').hide(); // if any
        if (user.is_asker || instance.show_votes) {
            // we are no longer showing results with the topbar.
            me.showResults();
        } else {
            wm.fire('storeAnalytics', message);
            me.showAsk();
        }
    };


    // set up your module hooks
    if (wm) {
        wm.on('hasjQuery', function (jq) {
            wm.fire('log', "woot!");
            me.init(jq);
        });
    }

    return me;
} (_willet.SIBT || {}));