/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

{% include "js/jquery.min.js" %}
{% include "js/jquery.colorbox.js" %}

var _willet_closeCallback = function () {
    //document.getElementById( '_willet_button' ).style.display = "none";
};

var getFirstChild = function( elem, tagName, className ) {
    var childNodes = elem.childNodes;

    for (var i = 0; i < childNodes.length; i++) {
        
        var child = childNodes[i];
        if ( tagName.length > 0 && child.nodeName.toUpperCase() == tagName.toUpperCase() ) {
            return child;
        } else if ( className.length > 0 ) {
            c = elem.getAttribute("class");
            c = " "+ c + " ";
            if ( c.indexOf(" " + className + " ") > -1 ) {
                return child;
            }
        }
        else {
            var maybe = getFirstChild( child, tagName, className );
            if ( maybe != null ) return maybe;
        }
    }
};

function includeCSS(p_file) {
	var v_css   = document.createElement('link');
    v_css.setAttribute('rel', 'stylesheet');
    v_css.setAttribute('type', 'text/css');
    v_css.setAttribute('media', 'screen');
    v_css.setAttribute('href', p_file);
	document.getElementsByTagName('head')[0].appendChild(v_css);
};

/**
 * Onclick event handler for the 'sibt' button
 */
var _willet_button_onclick = function() {
    var url = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;
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

/**
 * Main script to run
 */
var run_scripts = function() {
    console.log('running scripts');
    var button      = document.createElement('a');
    var hash        = window.location.hash;

    // Construct button.
    button.innerText = 'Not Sure? Ask your friends';
    button.innerHTML = 'Not Sure? Ask your friends';
    button.setAttribute( 'class', 'button' );
    button.setAttribute( 'style', 'display:none; margin: 15px 15px 15px 15px; font-size: 0.7em;' );
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', '_willet_button_onclick(); return false;');
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
var style_url = "{{URL}}/static/colorbox/example4/colorbox.css";
var style = document.createElement('style');
var head = document.getElementsByTagName('head')[0];
style.textContent = '@import "' + style_url + '"';
head.appendChild(style);

var style_timeout = setInterval(function() {
  try {
    style.sheet.cssRules; // <--- MAGIC: only populated when file is loaded
    clearInterval(style_timeout);
    
    // style is loaded
    run_scripts();
  } catch (e) {
    console.log('rules failed', e);
  }
}, 10);  

