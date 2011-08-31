/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

window.onload = function() {
    var tag = document.getElementById( 'tagline' );
    var content_div = document.getElementById( 'content' );
    var group_div   = content_div.children[0];
    var order_id, store_name;
    var l = group_div.children.length;

    // Find the order id number
    for ( var i = 0; i < l; i ++ ) {
        var c = group_div.children[i];
        if ( c.innerHTML.indexOf('Your Order') != -1 ){
            order_id = c.children[0].innerHTML.substring(1);
        } else if ( c.innerHTML.indexOf('shopping at') != -1 ){
            store_name = c.children[0].innerHTML;
        }
    }

    // Make the referral iframe
    var iframe = document.createElement( 'iframe' );
    iframe.setAttribute( 'allowtransparency', 'true' );
    iframe.setAttribute( 'frameborder', '0' );
    iframe.setAttribute( 'scrolling', 'no' );
    iframe.setAttribute( 'style', 'width:372px; min-height:500px;background-color: #dddddd; margin-top: 20px; margin-left: auto; margin-right: auto; ' );
    iframe.setAttribute( 'src', 'http://social-referral.appspot.com/invite?store_id=' + store_name + '&order=' + order_id );

    // Add the div to the page
    tag.appendChild( iframe );
};
