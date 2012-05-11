var _willet = _willet || {};  // ensure namespace is there

// Should I Buy This
// The hasjQuery event starts off automatic initialisation.
// product_title and product_description django tags require their own
// double quotes!

_willet.sibt = (function (me) {
    var wm = _willet.mediator || {};
    var $ = jQuery || {};  // I want jQuery here, but it won't be available
                           // until mediator says so.

    var SMALL_SIBT = 1, LARGE_SIBT = 2,
        SMALL_WOSIB = 3, LARGE_WOSIB = 4,
        selectors = {
            '#mini_sibt_button': SMALL_SIBT, // SIBT for ShopConnection (SIBT Connection)
            '#_willet_shouldIBuyThisButton': LARGE_SIBT, // SIBT standalone (v2, v3, v10)
            '._willet_sibt': SMALL_SIBT, // SIBT-JS
            '#_willet_WOSIB_Button': LARGE_WOSIB // WOSIB mode
        },
        cart_items = cart_items || window._willet_cart_items || [],
        PRODUCT_HISTORY_COUNT = {{ product_history_count|default:10 }},
        SHAKE_DURATION = 600, // ms
        SHAKE_WAIT = 1000, // ms

        padding_elem = null,
        topbar = null,
        topbar_hide_button = null;

    // declare vars in this scope
    var app, instance, products, topbar, user;

    me.init = me.init || function (jQueryObject) {
        $ = jQueryObject;  // throw $ into module scope
        // wm.fire('log', 'initialisating SIBT!');

        // These ('???' === 'True') guarantee missing tag, ('' === 'True') = false
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

        me.updateProductHistory(); // generates the required variable, 'products'

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
                    wm.fire('log', 'error setting button: ' + err);
                }
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
                "?products=" + me.getProductUUIDs().join(',') +
                "&ids=" + shopify_ids.join(',') +
                "&" + me.metadata()
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
                    me.metadata({
                        'refer_url': me.getCanonicalURL(window.location.href)
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
        wm.fire('log', 'setting a large SIBT button');
        wm.fire('storeAnalytics');

        // run our scripts
        var hash = window.location.hash;
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
        if (!instance.has_product) {
            wm.fire('log', "product does not exist here; hiding button.");
            return;
        }

        // show the topbar...
        if (app.features.topbar) {
            wm.fire('storeAnalytics', 'topbarEnabled');
            wm.fire('log', 'topbar enabled');

            var cookie_topbar_closed = ($.cookie('_willet_topbar_closed') === 'true');

            // create the hide button
            topbar_hide_button = $(document.createElement('div'));
            topbar_hide_button.attr('id', '_willet_topbar_hide_button')
                .css('display', 'none')
                .click(me.unhideTopbar);

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
                    wm.fire('storeAnalytics', 'SIBTShowingTopBarAsk');
                    me.showTopbarAsk();
                }
            }
        }

        if (app.features.button) {
            wm.fire('storeAnalytics', 'buttonEnabled');
            if (parseInt(app.version) <= 2) {
                wm.fire('log', 'v2 button is enabled');
                var button = document.createElement('a');
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
                    .click(me.button_onclick);
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
                $('#_willet_button').click(me.button_onclick);

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
                'target_url': '{{ page_url }}' || me.getCanonicalURL(window.location.href)
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
        if (me.getLargestImage() !== $.cookie('product1_image') &&
            me.getLargestImage() !== $.cookie('product2_image')) {
            // image 1 is more recent; shift products
            $.cookie('product2_image', $.cookie('product1_image'));
            $.cookie('product1_image', me.getLargestImage());
        }

        // load product currently on page
        var ptemp = $.cookie('products') || '';
        // wm.fire('log', "read product cookie, got " + ptemp);
        products = ptemp.split(','); // load
        if ($.inArray("{{product.uuid}}", products) === -1) { // unique
            products.unshift("{{product.uuid}}"); // insert as products[0]
            products = products.splice(0, PRODUCT_HISTORY_COUNT); // limit count (to 4kB!)
            products = me.cleanArray(products); // remove empties
            $.cookie('products', products.join(',')); // save
            wm.fire('log', "saving product cookie " + products.join(','));
        } // else {
            // wm.fire('log', "product already in cookie");
        // }
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
                // wm.fire('log', 'product already in DB, it seems.');
                return;
            }

            var data = {
                'client_uuid': fill.client_uuid || '{{ client.uuid }}', // REQUIRED
                'sibtversion': fill.sibtversion || app.version,
                'title': fill.title || me.getPageTitle(),
                'image': fill.image || me.getLargestImage(d),
                'resource_url': '{{ page_url }}' || me.getCanonicalURL(window.location.href)
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

    me.autoShowResults = me.autoShowResults || function () {
        // auto-show results on hash
        var hash = window.location.hash;
        var hash_search = '#open';
        var hash_index = hash.indexOf(hash_search);
        if (instance.has_results && hash_index !== -1) {
            // if vote has results and voter came from an email
            // wm.fire('log', "has results?");
            me.showResults();
        }
    };

    me.getVisitLength = me.getVisitLength || function () {
        // analytics to record the amount of time this script has been loaded
        // this must be an iframe to time it + send synchronous requests
        $('<iframe />', {
            css: {'display': 'none'},
            src: "{{URL}}{% url ShowOnUnloadHook %}?" +
                 me.metadata({'evnt': 'SIBTVisitLength'})
        }).appendTo("body");
    };


    // =================== deprecated topbar functions ========================
    me.topbar_onclick = me.topbar_onclick || function(e) {
        // Onclick event handler for the 'sibt' button
        me.button_onclick(e, 'SIBTUserClickedTopBarAsk');
    };

    me.unhideTopbar = me.unhideTopbar || function() {
        // When a user hides the top bar, it shows the little
        // "Show" button in the top right. This handles the clicks to that
        $.cookie('_willet_topbar_closed', false);
        topbar_hide_button.slideUp('fast');
        if (topbar === null) {
            if (instance.show_votes || hash_index !== -1) {
                me.showTopbar();
                wm.fire('storeAnalytics', 'SIBTUserReOpenedTopBar');
            } else {
                me.showTopbarAsk();
                wm.fire('storeAnalytics', 'SIBTShowingTopBarAsk');
            }
        } else {
            topbar.slideDown('fast');
            wm.fire('storeAnalytics', 'SIBTUserReOpenedTopBar');
        }
    };

    me.closeTopbar = me.closeTopbar || function() {
        // Hides the top bar and padding
        $.cookie('_willet_topbar_closed', true);
        topbar.slideUp('fast');
        topbar_hide_button.slideDown('fast');
        wm.fire('storeAnalytics', 'SIBTUserClosedTopBar');
    };

    // Expand the top bar and load the results iframe
    me.doVote = me.doVote || function(vote) {
        // detecting if we just voted or not
        var doing_vote = (vote !== -1);
        var vote_result = (vote === 1);

        // getting the neccesary dom elements
        var iframe_div = topbar.find('div.iframe');
        var iframe = topbar.find('div.iframe iframe');

        // constructing the iframe src
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);
        var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
        var results_src = "{{URL}}/s/results.html?" +
            "willt_code=" + encodeURIComponent(willt_code) +
            "&user_uuid={{user.uuid}}" +
            "&doing_vote=" + encodeURIComponent(doing_vote) +
            "&vote_result=" + encodeURIComponent(vote_result) +
            "&is_asker=" + user.is_asker +
            "&store_id={{store_id}}" +
            "&store_url={{store_url}}" +
            "&instance_uuid={{instance.uuid}}" +
            "&url=" + encodeURIComponent(window.location.href);

        // show/hide stuff
        topbar.find('div.vote').hide();
        if (doing_vote || user.has_voted) {
            topbar.find('div.message').html('Thanks for voting!').fadeIn();
        } else if (user.is_asker) {
            topbar.find('div.message').html('Your friends say:   ').fadeIn();
        }

        // start loading the iframe
        iframe_div.show();
        iframe.attr('src', '');
        iframe.attr('src', results_src);

        iframe.fadeIn('medium');
    };

    me.doVote_yes = me.doVote_yes || function () {
        me.doVote(1);
    };
    me.doVote_no = me.doVote_no || function () {
        me.doVote(0);
    };

    me.buildTopBarHTML = me.buildTopBarHTML || function (is_ask_bar) {
        // Builds the top bar html
        // is_ask_bar option boolean
        // if true, loads ask_in_the_bar iframe

        if (is_ask_bar || false) {
            var AB_CTA_text = AB_CTA_text || 'Ask your friends for advice!'; // AB lag
            var bar_html = "<div class='_willet_wrapper'><p style='font-size: 15px'>Decisions are hard to make. " + AB_CTA_text + "</p>" +
                "<div id='_willet_close_button' style='position: absolute;right: 13px;top: 1px; cursor: pointer;'>" +
                "   <img src='{{URL}}/static/imgs/fancy_close.png' width='30' height='30' />" +
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
                "   <img src='{{URL}}/static/imgs/fancy_close.png' width='30' height='30' />" +
                "</div>" +
            "</div>";
        }
        return bar_html;
    };

    me.showTopbar = me.showTopbar || function() {
        // Shows the vote top bar
        var body = $('body');

        // create the padding for the top bar
        padding_elem = document.createElement('div');
        padding_elem = $(padding_elem)
            .attr('id', '_willet_padding')
            .css('display', 'none');

        topbar = document.createElement('div');
        topbar = $(topbar)
            .attr('id', '_willet_sibt_bar')
            .css('display', "none")
            .html(me.buildTopBarHTML());
        body.prepend(padding_elem);
        body.prepend(topbar);

        // bind event handlers
        $('#_willet_close_button').unbind().bind('click', me.closeTopbar);
        $('#yesBtn').click(me.doVote_yes);
        $('#noBtn').click(me.doVote_no);

        padding_elem.show();
        topbar.slideDown('slow');

        if (!instance.is_live) {
            // voting is over folks!
            topbar.find('div.message').html('Voting is over!');
            me.toggleResults();
        } else if (instance.show_votes && !user.has_voted && !user.is_asker) {
            // show voting!
            topbar.find('div.vote').show();
        } else if (user.has_voted && !user.is_asker) {
            // someone has voted && not the asker!
            topbar.find('div.message').html('Thanks for voting!').fadeIn();
            me.toggleResults();
        } else if (user.is_asker) {
            // showing top bar to asker!
            topbar.find('div.message').html('Your friends say:   ').fadeIn();
            me.toggleResults();
        }
    };

    me.showTopbarAsk = me.showTopbarAsk || function() {
        //Shows the ask top bar

        // create the padding for the top bar
        padding_elem = document.createElement('div');

        padding_elem = $(padding_elem)
            .attr('id', '_willet_padding')
            .css('display', 'none');

        topbar = $('<div />', {
            'id': '_willet_sibt_ask_bar',
            'class': 'willet_reset',
            'css': {
                'display': 'none'
            }
        });
        topbar.html(me.buildTopBarHTML(true));

        $("body").prepend(padding_elem).prepend(topbar);

        var iframe = topbar.find('div.iframe iframe');
        var iframe_div = topbar.find('div.iframe');

        $('#_willet_close_button').unbind().bind('click', me.closeTopbar);

        topbar.find( '._willet_wrapper p')
            .css('cursor', 'pointer')
            .click(me.topbar_onclick);
        padding_elem.show();
        topbar.slideDown('slow');
    };

    me.topbarAskSuccess = me.topbarAskSuccess || function () {
        // if we get a postMessage from the iframe
        // that the share was successful
        wm.fire('storeAnalytics', 'SIBTTopBarShareSuccess');
        var iframe = topbar.find('div.iframe iframe');
        var iframe_div = topbar.find('div.iframe');

        user.is_asker = true;

        iframe_div.fadeOut('fast', function() {
            topbar.animate({height: '40'}, 500);
            iframe.attr('src', '');
            me.toggleResults();
        });
    };

    me.toggleResults = me.toggleResults || function() {
        // Used to toggle the results view
        // iframe has no source, hasnt been loaded yet
        // and we are FOR SURE showing it
        doVote(-1);
    };
    // =================== deprecated topbar functions ========================




    // set up your module hooks
    if (wm) {
        wm.on('hasjQuery', me.init);

        // auto-show results on hash
        wm.on('scriptComplete', me.autoShowResults);
        wm.on('scriptComplete', me.getVisitLength);
    }

    return me;
} (_willet.sibt || {}));