/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

var _willet_closeCallback = function () {
    var button = document.getElementById( '_willet_button' );
    var hash   = window.location.hash;
    
    if ( {{show_votes}} || hash.indexOf( '#code=' ) != -1 ) {
        button.innerText = 'Should your friend buy this?';
        button.innerHTML = 'Should your friend buy this?';
    } else {
        button.innerText = 'Awaiting Friends\' Thoughts!';
        button.innerHTML = 'Awaiting Friends\' Thoughts!';
    }

    button.disabled = true;
    button.setAttribute( 'onClick', ';');

    button.style.display = "none";
};

var showVote = function( willt_code, photo_url ) {
    var url = "{{URL}}/s/vote.html?willt_code=" + willt_code + "&is_asker={{is_asker}}&store_id={{ store_id }}&photo=" + photo_url + "&url=" + window.location.href;
    $.colorbox({ transition: 'fade', scrolling: false, iframe:true, width:'690px', height:'90%', href: url });
};

window.onload =  function () {
    var colorBoxStr;
    var button       = document.createElement( 'a' );
    var hash         = window.location.hash;
    var details      = document.getElementById( 'product-details' );
    if ( !details ) {
        details      = document.getElementById( 'details' );
    }
    var productName  = getFirstChild( details, "h1", "" );
    
    var photos = document.getElementById( 'product-photos' );
    if( !photos ) {
        photos = document.getElementById( 'images' );
    }
    var productPhoto = getFirstChild( photos, "img", "" );
    
    var productDesc  = getFirstChild( details, "", "description" );
    if ( !productDesc ){
        productDesc  = getFirstChild( details, "", "desc" );
    }
    if ( !productDesc ){
        productDesc  = document.getElementById( "desc" );
    }
    
    var url          = "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;

    if ( productPhoto ) {
        url += "&productPhoto=" + productPhoto.src;
    }
    if ( productName ) {
        url += "&productName=" + productName.innerHTML;
    }   
    if ( productDesc ) {
        url += "&productDesc=" + productDesc.innerHTML;
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

    colorBoxStr = "$.colorbox({ transition: 'fade', scrolling: false, iframe:true, initialWidth:0, initialHeight:0, innerWidth:420, innerHeight:232, callback: _willet_closeCallback, href:'" + url + "' })";

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
    var purchase_cta = document.getElementById( 'purchase' );
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'price' );
    }
    if ( !purchase_cta ) {
        purchase_cta = document.getElementById( 'buy' );
    }
    purchase_cta.parentNode.appendChild( button );

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

/*




    open.setAttribute( 'href', "javascript:(function() {$.cookie('_wl_open', 'true');$('#_willet_open').animate({top: '-70px'}, 500);$('#_willet_bar').animate({top: '0px'}, 500);$('#_willet_pad').animate({height: '37px'}, 500);})();");

        var cookieVal = $.cookie('_wl_open');
        if ( cookieVal == null ) {
        } else if ( cookieVal == 'false' ) {

            */

