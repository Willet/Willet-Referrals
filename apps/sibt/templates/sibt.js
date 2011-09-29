/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

var _willet_css = {% include "css/colorbox.css" %}

/**
 * quick helper function to add scripts to dom
 */
var _willet_load_remote_script = function(script) {
    var dom_el = document.createElement('script'); 
    dom_el.src = script;
    dom_el.type = 'text/javascript'; 
    document.getElementsByTagName('head')[0].appendChild(dom_el); 
    return dom_el;
}

var _willet_closeCallback = function () {
    //document.getElementById( '_willet_button' ).style.display = "none";
}

/**
 * Onclick event handler for the 'sibt' button
 */
var _willet_button_onclick = function(url) {
    //var url = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;
    $.colorbox({
        transition: 'fade',
        scrolling: false,
        iframe: true, 
        initialWidth: 0, 
        initialHeight: 0, 
        innerWidth: 420,
        innerHeight: 232, 
        callback: _willet_closeCallback, 
        href: url
    });
}

var _willet_show_vote = function(willt_code, photo_url) {
    var url = "{{URL}}/s/vote.html?willt_code=" + 
        willt_code + 
        "&is_asker={{is_asker}}&store_id={{ store_id }}&photo=" + 
        photo_url + 
        "&url=" + window.location.href;
    console.log('showing colorbox for url, image', willt_code, photo_url, url);
    //$.colorbox.init();
    $.colorbox({
        transition: 'fade',
        scrolling: false, 
        iframe: true,
        width: '690px',
        height: '90%',
        initialWidth: 0, 
        initialHeight: 0,
        href: url
    });
}

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
}

/**
 * Main script to run
 */
var _willet_run_scripts = function() {
    console.log('running');
    var button      = document.createElement('a');
    var hash        = window.location.hash;
    var hash_search = '#code=';
    var photo_src = $('#image img').attr('src'); 

    var hash_index = hash.indexOf(hash_search);
    if ({{show_votes}} || hash_index != -1) {
        var willt_code = hash.substring(hash_index + hash_search.length , hash.length);
        _willet_show_vote(willt_code, photo_src);
    }
    
    /*
    if ( {{show_votes}} || hash.indexOf( '#code=' ) != -1 ) {
        var willt_code = hash.substring( hash.length - 1, hash.length );
        url = "{{URL}}/s/vote.html?willt_code=" + willt_code + "&is_asker={{is_asker}}&store_id={{ store_id }}&photo=" + photo.src + "&url=" + window.location.href;
        colorBoxStr = "$.colorbox({ scrolling: false, iframe:true, width:'690px', height:'90%', callback: _willet_closeCallback, href:'" + url + "' })";
        
        showVote( willt_code, photo.src );
        
        button.innerText = 'Should your friend buy this?';
        button.innerHTML = 'Should your friend buy this?';

    } else {

        url = "{{URL}}/s/ask.html?store_id={{ store_id }}&photo=" + photo.src + "&url=" + window.location.href;
        colorBoxStr = "$.colorbox({ scrolling: false, iframe:true, innerWidth:420, innerHeight:232, callback: _willet_closeCallback, href:'" + url + "' })";
        button.innerText = 'Not Sure? Ask your friends';
        button.innerHTML = 'Not Sure? Ask your friends';
    }
    */
    // Construct button.
    var url = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;
    button.innerText = 'Not Sure?<br />Ask your friends';
    button.innerHTML = 'Not Sure?<br />Ask your friends';
    button.setAttribute( 'class', 'button' );
    button.setAttribute( 'style', 'display:none; margin: 15px 15px 15px 15px; font-size: 12pt; cursor: pointer;' );
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', '_willet_button_onclick("'+url+'"); return false;');
    button.setAttribute( 'id', '_willet_button' );
    
    // Put button on the page.
    var purchase_cta = document.getElementById( '{{buy_btn_id}}' );
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

    if ( purchase_cta ) {
        purchase_cta.parentNode.appendChild( button );
        $("#_willet_button").fadeIn(150);
    }
}

/**
 * Insert style and get the ball rolling
 */
//var style_url = "{{URL}}/static/colorbox/example4/colorbox.css";
var _willet_style = document.createElement('style');
var _willet_head = document.getElementsByTagName('head')[0];
_willet_style.textContent = _willet_css;
_willet_head.appendChild(_willet_style);

// run our scripts
_willet_check_scripts();

