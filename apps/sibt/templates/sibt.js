/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

var _willet_css = {% include "css/colorbox.css" %}

var _willet_is_asker = false;
var _willet_show_votes = false;
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
    var el = document.createElement('img');
    el = $(el);
    el.attr('src', instance.src);
    el.attr('title', 'Should ' + instance.user_name + ' buy this?');
    el.attr('data-item', instance.code);
    el.click(function() {
        var code = $(this).attr('data-item');
        var photo_src = $('#image img').attr('src'); 
        _willet_show_vote(code, photo_src);
    });
    
    return el;
};

/**
 * Called when the vote iframe is closed
 */
var _willet_vote_callback = function () {
    var button = $('#_willet_button');
    var original_shadow = button.css('box-shadow');
    var glow_timeout = 400;

    var resetGlow = function() {
        button.css('box-shadow', original_shadow);
    };
    if (_willet_show_vote && !_willet_is_asker) {
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
var _willet_button_onclick = function(url) {
    if (_willet_is_asker || _willet_show_votes) {
        // instead of showing vote again, let's show the results
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index = hash.indexOf(hash_search);
        var willt_code = hash.substring(hash_index + hash_search.length , hash.length);
        var photo_src = $('#image img').attr('src'); 
        _willet_show_vote(willt_code, photo_src);
    } else {
        $.colorbox({
            transition: 'fade',
            scrolling: false,
            iframe: true, 
            initialWidth: 0, 
            initialHeight: 0, 
            innerWidth: 420,
            innerHeight: 232, 
            href: url,
            onClosed: _willet_ask_callback
        });
    }
};

var _willet_show_vote = function(willt_code, photo_url) {
    var url = "{{URL}}/s/vote.html?willt_code=" + 
        willt_code + 
        "&is_asker={{is_asker}}&store_id={{store_id}}&photo=" + 
        photo_url + 
        "&url=" + window.location.href;
    console.log('showing colorbox for url, image', willt_code, photo_url, url);
    //$.colorbox.init();
    $.colorbox({
        transition: 'fade',
        scrolling: true, 
        iframe: true,
        width: '700px',
        height: '90%',
        initialWidth: 0, 
        initialHeight: 0,
        href: url,
        onClosed: _willet_vote_callback
    });
};

/**
 * Scripts to load into the dom
 *   name - name of the script
 *   url - url of script
 *   dom_el - dom element once inserted
 *   loaded - script has been loaded
 *   test - method to test if it has been loaded
 *   callback - callback after test is success
 */
var scripts = [
    {
        'name': 'jQuery',
        'url': 'http://rf.rs/static/js/jquery.min.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            return (typeof jQuery == 'function');
        }, 'callback': function() {
            return;
        }
    }, {
        'name': 'jQuery Colorbox',
        'url': 'http://rf.rs/static/js/jquery.colorbox-min.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            return (typeof jQuery == 'function' && typeof jQuery.colorbox == 'function');
        }, 'callback': function() {
            jQuery.colorbox.init();
        }
    }
];

/**
 * checkScripts checks the scripts var and uses
 * the defined `test` and `callack` methods to tell
 * when a script has been loaded and is ready to be
 * used
 */
var _willet_check_scripts = function() {
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
    var button      = document.createElement('a');
    var hash        = window.location.hash;
    var hash_search = '#code=';
    var photo_src = $('#image img').attr('src'); 
    
    _willet_is_asker = (parseInt('{{ is_asker }}') == 1); // did they ask?
    _willet_show_votes = (parseInt('{{ show_votes }}') == 1);

    var hash_index = hash.indexOf(hash_search);
    if (_willet_show_votes || hash_index != -1) {
        var willt_code = hash.substring(hash_index + hash_search.length , hash.length);
        _willet_show_vote(willt_code, photo_src);
    }
    
    // Construct button.
    var url = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;

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
    button.setAttribute( 'onClick', '_willet_button_onclick("'+url+'"); return false;');
    button.setAttribute( 'id', '_willet_button' );
    
    // Put button on the page.
    var purchase_cta = document.getElementById( '_willet_shouldIBuyThisButton');
    /*
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'purchase' );
    }
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'add' );
    }
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'add-to-cart' );
    }
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'buy' );
    }
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'price' );
    }
    */
    if (purchase_cta) {
        $(purchase_cta).append(button);
        //purchase_cta.parentNode.appendChild( button );
        $("#_willet_button").fadeIn(250).css('display', 'inline-block');
        
        // watch for message
        $(window).live('message', function(e) {
            if (e.data == 'shared') {
               _willet_ask_success = true;
            }
        });
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

