/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

window.onload = {

    var content_div = document.getElementById( 'content' );
    var group_div   = content_div.children[0];
    var order_id;

    // Find the order id number
    for ( c in group_div.children ) {
        if ( c.innerHTML.indexOf('Your Order') != -1 ){
            order_id = c.children[0].innerText;
        }
    }

    var iframe = document.createElemebt( 'iframe' );
    iframe.setAttribute( 'allowtransparency', 'true' );
    iframe.setAttribute( 'frameborder', '0' );
    iframe.setAttribute( 'scrolling', 'no' );
    iframe.setAttribute( 'style', 'width:372px; min-height:520px;' );
    iframe.setAttribute( 'src', 'http://social-referral.appspot.com/widget?ca_id=c8e166c12a2e4f19&order=' + order_id );

    content_div.appendChild( iframe );
};
