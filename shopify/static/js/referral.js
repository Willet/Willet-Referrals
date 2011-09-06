/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

window.onload = function() {
    // Example URL: https://checkout.shopify.com/orders/962072/403f3cf2ca6ec05a118864ee80ba30a5

    var tag = document.getElementById( 'tagline' );
    var url = location.href.split('/');
    var l   = url.length;
    var order_token = url[ l - 1 ]; // Last portion of URL
    var store_id    = url[ l - 2 ]; // Second last portion of URL

    // Make the referral iframe
    var iframe = document.createElement( 'iframe' );
    iframe.setAttribute( 'allowtransparency', 'true' );
    iframe.setAttribute( 'frameborder', '0' );
    iframe.setAttribute( 'scrolling', 'no' );
    iframe.setAttribute( 'style', 'padding: 10px 10px 10px 10px; width:375px; min-height:340px; border: 1px solid #dddddd; background-color: #dddddd; margin-top: 20px; margin-left: 10px;' );
    iframe.setAttribute( 'src', 'http://social-referral.appspot.com/shopify/load/referral?store_id=' + store_id + '&order_token=' + order_token );

    // Add the div to the page
    tag.appendChild( iframe );
};
