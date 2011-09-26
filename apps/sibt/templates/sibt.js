/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

var _willet_closeCallback = function () {
    document.getElementById( '_willet_button' ).style.display = "none";
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
	v_css.rel   = 'stylesheet'
	v_css.type  = 'text/css';
    v_css.media = 'screen';
	v_css.href  = p_file;
	document.getElementsByTagName('head')[0].appendChild(v_css);
};

//window.onload =  function () {
    //document.write('<link rel="stylesheet" type="text/css" href="{{URL}}/static/colorbox/example4/colorbox.css">');

    // Insert ColorBox CSS into the page
    includeCSS( "{{URL}}/static/colorbox/example4/colorbox.css" );

    var button      = document.createElement( 'a' );
    var hash        = window.location.hash;
    var url         = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;
    var colorBoxStr = "$.colorbox({ transition: 'fade', scrolling: false, iframe:true, initialWidth:0, initialHeight:0, innerWidth:420, innerHeight:232, callback: _willet_closeCallback, href:'" + url + "' })";

    // Construct button.
    button.innerText = 'Not Sure? Ask your friends';
    button.innerHTML = 'Not Sure? Ask your friends';
    button.setAttribute( 'class', 'button' );
    button.setAttribute( 'style', 'margin: 15px 15px 15px 15px' );
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', colorBoxStr);
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
        purchase_cta = document.getElementById( 'buy' );
    }
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'price' );
    }

    if ( purchase_cta ) {
        purchase_cta.parentNode.appendChild( button );
    }
//};

