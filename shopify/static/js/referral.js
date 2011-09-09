/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

// Example URL: https://checkout.shopify.com/orders/962072/403f3cf2ca6ec05a118864ee80ba30a5

var container   = document.getElementById( 'container' );
var main        = document.getElementById( 'main' );
var url         = location.href.split('/');
var l           = url.length;
var order_token = url[ l - 1 ]; // Last portion of URL
var store_id    = url[ l - 2 ]; // Second last portion of URL

// Make the referral iframe
var iframe      = document.createElement( 'iframe' );
iframe.setAttribute( 'allowtransparency', 'true' );
iframe.setAttribute( 'frameborder', '0' );
iframe.setAttribute( 'scrolling', 'no' );
iframe.setAttribute( 'style', 'padding: 0 15px; width:413px; min-height:340px; display: block; background: url("../images/checkout/checkout-bg-slim.gif") bottom left repeat-y' );
iframe.setAttribute( 'src', 'http://social-referral.appspot.com/shopify/load/referral?store_id=' + store_id + '&order_token=' + order_token );

// Add the div to the page
// > inserts it between the header and main content divs
container.insertBefore(iframe, main);
