/**
 * Buttons JS
 */

/**
* quick helper function to add scripts to dom
*/
var _willet_load_remote_script = function(script) {
    var dom_el  = document.createElement('script'); 
    dom_el.src  = script;
    dom_el.type = 'text/javascript'; 
    document.getElementsByTagName('head')[0].appendChild(dom_el); 
    return dom_el;
};

var scripts = [
/**
* Scripts to load into the dom
*   name - name of the script
*   url - url of script
*   dom_el - dom element once inserted
*   loaded - script has been loaded
*   test - method to test if it has been loaded
*   callback - callback after test is success
*/
    {
        'name': 'jQuery',
        'url': 'http://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            return (typeof jQuery == 'function')
        }, 'callback': function() {
            // HACKETY HACK HACK
            $ = jQuery;
        }
    }
];

var _willet_check_scripts = function() {
    /**
    * checkScripts checks the scripts var and uses
    * the defined `test` and `callack` methods to tell
    * when a script has been loaded and is ready to be
    * used
    */    
    var all_loaded = true;

    for (i = 0; i < scripts.length; i++) {
        var row  = scripts[i];
        if (row.dom_el == null) {
            // insert the script into the dom
            if (row.test()) {
                // script is already loaded!
                row.callback();
                row.loaded = true;
                row.dom_el = true;
            } else {
                row.dom_el = _willet_load_remote_script(row.url);
            }
        }
        if (row.loaded == false) {
            if (row.test()) {
                // script is now loaded!
                row.callback();
                row.loaded = true;
            } else {
                all_loaded = false;
            }
        }   
    }

    if (all_loaded) {
        // let's actually get this party started 
        _willet_run_scripts();
    } else {
        window.setTimeout(_willet_check_scripts,100);
    }
};

/**
 * body of code to run when all scripts have been injected
 */
var _willet_run_scripts = function() {
    // get the button where we are going to insert
    var here = window.location + '.json';
    var $    = jQuery;

    jQuery.getJSON (
        here,
        function(data) {
            // callback function
            var head = document.getElementsByTagName('head')[0];
            var tmp  = document.createElement( 'script' );
            $(tmp).attr( 'type', 'text/javascript' );
            $(tmp).attr( 'src', 'http://assets.pinterest.com/js/pinit.js' );
            head.appendChild( tmp );
            
            tmp = document.createElement( 'script' );
            $(tmp).attr( 'type', 'text/javascript' );
            $(tmp).attr( 'src', 'http://platform.tumblr.com/v1/share.js' );
            head.appendChild( tmp );

            tmp = document.createElement( 'script' );
            $(tmp).attr( 'type', 'text/javascript' );
            $(tmp).attr( 'src', 'http://www.thefancy.com/fancyit.js' );
            head.appendChild( tmp );

            /**
             * INSERT IFRAME WITH DATA
             */
            var button_div = document.getElementById('{{ app.button_selector }}');

            if (button_div && window.iframe_loaded == undefined) {
                $(button_div).css( {"float"   : "left",
                                    "height"  : "30px",
                                    "width"   : "225px",
                                    "padding" : "5px"} );

                window.iframe_loaded = "teh fb_iframe haz been loaded";
                      
                // Grab the photo
                var photo = '';
                if ( data.product.images[0] != null ) {
                    photo = data.product.images[0].src;
                }

                // Tumblr
                var d = document.createElement( 'div' );
                $(d).attr('style', 'float: left; margin-right: 5px; width: 62px !important;' );
                
                var a = document.createElement( 'a' );
                var style = "display:inline-block; text-indent:-9999px; " +
                            "overflow:hidden; width:63px; height:20px; " + 
                            "background:url('http://platform.tumblr.com/v1/" + 
                            "share_2.png') top left no-repeat transparent; float: left; margin-right: 5px; margin-top: 3px;" 
                $(a).attr( 'href', 'http://www.tumblr.com/share' );
                $(a).attr( 'title', "Share on Tumblr" );
                $(a).attr( 'style', style);
                $(a).html = "Share on Tumblr";
                d.appendChild( a );
                button_div.appendChild( d );

                // Pinterest
                var d = document.createElement( 'div' );
                $(d).attr('style', 'float: left; margin-right: 5px; overflow:hidden; width: 49px !important;' );

                a = document.createElement( 'a' );
                var u = "http://pinterest.com/pin/create/button/?" +
                        "url=" + encodeURIComponent( window.location.href ) + 
                        "&media=" + encodeURIComponent( photo ) + 
                        "&description=" + "Found on {{domain}}!";
                $(a).attr( 'href', u );
                $(a).attr( 'class', 'pin-it-button' );
                $(a).attr( 'count-layout', "horizontal" );
                $(a).html = "Pin It";
                d.appendChild( a );
                button_div.appendChild( d );

                // The Fancy Button
                var d = document.createElement( 'div' );
                $(d).attr('style', 'float: left; margin-top: 3px; width: 97px !important;' );

                a = document.createElement( 'a' );
                var u = "http://www.thefancy.com/fancyit?" +
                        "ItemURL=" + encodeURIComponent( window.location.href ) + 
                        "&Title="  + encodeURIComponent( data.product.title ) +
                        "&Category=Other";
                if ( photo.length > 0 ) {
                    u += "&ImageURL=" + encodeURIComponent( photo );
                } else { // If no image on page, submit blank image.
                    u += "&ImageURL=" + encodeURIComponent( '{{URL}}/static/imgs/noimage.png' );
                }

                $(a).attr( 'href', u );
                $(a).attr( 'id', 'FancyButton' );
                d.appendChild( a );
                button_div.appendChild( d ); 

                            }
        }
    );
};

// let's start to get this party started 
_willet_check_scripts();

