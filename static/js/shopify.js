/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

window.onload = function() {
    alert('asdasdasd');
    var content_div = document.getElementById( 'content' );
    var group_div   = content_div.children[0];
    var order_id, store_name;
    var l = group_div.children.length;

    // Find the order id number
    for ( var i = 0; i < l; i ++ ) {
        var c = group_div.children[i];
        if ( c.innerText.indexOf('Your Order') != -1 ){
            order_id = c.children[0].innerText.substring(1);
        } else if ( c.innerText.indexOf('shopping at') != -1 ){
            store_name = c.children[0].innerText;
        }
    }

    // Make the referral iframe
    var iframe = document.createElement( 'iframe' );
    iframe.setAttribute( 'allowtransparency', 'true' );
    iframe.setAttribute( 'frameborder', '0' );
    iframe.setAttribute( 'scrolling', 'no' );
    iframe.setAttribute( 'style', 'width:372px; min-height:520px;' );
    iframe.setAttribute( 'src', 'http://localhost:8096/widget?store=' + store_name + '&order=' + order_id );

    // Add the div to the page
    group_div.appendChild( iframe );
};
