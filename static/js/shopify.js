/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

window.onload = function() {

    var content_div = document.getElementById( 'content' );
    var group_div   = content_div.children[0];
    var order_id;
    var l = group_div.children.length;

    // Find the order id number
    for ( var i = 0; i < l; i ++ ) {
        var c = group_div.children[i];
        if ( c.innerText.indexOf('Your Order') != -1 ){
            order_id = c.children[0].innerText.substring(1);
        }
    }

    // Make the referral iframe
    var iframe = document.createElement( 'iframe' );
    iframe.setAttribute( 'allowtransparency', 'true' );
    iframe.setAttribute( 'frameborder', '0' );
    iframe.setAttribute( 'scrolling', 'no' );
    iframe.setAttribute( 'style', 'width:372px; min-height:520px;' );
    iframe.setAttribute( 'src', 'http://social-referral.appspot.com/widget?ca_id=c8e166c12a2e4f19&order=' + order_id );

    // Add the div to the page
    group_div.appendChild( iframe );
};
