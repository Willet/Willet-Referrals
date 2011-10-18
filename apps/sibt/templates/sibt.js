/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

(function(document, window){
    var _willet_css = {% include stylesheet %}
    var _willet_ask_success = false;
    var _willet_is_asker = ('{{ is_asker }}' == 'True'); // did they ask?
    var _willet_show_votes = ('{{ show_votes }}' == 'True');
    var _willet_has_voted = ('{{ has_voted }}' == 'True');
    var _willet_topbar = null;

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

    var _willet_store_analytics = function () {
        var iframe = document.createElement( 'iframe' );

        iframe.style.display = 'none';
        iframe.src = "{{URL}}/s/storeAnalytics?evnt={{evnt}}" + 
                    "&target_url=" + window.location.href +
                    "&app_uuid={{app.uuid}}" +
                    "&user_uuid={{user.uuid}}";

        document.body.appendChild( iframe );
    };

    /**
    * Called when ask iframe is closed
    */
    var _willet_ask_callback = function() {
        if (_willet_ask_success) {
            _willet_is_asker = true;
            $('#_willet_button').html('Refresh the page to see your results!');
        }
    };

    /**
    * Onclick event handler for the 'sibt' button
    */
    var _willet_button_onclick = function() {
        if (_willet_is_asker || _willet_show_votes) {
            //_willet_show_vote();
            window.location.reload(true);
        } else {
            _willet_show_ask();        
        }
    };

    /**
    * shows the ask your friends iframe
    */
    var _willet_show_ask = function () {
        var url =  "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;

        $.colorbox({
            transition: 'fade',
            scrolling: false,
            iframe: true, 
            initialWidth: 0, 
            initialHeight: 0, 
            innerWidth: '450px',
            innerHeight: '240px', 
            fixed: true,
            href: url,
            onClosed: _willet_ask_callback
        });
    };

    /**
    * Shows the voting screen
    */
    var _willet_show_vote = function() {
        var photo_src = $('#image img').attr('src'); 
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);
        var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
            
        var url = "{{URL}}/s/vote.html?willt_code=" + willt_code + 
                "&is_asker={{is_asker}}&store_id={{store_id}}" +
                "&photo=" + photo_src + 
                "&instance_uuid={{instance.uuid}}" +
                "&url=" + window.location.href; 

        $.colorbox({
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
     * called when the results iframe is refreshed
     */
    var _willet_iframe_loaded = function() {
        //$('#_willet_sibt_bar div.loading').hide();
        _willet_topbar.children('div.iframe').children('div.loading').hide();
        //$('#_willet_sibt_bar').children('div.iframe').children('div.loading').hide();
        //$('#_willet_sibt_bar').children('div.iframe').children('div.loading').hide();
        $(this).css('width', $(this).parent().css('width'));
        $(this).fadeIn('fast');
    };
    
    /**
     * This would be called to show the link to this vote
     */
    var _willet_getlink = function() {

    };

    /**
    * Refreshes the results window
    */
    var _willet_refresh_results = function() {
        // TODO:
        // THIS CODE DOES NOT WORK IN SAFARI
        // FUCK SAFARI SOMETHING PAINFUL
        // DO NOT USE
        var iframe_div = _willet_topbar.children('div.iframe');//$('#_willet_sibt_bar div.iframe');
        var iframe = iframe_div.children('iframe');//$('#_willet_sibt_bar div.iframe iframe');
        var src_backup = iframe.attr('src'); 
        // hide iframe
        iframe.hide();

        iframe_div.children('div.loading').fadeIn();

        // reset iframe source
        iframe.attr('src', '');
        iframe.attr('src', src_backup);

        iframe.load(_willet_iframe_loaded);

        // show loading

        // iframe.load should already be set, iframe will show itself when ready
    };

    /**
    * Used to toggle the results view
    */
    var _willet_toggle_results = function() {
        // check if results iframe is showing
        var iframe = _willet_topbar.find('div.iframe iframe'); 
        var iframe_div = _willet_topbar.find('div.iframe'); 
        var iframe_display = iframe_div.css('display');

        if (iframe.attr('src') == undefined) {
            // iframe has no source, hasnt been loaded yet
            // and we are FOR SURE showing it
            _willet_do_vote(-1);
            $('#_willet_toggle_results span.down').hide();
            $('#_willet_toggle_results span.up').show();
        } else {
            // iframe has been loaded before
            if (iframe_display == 'none') {
                // show the iframe
                _willet_topbar.animate({height: '337px'}, 500);
                $('#_willet_toggle_results span.down').hide();
                $('#_willet_toggle_results span.up').show();
                iframe_div.fadeIn('fast');
            } else {
                // hide iframe
                $('#_willet_toggle_results span.up').hide();
                $('#_willet_toggle_results span.down').show();
                iframe_div.fadeOut('fast');
                _willet_topbar.animate({height: '40'}, 500);
            }
        }
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
        var iframe_div = _willet_topbar.find('div.iframe');//$('#_willet_sibt_bar div.iframe');
        var iframe = _willet_topbar.find('div.iframe iframe');//$('#_willet_sibt_bar div.iframe iframe');

        // constructing the iframe src
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);
        var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
        var results_src = "{{ URL }}/s/results.html?" +
            "willt_code=" + willt_code + 
            "&doing_vote=" + doing_vote + 
            "&vote_result=" + vote_result + 
            "&is_asker={{is_asker}}" +
            "&store_id={{store_id}}" +
            "&store_url={{store_url}}" +
            "&instance_uuid={{instance.uuid}}" + 
            "&url=" + window.location.href; 

        // show/hide stuff
        _willet_topbar.find('div.vote').hide();
        $('#_willet_toggle_results').show();
        if (doing_vote || _willet_has_voted) {
            _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
        } else if (_willet_is_asker) {
            _willet_topbar.find('div.message').html('Here\'s what your friends say:').fadeIn();
        }

        // start loading the iframe
        iframe.attr('src', ''); 
        iframe.attr('src', results_src); 

        // once the iframe has loaded, switch out the loading gif
        // and display the iframe with its content
        console.log('binding function to', $('#_willet_results'));
        //$('#_willet_results').load(_willet_iframe_loaded);
        //iframe.load(_willet_iframe_loaded);
        iframe.css('width', iframe.parent().css('width'));
        iframe.fadeIn('fast');

        // show the iframe div!
        _willet_toggle_results();
    };

    /**
    * Shows the vote top bar
    */
    var _willet_show_topbar = function() {
        var body = $('body'); 
        
        // create the padding for the top bar
        var padding = document.createElement('div');
        padding = $(padding);
        padding.attr('id', '_willet_padding');
        padding.css('display', 'none');

        _willet_topbar  = document.createElement('div');
        _willet_topbar = $(_willet_topbar);
        _willet_topbar.attr('id', '_willet_sibt_bar');
        _willet_topbar.css('display', "none");
        bar_html = " " +
            "<div class='asker'>" +
                "<div class='pic'>" +
                "<img src='{{ asker_pic }}' />" +
                "</div>" +
                "<div class='name'>" +
                "    &#147;I'm not sure if I should buy this.&#148;" +
                "</div>" +
            "</div>" +
            "<div class='message'>Should <em>{{ asker_name }}</em> Buy This?</div>" +
            "<div class='vote last' style='display: none'>" +
            "    <button id='yesBtn' class='yes'>" +
            "        Buy it "+
            "    </button> "+
            "    <button id='noBtn' class='no'> "+
            "        Skip it "+
            "    </button> "+
            "</div> "+
            "<div id='_willet_toggle_results' class='button toggle_results last' style='display: none'> "+
            "    <span class='down'>" +
            "      Show <img src='{{URL}}/static/imgs/arrow-down.gif' /> "+
            "   </span> "+
            "   <span class='up' style='display: none'>" +
            "      Hide <img src='{{URL}}/static/imgs/arrow-up.gif' /> "+
            "   </span> "+
            "</div>"+
            "<div id='_willet_refresh_results' class='last' style='display: none'> "+
            "    <span class='refresh'>" +
            "      &nbsp;<img alt='Refresh voting' title='Refresh voting' src='{{URL}}/static/imgs/refresh.gif' />&nbsp;"+
            "   </span> "+
            "</div> "+
            "<div id='_willet_getlink_results' class='last' style='display: none'> "+
            "    <span class='getlink'>" +
            "      &nbsp;<img alt='Invite a friend to vote' title='Invite a friend to vote' src='{{URL}}/static/imgs/paper-clip.gif' />&nbsp;"+
            "   </span> "+
            "   <div id='_willet_sharelink'>Invite a friend to vote:<br />"+
            "       <input type='text' readonly='reaodnly value='{{ share_url }}' />'"+
            "   </div> "+
            "</div> "+
            "<div class='clear'></div> "+
            "<div class='iframe' style='display: none'> "+
            "    <div style='display: none' class='loading'><img src='{{URL}}/static/imgs/ajax-loader.gif' /></div>"+
            "    <iframe id='_willet_results' height='280' width='100%' frameBorder='0' ></iframe> "+ 
            "</div>";
        _willet_topbar.html(bar_html);
        body.prepend(padding);
        body.prepend(_willet_topbar);

        // bind event handlers
        //$('#_willet_refresh_results').click(_willet_refresh_results);
        $('#_willet_toggle_results').click(_willet_toggle_results);
        $('#yesBtn').click(_willet_do_vote_yes);
        $('#noBtn').click(_willet_do_vote_no);
    
        if (_willet_show_votes && !_willet_has_voted && !_willet_is_asker) {
            // show voting!
            _willet_topbar.find('div.vote').show();
        } else if (_willet_has_voted && !_willet_is_asker) {
            _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
            _willet_topbar.children('div.button').fadeIn();
        } else if (_willet_is_asker) {
            // showing top bar to asker!
            _willet_topbar.find('div.message')
                .html('See what your friends say!')
                .css('cursor', 'pointer')
                .click(_willet_toggle_results)
                .fadeIn();
            _willet_topbar.children('div.button').fadeIn();
        }
        padding.show(); 
        _willet_topbar.slideDown('slow');
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
            'name': 'jQuery',
            'url': 'https://social-referral.appspot.com/static/js/jquery.min.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof jQuery == 'function');
            }, 'callback': function() {
                return;
            }
        }, {
            'name': 'jQuery Colorbox',
            'url': 'https://social-referral.appspot.com/static/js/jquery.colorbox-min.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof jQuery == 'function' && typeof jQuery.colorbox == 'function');
            }, 'callback': function() {
                jQuery.colorbox.init();
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
                    //console.log('script already loaded', row.name);
                    row.callback();
                    row.loaded = true;
                    row.dom_el = true;
                } else {
                    //console.log('loading remote script', row.name);
                    row.dom_el = _willet_load_remote_script(row.url);
                }
            }
            if (row.loaded == false) {
                if (row.test()) {
                    // script is now loaded!
                    //console.log('script has been loaded', row.name);
                    row.callback();
                    row.loaded = true;
                } else {
                    all_loaded = false;
                }
            }   
        }

        if (all_loaded) {
            _willet_run_scripts();
        } else {
            window.setTimeout(_willet_check_scripts,100);
        }
    };

    /**
    * Main script to run
    */
    var _willet_run_scripts = function() {
        //console.log('running');
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);

        // Show the vote fast
        if (_willet_show_votes || hash_index != -1) {
            //_willet_show_vote();
            _willet_show_topbar();
        } else {
            // ONLY SHOW THE BUTTON IF WE ARE NOT SHOWING THE BAR!!!
            var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
            var button       = document.createElement('a');
            
            button.setAttribute('class', 'button');
            button.setAttribute('style', 'display: none'); 
            button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
            button.setAttribute( 'value', '' );
            //button.setAttribute( 'onClick', '_willet_button_onclick(); return false;');
            button.setAttribute( 'id', '_willet_button' );
            
            // Construct button.
            if (_willet_is_asker) {
                $(button).html('See what your friends said');
            } else if (_willet_show_votes) {
                // not the asker but we are showing votes
                $(button).html('Help {{ asker_name }} by voting!');
            } else {
                $(button).html( "{{AB_CTA_text}}" );
            }
            $(purchase_cta).append(button);
            $(button).click(_willet_button_onclick);
            $(button).fadeIn(250).css('display', 'inline-block');
            
            // watch for message
            // Create IE + others compatible event handler
            var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
            var eventer = window[eventMethod];
            var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";

            // Listen to message from child window
            eventer(messageEvent,function(e) {
                //console.log('parent received message!:  ',e.data);
                if (e.data == 'shared') {
                    _willet_ask_success = true;
                } else if (e.data == 'close') {
                    // the iframe wants to be closed
                    // ... maybe it's emo
                    $.colorbox.close();
                }
            }, false);
        } // else
    };

    /**
    * Insert style and get the ball rolling
    */
    try {
        var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
        
        if ( purchase_cta ) {
            var _willet_style = document.createElement('style');
            var _willet_head  = document.getElementsByTagName('head')[0];
            _willet_style.type = 'text/css';
            _willet_style.setAttribute('charset','utf-8');
            _willet_style.setAttribute('media','all');
            if (_willet_style.styleSheet) {
                _willet_style.styleSheet.cssText = _willet_css;
            } else {
                var rules = document.createTextNode(_willet_css);
                _willet_style.appendChild(rules);
            }
            _willet_head.appendChild(_willet_style);
            
            // run our scripts
            _willet_check_scripts();

            _willet_store_analytics();
        }
    } catch (err) {
        // this defines printStackTrace
        // there was an error
        var st = printStackTrace();
        var el = document.createElement('img');
        var _body = document.getElementsByTagName('body')[0];
        el.setAttribute('src', 'http://rf.rs/admin/ithinkiateacookie?error=' + err + '&st=' + st);
        _body.appendChild(el);
    }
}(document, window));

