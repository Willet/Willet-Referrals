/** Willet Referral Shopify App
  * Copyright 2011, Willet, Inc.
 **/

window.onload = function() {
    var heading = document.body.firstChild; //getElementById( 'header' );
    
    var pad  = document.createElement( 'div' );
    pad.setAttribute( 'style', 'height: 0px; display: block;' );
    pad.setAttribute( 'id', '_willet_pad' );
    
    // -------

    var bar  = document.createElement( 'div' );
    bar.setAttribute( 'style', "-webkit-box-shadow:0 1px 3px rgba(0,0,0,0.7); -moz-box-shadow:0 1px 3px rgba(0,0,0,0.7); box-shadow:0 1px 3px rgba(0,0,0,0.7); text-align:center; background-color: #b9b900; background:#b9b900; background:-webkit-gradient(linear,left top,left bottom,from(yellow),to(#b9b900)); background:-moz-linear-gradient(top,yellow,#b9b900); background:transparent\9; filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='yellow',endColorstr='#b9b900'); -ms-filter:'progid:DXImageTransform.Microsoft.gradient(startColorstr=\'yellow\',endColorstr=\'#b9b900\')'; -webkit-user-select:none;-ms-user-select:none;-moz-user-select:none;-o-user-select:none;user-select:none;cursor:default; position: absolute; left: 0px; top: -70px; height: 37px; width: 100%; z-index: 999998; margin-top: 0px; margin-right: 0px; margin-bottom: 0px; margin-left: 0px; padding-top: 3px; padding-right: 0px; padding-bottom: 7px; padding-left: 0px; border-top-width: 0px; border-right-width: 0px; border-bottom-width: 0px; border-left-width: 0px; border-style: initial; border-color: initial; text-align: center; font-family: 'Trebuchet MS', arial, helvetica, clean, sans-serif; font-size: 16px; color: rgb(0, 0, 0);" ); bar.setAttribute( 'id', '_willet_bar' ); 
    
    var profile_pic = document.createElement( 'img' );
    profile_pic.setAttribute( 'src', '{{profile_pic}}' );
    profile_pic.setAttribute( 'style', '-webkit-box-shadow:0 1px 3px rgba(0,0,0,0.7); -moz-box-shadow:0 1px 3px rgba(0,0,0,0.7); box-shadow:0 1px 3px rgba(0,0,0,0.7); border-radius: 3px; border: 1px solid black; float: left; height: 37px; margin: 0px 20px 2px 150px' );

    var text = document.createElement( 'p' );
    text.setAttribute( 'style', 'margin-top: 10px; float: left;' );
    text.innerHTML = 'Lucky you! {{referrer_name}} left you a gift.  Purchase any item on this site to get it!';

    var hide = document.createElement( 'a' );
    hide.setAttribute('style', 'margin-top: 10px; margin-right: 125px; float: right; text-decoration: none; color: black;');
    hide.setAttribute('href', "javascript:(function() {$.cookie('_wl_open', 'false');$('#_willet_bar').animate({top: '-100px'}, 500);$('#_willet_pad').animate({height: '0px'}, 500);$('#_willet_open').animate({top: '0px'}, 500);})();");
    hide.innerText = 'Hide';

    var burst = document.createElement( 'img' );
    burst.setAttribute( 'src', "http://social-referral.appspot.com/static/imgs/burst.png" );
    burst.setAttribute( 'style', "position: absolute; top: -90px; right: -100px; height: 200px;" );

    var gift = document.createElement( 'img' );
    gift.setAttribute( 'src', "http://social-referral.appspot.com/static/imgs/gift_box.gif" );
    gift.setAttribute( 'style', "position: absolute; top: 0px; right: 0px; height: 50px;");
    
    bar.appendChild( profile_pic );
    bar.appendChild( text );
    bar.appendChild( hide );
    bar.appendChild( burst );
    bar.appendChild( gift );

    // -------

    var open = document.createElement( 'a' );

    open.setAttribute( 'style', "-webkit-box-shadow:0 1px 3px rgba(0,0,0,0.7); -moz-box-shadow:0 1px 3px rgba(0,0,0,0.7); box-shadow:0 1px 3px rgba(0,0,0,0.7);text-decoration: none; display: block; position: absolute; top: -70px; right: 10px; z-index: 999998; line-height: 27px; height: 27px; background-color: #b9b900; background:#b9b900; background:-webkit-gradient(linear,left top,left bottom,from(yellow),to(#b9b900)); background:-moz-linear-gradient(top,yellow,#b9b900); background:transparent\9; filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='yellow',endColorstr='#b9b900'); -ms-filter:'progid:DXImageTransform.Microsoft.gradient(startColorstr=\'yellow\',endColorstr=\'#b9b900\')'; -webkit-user-select:none;-ms-user-select:none;-moz-user-select:none;-o-user-select:none;user-select:none;cursor:default; margin: 0; padding: 3px 5px 7px 5px; width: auto; border: 0; text-align: center; font-family: 'Trebuchet MS',arial,helvetica,clean,sans-serif; font-size: 16px; color: #000; border-radius: 0 0 5px 5px; -moz-border-radius: 0 0 5px 5px; -webkit-border-radius: 0 0 5px 5px;" ); 
    open.setAttribute( 'href', "javascript:(function() {$.cookie('_wl_open', 'true');$('#_willet_open').animate({top: '-70px'}, 500);$('#_willet_bar').animate({top: '0px'}, 500);$('#_willet_pad').animate({height: '37px'}, 500);})();");
    open.setAttribute( 'id', '_willet_open' );
    open.innerText = 'Remember your gift!';


    {% if show_gift %}
        // Now put the elems in the page.
        document.body.insertBefore( pad, heading );
        document.body.insertBefore( bar, heading );
        document.body.insertBefore( open, heading );

        var cookieVal = $.cookie('_wl_open');
        if ( cookieVal == null ) {
            $('#_willet_pad').animate({height: '37px'}, 500);
            $('#_willet_open').animate({top: '-70px'}, 500);
            $('#_willet_bar').animate({top: '0px'}, 500);
        } else if ( cookieVal == 'false' ) {
            open.style.top = '0px';
            bar.style.top  = '-100px';
        } else {
            bar.style.top    = '0px';
            pad.style.height = '37px';
        }
    {% endif %}
};
