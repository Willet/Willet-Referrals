/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

    /* Voting Results Screen for Asker */
{% if is_asker %}



/* Voting Screen for Friends of Asker */
{% else %}  {% if show_vote %}




/* Regular Page with 'SIBT' Button */
{% else %}

window.onload =  function () {

    // Construct button.
    var button = document.createElement( 'a' );
    button.setAttribute( 'class', 'button' );
    button.setAttribute( 'style', 'margin: 5px 10px 5px 10px' );
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', '$.colorbox({ scrolling: false, iframe:true, innerWidth:420, innerHeight:232, href:"http://localhost:8080/s/ask.html?store_id={{ store_id }}" } )' );
    button.setAttribute( 'id', '_willet_button' );

    button.innerText = 'Not Sure? Ask your friends';
    button.innerHTML = 'Not Sure? Ask your friends';
    
    // Put button on the page.
    var purchase_cta = document.getElementById( 'purchase' );
    purchase_cta.parentNode.appendChild( button );
};


var _willet_closeCallback = function () {
    var button = document.getElementById( '_willet_button' );
    button.innerText = 'Awaiting Results!';
    button.innerHTML = 'Awaiting Results!';
};

var _willet_startVote = function () {
    event.preventDefault();
/*
    var iframe = document.createElement( 'iframe' );
    iframe.setAttribute( 'src', '' );
    iframe.setAttribute( 'allowtransparency', "true" );
    iframe.setAttribute( 'scrolling', "no" );
    iframe.setAttribute( 'style', "width:403px; min-height: 350px" );

    document.body.appendChild( iframe );

*/
};

{% endif %} {% endif %}
/*




    open.setAttribute( 'href', "javascript:(function() {$.cookie('_wl_open', 'true');$('#_willet_open').animate({top: '-70px'}, 500);$('#_willet_bar').animate({top: '0px'}, 500);$('#_willet_pad').animate({height: '37px'}, 500);})();");

        var cookieVal = $.cookie('_wl_open');
        if ( cookieVal == null ) {
        } else if ( cookieVal == 'false' ) {

            */

