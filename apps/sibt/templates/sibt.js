/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

// Fun Safari cookie hack ... wooooo
var firstTimeSession = 0;
var doSafariCookieHack = function() {
    if (firstTimeSession == 0) {
        firstTimeSession = 1;
        document.getElementById('sessionform').submit()
        setTimeout(setCookieHackFlag, 2000);
    }
};

var setCookieHackFlag = function() {
    window.cookieSafariHackReady = true;
};

// Let's be dumb about this ... this'll fire on more than just Safari
// BUT it will fire on Safari, which is what we need.
// TODO: Fix this. Apparently, there is no easy way to determine strictly 'Safari'.
if ( navigator.userAgent.indexOf('Safari') != -1 ) {
    var hackIFrame = document.createElement( 'iframe' );
    hackIFrame.setAttribute( 'src', "{{URL}}{% url UserCookieSafariHack %}" );
    hackIFrame.setAttribute( 'id', "sessionFrame" );
    hackIFrame.setAttribute( 'name', "sessionFrame" );
    hackIFrame.setAttribute( 'onload', "doSafariCookieHack();" );
    hackIFrame.style.display = 'none';

    var hackForm = document.createElement( 'form' );
    hackForm.setAttribute( 'id', 'sessionform' );
    hackForm.setAttribute( 'action', "{{URL}}{% url UserCookieSafariHack %}" );
    hackForm.setAttribute( 'method', 'post' );
    hackForm.setAttribute( 'target', 'sessionFrame' );
    hackForm.setAttribute( 'enctype', 'application/x-www-form-urlencoded' );
    hackForm.style.display = 'none';

    var hackInput = document.createElement( 'input' );
    hackInput.setAttribute( 'type', 'text' );
    hackInput.setAttribute( 'value', '{{user.uuid}}' );
    hackInput.setAttribute( 'name', 'user_uuid' );
    document.body.appendChild( hackIFrame );
    hackForm.appendChild( hackInput );
    document.body.appendChild( hackForm );
} else {
    setCookieHackFlag();
}

