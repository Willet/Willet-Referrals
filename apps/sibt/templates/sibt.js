/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

var _willet_css = {% include "css/colorbox.css" %}

var _willet_is_asker    = false;
var _willet_show_votes  = false;
var _willet_ask_success = false;

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

var _willet_add_other_instance = function(instance) {
    /**
     * this method will be used if a user has multiple
     * "sibt" instances for a given product page.
     * Currently this functionality is not implemented in the backend
     */
    var el = document.createElement('img');
    el = $(el);
    el.attr('src', instance.src);
    el.attr('title', 'Should ' + instance.user_name + ' buy this?');
    el.attr('data-item', instance.code);
    el.click(function() {
        var code = $(this).attr('data-item');
        var photo_src = $('#image img').attr('src'); 
        _willet_show_vote();
    });
    
    return el;
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

/**
 * Called when ask iframe is closed
 */
var _willet_ask_callback = function() {
    if (_willet_ask_success) {
        _willet_is_asker = true;
        $('#_willet_button').html('See if your friends have voted');
    }
};

/**
 * Onclick event handler for the 'sibt' button
 */
var _willet_button_onclick = function() {
    if (_willet_is_asker || _willet_show_votes) {
        // instead of showing vote again, let's show the results
        _willet_show_vote();
    } else {
        $.colorbox({
            inline: true,
            href: "#_willet_askIframe",
            transition: 'fade',
            scrolling: false,
            initialWidth: 0, 
            initialHeight: 0, 
            innerWidth: '420px',
            innerHeight: '232px', 
            fixed: true,
            onClosed: _willet_ask_callback
        });
    }
};

var _willet_show_vote = function() {
    //$.colorbox.init();
    $.colorbox({
        inline: true,
        href: "#_willet_voteIframe",
        transition: 'fade',
        scrolling: true, 
        initialWidth: 0, 
        initialHeight: 0,
        innerWidth: '635px',
        innerHeight: '90%',
        fixed: true,
        onClosed: _willet_vote_callback
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
                console.log('script already loaded', row.name);
                row.callback();
                row.loaded = true;
                row.dom_el = true;
            } else {
                console.log('loading remote script', row.name);
                row.dom_el = _willet_load_remote_script(row.url);
            }
        }
        if (row.loaded == false) {
            if (row.test()) {
                // script is now loaded!
                console.log('script has been loaded', row.name);
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
    console.log('running');
    var ask_div     = document.createElement( 'div' );
    var vote_div    = document.createElement( 'div' );
    var ask_iframe  = document.createElement( 'iframe' );
    var vote_iframe = document.createElement( 'iframe' );
    var button      = document.createElement('a');
    var photo_src = $('#image img').attr('src'); 
    var hash        = window.location.hash;
    var hash_search = '#code=';
    var hash_index  = hash.indexOf(hash_search);
    var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
    
    _willet_is_asker = (parseInt('{{ is_asker }}') == 1); // did they ask?
    _willet_show_votes = (parseInt('{{ show_votes }}') == 1);


    
    // Construct button.
    if (_willet_is_asker) {
        $(button).html('See what your friends said');
    } else if (_willet_show_votes) {
        // not the asker but we are showing votes
        $(button).html('Help {{ asker_name }} by voting!');
    } else {
        $(button).html('Not sure?&nbsp;Ask your friends!');
    }
   
    button.setAttribute('class', 'button');
    button.setAttribute('style', 'display: none'); 
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', '_willet_button_onclick(); return false;');
    button.setAttribute( 'id', '_willet_button' );
    
    // Put button on the page.
    var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
    if (purchase_cta) {
        $(purchase_cta).append(button);
        //purchase_cta.parentNode.appendChild( button );
        $("#_willet_button").fadeIn(250).css('display', 'inline-block');
        
        // watch for message
        // Create IE + others compatible event handler
        var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
        var eventer = window[eventMethod];
        var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";

        // Listen to message from child window
        eventer(messageEvent,function(e) {
            console.log('parent received message!:  ',e.data);
            if (e.data == 'shared') {
                _willet_ask_success = true;
            } else if (e.data == 'close') {
                // the iframe wants to be closed
                // ... maybe it's emo
                $.colorbox.close();
            }
        }, false);
    }

    // Construct iframes and hide them in the page (ie. cache)
    ask_div.style.display  = "none";
    vote_div.style.display = "none";

    ask_iframe.setAttribute( 'id', '_willet_askIframe' );
    ask_iframe.setAttribute( 'width', '420px' );
    ask_iframe.setAttribute( 'height', '232px' );
    
    vote_iframe.setAttribute( 'id', '_willet_voteIframe' );
    vote_iframe.setAttribute( 'width', '635px' );
    vote_iframe.setAttribute( 'height', '90%' );

    ask_iframe.src  = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;
    vote_iframe.src = "{{URL}}/s/vote.html?willt_code=" + willt_code + 
                       "&is_asker={{is_asker}}&store_id={{store_id}}&photo=" + 
                       photo_src + "&url=" + window.location.href;
    // Attach to page
    ask_div.appendChild( ask_iframe );
    vote_div.appendChild( vote_iframe );

    document.body.appendChild( ask_div );
    document.body.appendChild( vote_div );

    if (_willet_show_votes || hash_index != -1) {
        _willet_show_vote();
    }
};

/**
 * Insert style and get the ball rolling
 */
var _willet_style = document.createElement('style');
var _willet_head  = document.getElementsByTagName('head')[0];
_willet_style.textContent = _willet_css;
_willet_head.appendChild(_willet_style);

// run our scripts
_willet_check_scripts();

