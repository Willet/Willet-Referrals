{{show_votes}}
{{is_asker}}

/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

var _willet_closeCallback = function () {
    var button = document.getElementById( '_willet_button' );
    button.innerText = 'Awaiting Friend\'s Thoughts!';
    button.innerHTML = 'Awaiting Friend\'s Thoughts!';

    button.disabled = true;
    button.setAttribute( 'onClick', ';');
};

var showVote = function( instance_uuid ) {
    var url = "{{URL}}/s/vote.html?instance_uuid=" + instance.uuid + "&is_asker={{is_asker}}&store_id={{ store_id }}&photo=" + photo.src + "&url=" + window.location.href;
    $.colorbox({ scrolling: false, iframe:true, innerWidth:420, innerHeight:232, href: url });

    // Hide other stuff.
    document.getElementById( 'sub-banner-wrapper' ).style.display   = 'none';
    document.getElementById( 'content-wrapper' ).style.display      = 'none';
    document.getElementById( 'footer' ).style.display               = 'none';
};

/* Voting Screen for Friends of Asker */
{% if show_vote %}
    window.onload =  function () {
        showVote( "{{instance_uuid}}" );
    };
/* Regular Page with 'SIBT' Button */
{% else %}

window.onload =  function () {
    var photo = getFirstImgChild( document.getElementById( 'product-photos' ) );
    var url = "{{URL}}/s/ask.html?store_id={{ store_id }}&photo=" + photo.src + "&url=" + window.location.href;
    var colorBoxStr = "$.colorbox({ scrolling: false, iframe:true, innerWidth:420, innerHeight:232, callback: _willet_closeCallback, href:'" + url + "' })";
    
    // Construct button.
    var button = document.createElement( 'a' );
    button.setAttribute( 'class', 'button' );
    button.setAttribute( 'style', 'margin: 5px 10px 5px 10px' );
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', colorBoxStr);
    button.setAttribute( 'id', '_willet_button' );

    button.innerText = 'Not Sure? Ask your friends';
    button.innerHTML = 'Not Sure? Ask your friends';
    
    // Put button on the page.
    var purchase_cta = document.getElementById( 'purchase' );
    purchase_cta.parentNode.appendChild( button );
};

var getFirstImgChild = function( elem ) {
    var childNodes = elem.childNodes;

    for (var i = 0; i < childNodes.length; i++) {
        var child = childNodes[i];
        if ( child.tagName == 'img' || child.tagName == "IMG" ) {
            return child;
        }
        else {
            var maybe = getFirstImgChild( child );
            if ( maybe != null ) return maybe;
        }
    }
};




{% endif %}
/*




    open.setAttribute( 'href', "javascript:(function() {$.cookie('_wl_open', 'true');$('#_willet_open').animate({top: '-70px'}, 500);$('#_willet_bar').animate({top: '0px'}, 500);$('#_willet_pad').animate({height: '37px'}, 500);})();");

        var cookieVal = $.cookie('_wl_open');
        if ( cookieVal == null ) {
        } else if ( cookieVal == 'false' ) {

            */