(function(document, window){
    var _willet_css = {% include stylesheet %}
    var _willet_app_css = '{{ app_css }}';
    var _willet_ask_success = false;
    var _willet_is_asker = ('{{ is_asker }}' == 'True'); // did they ask?
    var _willet_show_votes = ('{{ show_votes }}' == 'True');
    var _willet_has_voted = ('{{ has_voted }}' == 'True');
    var sibt_button_enabled = ('{{ app.button_enabled }}' == 'True');
    var is_live = ('{{ is_live }}' == 'True');
    var show_top_bar_ask = ('{{ show_top_bar_ask }}' == 'True');
    var _willet_topbar = null;
    var _willet_padding = null;
    var _willet_topbar_hide_button = null;
    var willt_code = null;
    var hash_index = -1;
    var sibt_tb_enabled   = {{AB_top_bar}};
    var imgOverlayEnabled = {{AB_overlay}};
    var bottomTabEnabled  = {{AB_btm_tab}};
    var $ = (typeof jQuery == 'function' ? jQuery : '');

    /**
    * quick helper function to add scripts to dom
    */
    var _willet_load_remote_script = function(script) {
        var dom_el = document.createElement('script'); 
        dom_el.src = script;
        dom_el.type = 'text/javascript'; 
        document.getElementsByTagName('head')[0].appendChild(dom_el); 
        return dom_el;
    };

    var _willet_vote_callback = function () {
        /**
        * Called when the vote iframe is closed
        */
        var button = $('#_willet_button');
        var original_shadow = button.css('box-shadow');
        var glow_timeout = 400;

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

    /**
    * Onclick event handler for the 'sibt' button
    */
    var _willet_topbar_onclick = function(e) {
        _willet_button_onclick(e, 'SIBTUserClickedTopBarAsk');
    };

    /**
    * Onclick event handler for the 'sibt' overlay button
    */
    var _willet_overlay_onclick = function(e) {
        _willet_button_onclick(e, 'SIBTUserClickedOverlayAsk');
    };

    /**
    * Onclick event handler for the 'sibt' bottom tab button
    */
    var _willet_tab_onclick = function(e) {
        _willet_button_onclick(e, 'SIBTUserClickedTabAsk');
    };

    var _willet_button_mouseenter = function(e) {
        if ( imgOverlayEnabled ){
            $("#overlayImgDiv").fadeIn('fast', function() { $("#overlayImgDiv").mouseleave(_willet_button_mouseleave).unbind('mouseenter'); } );
        }
    };

    var _willet_button_mouseleave = function(e) {
        $("#overlayImgDiv").fadeOut('fast', function() { $("#overlayImgDiv").mouseenter(_willet_button_mouseenter); });
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
            //_willet_show_vote();
            window.location.reload(true);
        } else {
            _willet_store_analytics(message);
            _willet_show_ask();        
        }

        // Turn off image overlay if it was on
        _willet_button_mouseleave();
        imgOverlayEnabled = false;
        
        $('#_willet_bottom_tab').slideUp('fast');
    };

    /**
    * shows the ask your friends iframe
    */
    var _willet_show_ask = function ( message ) {

        var url =  "{{URL}}/s/preask.html?user_uuid={{ user.uuid }}" + 
                                     "&store_url={{ store_url }}" +
                                     "&url=" + window.location.href;
        $.willet_colorbox({
            transition: 'fade',
            close: '',
            scrolling: false,
            iframe: true, 
            initialWidth: 0, 
            initialHeight: 0, 
            innerWidth: '400px',
            innerHeight: '220px', 
            fixed: true,
            href: url,
            onClosed: _willet_ask_callback
        });

        _willet_button_mouseleave();
    };

    /**
    * Shows the voting screen
    */
    var _willet_show_vote = function() {
        var photo_src = $('#image img').attr('src'); 
        //var hash        = window.location.hash;
        //var hash_search = '#code=';
        //var hash_index  = hash.indexOf(hash_search);
        //var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
            
        var url = "{{URL}}/s/vote.html?willt_code=" + willt_code + 
                "&user_uuid={{user.uuid}}" + 
                "&is_asker={{is_asker}}&store_id={{store_id}}" + 
                "&photo=" + photo_src + 
                "&instance_uuid={{instance.uuid}}" +
                "&url=" + window.location.href;  

        $.willet_colorbox({
            transition: 'fade',
            scrolling: true, 
            iframe: true,
            fixed: true,
            initialWidth: 0, 
            initialHeight: 0,
            innerWidth: '660px',
            innerHeight: '90%',
            href: url,
            onClosed: _willet_vote_callback
        });
    };
    
    /**
    * Used to toggle the results view
    */
    var _willet_toggle_results = function() {
        // iframe has no source, hasnt been loaded yet
        // and we are FOR SURE showing it
        _willet_do_vote(-1);
    };

    /**
     * When a user hides the top bar, it shows the little
     * "Show" button in the top right. This handles the clicks to that
     */
    var _willet_unhide_topbar = function() {
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

    /**
     * Hides the top bar and padding
     */
    var _willet_close_top_bar = function() {
        //$('#_willet_padding').hide();
        //_willet_padding.hide();
        $.cookie('_willet_topbar_closed', true);
        _willet_topbar.slideUp('fast'); 
        _willet_topbar_hide_button.slideDown('fast');
        _willet_store_analytics('SIBTUserClosedTopBar');
    };

    /**
    * Expand the top bar and load the results iframe
    */
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
    
    /**
     * Builds the top bar html
     * is_ask_bar option boolean
     *      if true, loads ask_in_the_bar iframe
     */
    var build_top_bar_html = function (is_ask_bar) {

        if (is_ask_bar || false) {
            var bar_html = "<div class='_willet_wrapper'><p style='font-size: 15px'>Decisions are hard to make. {{AB_CTA_text}}</p>" +
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

    /**
    * Shows the vote top bar
    */
    var _willet_show_topbar = function() {
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

    /**
     * Shows the ask top bar
     */
    var _willet_show_topbar_ask = function() {
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
            .click(function() {
                // user has clicked on the ask their friends top bar
                // text!

                // the top bar embedded ask is disabled
                // instead let's just show the normal colorbox popup
                // ... BORING!
                // let's hide the top bar as well
                
                _willet_topbar_onclick();
                //_willet_button_onclick();
                /*
                if (iframe_div.css('display') == 'none') {
                    if (iframe.attr('src') == undefined) {
                        var url =  "{{URL}}/s/ask.html?store_url={{ store_url }}" +
                            "&user_uuid={{user.uuid}} + 
                            "&is_topbar_ask=yourmomma" + 
                            "&url=" + window.location.href;
                        iframe.attr('src', url)
                        iframe.width(iframe_div.width());
                        iframe.fadeIn('fast');
                    } 
                    // show the iframe div!
                    _willet_topbar.animate({height: '337px'}, 500);
                    iframe_div.fadeIn('fast', function() {
                        // resize iframe once container showing
                        iframe.width(iframe_div.width());
                    });
                } else {
                    iframe_div.fadeOut('fast');
                    _willet_topbar.animate({height: '40'}, 500); 
                }
                */
            }
        );
        
        _willet_padding.show(); 
        _willet_topbar.slideDown('slow'); 
    };

    /**
     * if we get a postMessage from the iframe
     * that the share was successful
     */
    var _willet_topbar_ask_success = function () {
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

    var scripts = [
    /**
    * Scripts to load into the dom
    *   name - name of the script
    *   url - url of script
    *   dom_el - dom element once inserted
    *   loaded - script has been loaded
    *   test - method to test if it has been loaded
    *   callback - callback after test is success
    */
        {
            'name': 'Modernizr',
            'url': '{{ URL }}/static/js/modernizr.custom.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof Modernizr == 'object');
            }, 'callback': function() {
                return;
            }
        }, 
        /*
        {
            'name': 'jQuery',
            'url': 'http://github.com/cowboy/jquery-postmessage/raw/master/jquery.ba-postmessage.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof jQuery.receiveMessage == 'function');
            }, 'callback': function() {
                $ = jQuery;
                return;
            }
        },
        */
        {
            'name': 'jQuery Colorbox',
            'url': '{{ URL }}/s/js/jquery.colorbox.js?' + 
                   'app_uuid={{app.uuid}}&' + 
                   'user_uuid={{user.uuid}}&' + 
                   'instance_uuid={{instance.uuid}}&' + 
                   'target_url=' + window.location.href,
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof jQuery == 'function' && typeof jQuery.willet_colorbox == 'function')
            }, 'callback': function() {
                // HACKETY HACK HACK
                $ = jQuery;
                $.willet_colorbox = jQuery.willet_colorbox;
                jQuery.willet_colorbox.init();
            }
        }
    ];

    var _willet_check_scripts = function() {
        /**
        * checkScripts checks the scripts var and uses
        * the defined `test` and `callack` methods to tell
        * when a script has been loaded and is ready to be
        * used
        */    
        var all_loaded = true;

        for (i = 0; i < scripts.length; i++) {
            var row  = scripts[i];
            if (row.dom_el == null) {
                // insert the script into the dom
                if (row.test()) {
                    // script is already loaded!
                    row.callback();
                    row.loaded = true;
                    row.dom_el = true;
                } else {
                    row.dom_el = _willet_load_remote_script(row.url);
                }
            }
            if (row.loaded == false) {
                if (row.test()) {
                    // script is now loaded!
                    row.callback();
                    row.loaded = true;
                } else {
                    all_loaded = false;
                }
            }   
        }

        if (all_loaded && window.cookieSafariHackReady) {
            run();
        } else {
            window.setTimeout(_willet_check_scripts,100);
        }
    };

    /**
    * Main script to run
    * We have jQuery!!!!
    */
    var run = function() {
        
        var purchase_cta = $('#_willet_shouldIBuyThisButton');
        if (purchase_cta.length > 0) {
            
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
                var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
                var button = document.createElement('a');
                var button_html = '';

                // check if we are showing top bar ask too
                if (sibt_tb_enabled && show_top_bar_ask) {
                    if (cookie_topbar_closed) {
                        // user has hidden the top bar
                        _willet_topbar_hide_button.slideDown('fast');
                    } else {
                        _willet_store_analytics('SIBTShowingTopBarAsk');
                        _willet_show_topbar_ask();
                    }
                } 

                if (sibt_button_enabled) {
                    // only add button if it's enabled in the app 
                    if (_willet_is_asker) {
                        button_html = 'See what your friends said!';
                    } else if (_willet_show_votes) {
                        button_html = 'Help {{ asker_name }} by voting!';
                    } else {
                        button_html = '{{AB_CTA_text}}';
                    }

                    button = $(button)
                        .html(button_html)
                        .css('display', 'none')
                        .attr('title', 'Ask your friends if you should buy this!')
                        .attr('id','_willet_button')
                        .attr('class','_willet_button willet_reset')
                        .click(_willet_button_onclick);
                
                    $(purchase_cta).append(button);
                    button.fadeIn(250, function() {
                        $(this).css('display', 'inline-block'); 
                    });
                }
                
                // watch for message
                // Create IE + others compatible event handler
                $(window).bind('onmessage message', function(e) {
                    var message = e.originalEvent.data;
                    //console.log('parent received message: ', e.data, e);
                    if (message == 'shared') {
                        _willet_ask_success = true;
                    } else if (message == 'top_bar_shared') {
                        //console.log('shared on top bar!'); 
                        _willet_topbar_ask_success();
                    } else if (message == 'close') {
                        $.willet_colorbox.close();
                    }
                });
                
                if ( bottomTabEnabled ) {
                    var tab = $(document.createElement( 'div' ));
                    tab.attr( 'id', "_willet_bottom_tab" );
                    tab.attr( 'class', "willet_reset" );
                    tab.html( '<p>Can\'t decide?<br />{{AB_CTA_text}}</p>' );
                    tab.click( _willet_tab_onclick );

                    $('body').append( tab );
                    tab.slideDown( 'slow' );
                }

                if ( imgOverlayEnabled ) {
                    // Walk events on image div and make sure there are no
                    // mouse ones.
                    var imgElem = $('{{img_elem_selector}}');
                    if ( imgElem.length > 0 ) {
                        var imgWidth  = imgElem.width();
                        var imgHeight = imgElem.height();
                        var foo = $.data( imgElem.get(0), 'events' );
                        var noImgMouseEvent = true;
                        if ( foo != null ) {
                            $.each( foo, function(i,o) {
                                if( i=="hover" || i=="mouseover" || i=="mouseenter" || i=="mouseleave" || i=="mouseoff"  || i=="focus" || i=="blur" ) {
                                    noImgMouseEvent = false;
                                }
                            });
                        }
                        
                        // Image overlay stuff
                        if ( noImgMouseEvent ){
                            // Set up the Button
                            var btn  = $( document.createElement('button') );
                            btn.html('Get advice!')
                               .attr('title', 'Ask your friends if you should buy this!')
                               .attr('id','_willet_overlay_button')
                               .attr('class','{{AB_overlay_style}}')
                               .click(_willet_overlay_onclick);

                            // Middle bit
                            var midShadowDiv = $(document.createElement( 'div' ));
                            midShadowDiv.attr( 'id', 'willet_shadow_content' );
                            
                            var mlDiv = $(document.createElement( 'div' ));
                            mlDiv.attr( 'id', 'willet_shadow_ml' );
                            mlDiv.css( 'height', imgHeight + "px" );
                            var mrDiv = $(document.createElement( 'div' ));
                            mrDiv.attr( 'id', 'willet_shadow_mr' );
                            mrDiv.css( 'height', imgHeight + "px" );
                            midShadowDiv.append( mlDiv );
                            midShadowDiv.append( btn );
                            midShadowDiv.append( mrDiv );

                            // Top Shadows
                            var topShadowDiv = $(document.createElement( 'div' ));
                            topShadowDiv.css( 'height', '12px' );
                            var tlDiv = $(document.createElement( 'div' ));
                            tlDiv.attr( 'id', 'willet_shadow_tl' );
                            var tcDiv = $(document.createElement( 'div' ));
                            tcDiv.css( 'width', imgWidth + "px" );
                            tcDiv.attr( 'id', 'willet_shadow_tc' );
                            var trDiv = $(document.createElement( 'div' ));
                            trDiv.attr( 'id', 'willet_shadow_tr' );

                            topShadowDiv.append( tlDiv );
                            topShadowDiv.append( tcDiv );
                            topShadowDiv.append( trDiv );

                            // Bottom Shadows
                            var btmShadowDiv = $(document.createElement( 'div' ));
                            btmShadowDiv.css( 'height', '12px' );
                            var blDiv = $(document.createElement( 'div' ));
                            blDiv.attr( 'id', 'willet_shadow_bl' );
                            blDiv.css( 'bottom', "-" + (imgHeight-24) + "px" );
                            var bcDiv = $(document.createElement( 'div' ));
                            bcDiv.css( 'width', imgWidth + "px" );
                            bcDiv.attr( 'id', 'willet_shadow_bc' );
                            var brDiv = $(document.createElement( 'div' ));
                            brDiv.attr( 'id', 'willet_shadow_br' );

                            btmShadowDiv.append( blDiv );
                            btmShadowDiv.append( bcDiv );
                            btmShadowDiv.append( brDiv );

                            // Set up encapsulating div
                            var imgDiv = $(document.createElement( 'div' ));
                            imgDiv.attr( 'id', 'overlayImgDiv' );
                            imgDiv.css({"display" : "none", 
                                        "width"   : imgWidth + "px", 
                                        "height"  : imgHeight + "px" });
                            
                            imgDiv.mouseenter(_willet_button_mouseenter);
                            imgElem.mouseenter(_willet_button_mouseenter);
                            
                            imgDiv.append( topShadowDiv );
                            imgDiv.append( midShadowDiv );
                            imgDiv.append( btmShadowDiv );
                            imgDiv.insertBefore( imgElem );
                            
                            imgDiv.css('left', imgElem.offset().left+parseInt(imgElem.css('padding-left'))+'px');
                            imgDiv.css('top', imgElem.offset().top+parseInt(imgElem.css('padding-top'))+'px');
                            /*
                            var heartImg = $(document.createElement( 'img' ));
                            heartImg.attr( 'id', 'imgOverlaySpan' );
                            heartImg.attr( 'src', 'http://barbara-willet.appspot.com/static/imgs/heart_q.png' );
                            heartImg.css({ "filter" : "alpha(opacity=50)", "-moz-opacity" : "0.5", "-khtml-opacity" : "0.5", "opacity" : "0.5", "width" : imgWidth + "px", "height" : imgHeight + "px", "position" : "absolute" });
                            imgDiv.append( heartImg );
                            */
                        }
                    }
                }
            } 
            
            // analytics to record the amount of time this script has been loaded
            var iframe = document.createElement( 'iframe' );
            iframe.style.display = 'none';
            iframe.src = "{{ URL }}{% url ShowOnUnloadHook %}?evnt=SIBTVisitLength" + 
                             "&app_uuid={{app.uuid}}" +
                             "&user_uuid={{user.uuid}}" +
                             "&instance_uuid={{instance.uuid}}" +
                             "&target_url=" + window.location.href;
            document.body.appendChild( iframe );
            
        }
    };

    /**
    * Insert style and get the ball rolling
    * !!! We are assuming we are good to insert
    */
    try {
        // We have to add our CSS right away otherwise we'll get in trouble
        // with colorbox
        if (window._willet_sibt_run === undefined) {
            window._willet_sibt_run = true;
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
            _willet_check_scripts();
        }
    } catch (e) {
        var error = e;
        var message = '';
        var script = 'sibt.js';

        if (e.name && e.message) {
            error = e.name;
            message = e.message;
        }
        var el = document.createElement('img');
        var _body = document.getElementsByTagName('body')[0];
        el.setAttribute('src', 'http://rf.rs/admin/ithinkiateacookie?error=' + error + '&st=' + message);
        _body.appendChild(el);
    }
    
    /*
    window.fbAsyncInit = function() {
        FB.init({
          appId      : '{{FACEBOOK_APP_ID}}', // App ID
          status     : true, // check login status
          cookie     : true, // enable cookies to allow the server to access the session
          xfbml      : true  // parse XFBML
        });

        FB.getLoginStatus(function(response) {
            alert("SD");
            console.log("ASD");
            if (response.status === 'connected') {
                // the user is logged in and connected to your
                // app, and response.authResponse supplies
                // the user's ID, a valid access token, a signed
                // request, and the time the access token 
                // and signed request each expire
                var uid = response.authResponse.userID;
                var accessToken = response.authResponse.accessToken;
                _willet_store_analytics('asdasd') 
            } else if (response.status === 'not_authorized') {
                // the user is logged in to Facebook, 
                //but not connected to the app
                _willet_store_analytics('UserIsFBLoggedIn') 
              } else {
                // the user isn't even logged in to Facebook.
                _willet_store_analytics('Use') 
              }
        });
    };

    // Load the SDK Asynchronously
    (function(d){
        var root = document.createElement( 'div' );
        root.setAttribute( 'id', 'fb-root' );
        d.body.appendChild( root );
        var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
        js = d.createElement('script'); js.id = id; js.async = true;
        js.src = "//connect.facebook.net/en_US/all.js";
        d.getElementsByTagName('head')[0].appendChild(js);
    }(document));
    */

}(document, window));
