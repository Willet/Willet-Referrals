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
    
                
    bar.setAttribute( 'style', "text-align:center; position: absolute; left: 0px; top: -70px; height: 37px; width: 100%; z-index: 999998; margin-top: 0px; margin-right: 0px; margin-bottom: 0px; margin-left: 0px; padding-top: 3px; padding-right: 0px; padding-bottom: 7px; padding-left: 0px; font-family: 'Trebuchet MS', arial, helvetica, clean, sans-serif; font-size: 16px; -webkit-appearance: none; background-attachment: scroll; background-clip: border-box; background-color: #6A9912; background-image: -webkit-gradient(linear, 0% 0%, 0% 100%, from(rgb(215, 250, 150)), color-stop(0.05, rgb(171, 217, 87)), to(rgb(120, 172, 21))); background-origin: padding-box; border-bottom-color: #6A9912; border-bottom-left-radius: 3px; border-bottom-right-radius: 3px; border-bottom-style: solid; border-bottom-width: 1px; border-left-color: #7CB315; border-left-style: solid; border-left-width: 1px; border-right-color: #7CB315; border-right-style: solid; border-right-width: 1px; border-top-color: #8DCC18; border-top-left-radius: 3px; border-top-right-radius: 3px; border-top-style: solid; border-top-width: 1px; -webkit-box-shadow:0 1px 3px rgba(0,0,0,0.7); -moz-box-shadow:0 1px 3px rgba(0,0,0,0.7); box-shadow: rgb(153, 153, 153) 0px 1px 2px 0px; box-sizing: border-box; color: #FAFFF1; text-shadow: 1px 1px 1px #B3B3B3;" );

    bar.setAttribute( 'id', '_willet_bar' ); 
    
    var profile_pic = document.createElement( 'img' );
    profile_pic.setAttribute( 'src', '{{profile_pic}}' );
    profile_pic.setAttribute( 'style', '-webkit-box-shadow:0 1px 3px rgba(0,0,0,0.7); -moz-box-shadow:0 1px 3px rgba(0,0,0,0.7); box-shadow:0 1px 3px rgba(0,0,0,0.7); border-radius: 3px; border: 1px solid black; float: left; height: 27px; width: 27px; margin: 0px 20px 2px 150px' );

    var text = document.createElement( 'p' );
    text.setAttribute( 'style', 'margin-top: 5px; float: left;' );
    text.innerHTML = 'Lucky you! {{referrer_name}} left you a gift.  Purchase any item on this site to get it!';
    text.innerText = 'Lucky you! {{referrer_name}} left you a gift.  Purchase any item on this site to get it!';

    var hide = document.createElement( 'a' );
    hide.setAttribute('style', 'margin-top: 5px; margin-right: 150px; float: right; text-decoration: none; color: white;');
    hide.setAttribute('href', "javascript:(function() {$.cookie('_wl_open', 'false');$('#_willet_bar').animate({top: '-100px'}, 500);$('#_willet_pad').animate({height: '0px'}, 500);$('#_willet_open').animate({top: '0px'}, 500);})();");
    hide.innerText = 'Hide';
    hide.innerHTML = 'Hide';

    bar.appendChild( profile_pic );
    bar.appendChild( text );
    bar.appendChild( hide );

    // -------

    var open = document.createElement( 'a' );

    open.setAttribute( 'style', "height: 37px; text-decoration: none; display: block; position: absolute; top: -70px; right: 100px; z-index: 999998; line-height: 27px; height: 27px; margin: 0; padding: 0px 5px 15px 5px; width: auto; border: 0; text-align: center; font-family: 'Trebuchet MS',arial,helvetica,clean,sans-serif; font-size: 16px; color: #000; border-radius: 0 0 5px 5px; -moz-border-radius: 0 0 5px 5px; -webkit-border-radius: 0 0 5px 5px; -webkit-box-shadow:0 1px 3px rgba(0,0,0,0.7); -moz-box-shadow:0 1px 3px rgba(0,0,0,0.7); box-shadow: rgb(153, 153, 153) 0px 1px 2px 0px; box-sizing: border-box; color: #FAFFF1; -webkit-appearance: none; background-attachment: scroll; background-clip: border-box; background-color: #6A9912; background-image: -webkit-gradient(linear, 0% 0%, 0% 100%, from(rgb(215, 250, 150)), color-stop(0.05, rgb(171, 217, 87)), to(rgb(120, 172, 21))); background-origin: padding-box; border-bottom-color: #6A9912; border-bottom-left-radius: 3px; border-bottom-right-radius: 3px; border-bottom-style: solid; border-bottom-width: 1px; border-left-color: #7CB315; border-left-style: solid; border-left-width: 1px; border-right-color: #7CB315; border-right-style: solid; border-right-width: 1px;" ); 

    open.setAttribute( 'href', "javascript:(function() {$.cookie('_wl_open', 'true');$('#_willet_open').animate({top: '-70px'}, 500);$('#_willet_bar').animate({top: '0px'}, 500);$('#_willet_pad').animate({height: '37px'}, 500);})();");
    open.setAttribute( 'id', '_willet_open' );
    open.innerText = 'Remember your gift!';
    open.innerHTML = 'Remember your gift!';

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
