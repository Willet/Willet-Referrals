/**
 * Buttons JS
 */
(function () {
    var here = window.location + '.json';
    var console = ( typeof(window.console) === 'object' 
                 && typeof(window.console.log) === 'function' 
                 && typeof(window.console.error) ==='function' ) 
                    ? window.console 
                    : { log: function () {}, error: function () {} };
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
            'name': 'json',
            'url': 'http://cdnjs.cloudflare.com/ajax/libs/json2/20110223/json2.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof(window.JSON) === 'object' && typeof(window.JSON.parse) === 'function');
            },
            'callback': function() {}
        }
    ];

    var _init_buttons = function(data) {
        /* data is product json 
         */
        console.log("Buttons: finding buttons placeholder on page");
        /**
         * INSERT IFRAME WITH DATA
         */
        var button_div = document.getElementById('_willet_buttons_app');

        if (button_div && window._willet_iframe_loaded == undefined) {
            console.log("Buttons: found placeholder, attaching iframe");

            button_div.setAttribute('style',"float: left; height: 30px; padding: 5px;");

            window._willet_iframe_loaded = "teh fb_iframe haz been loaded";
            var domain = /:\/\/([^\/]+)/.exec(window.location.href)[1];

            // Grab the photo
            var photo = '';
            if ( data.product.images[0] != null ) {
                photo = data.product.images[0].src;
            }

            // Tumblr
            var d = document.createElement( 'div' );
            d.setAttribute('style', 'float: left; margin-right: 5px; width: 62px !important;' );
            
            var a = document.createElement( 'a' );
            var style = 
            a.href = 'http://www.tumblr.com/share';
            a.title = "Share on Tumblr";
            a.setAttribute('style', "display:inline-block; text-indent:-9999px; \
                        overflow:hidden; width:63px; height:20px; \
                        background:url('http://platform.tumblr.com/v1/share_2.png') \
                        top left no-repeat transparent; float: left; margin-right: 5px; margin-top: 3px;");
            a.innerHTML = "Share on Tumblr";
            d.appendChild( a );
            button_div.appendChild( d );

            console.log('Buttons: Tumblr attached');

            // Pinterest
            var d = document.createElement( 'div' );
            d.setAttribute('style', 'float: left; margin-right: 5px; overflow:hidden; width: 49px !important;');

            a = document.createElement( 'a' );
            var u = 
            a.href = "http://pinterest.com/pin/create/button/?" +
                    "url=" + encodeURIComponent( window.location.href ) + 
                    "&media=" + encodeURIComponent( photo ) + 
                    "&description=" + "Found on " + domain + "!";
            a.className = 'pin-it-button';
            a.setAttribute('count-layout', "horizontal");
            a.innterHTML = "Pin It";
            d.appendChild( a );
            button_div.appendChild( d );
            
            console.log("Buttons: Pinterest attached");

            // The Fancy Button
            var d = document.createElement( 'div' );
            d.setAttribute('style', 'float: left; margin-top: 3px;' );

            a = document.createElement( 'a' );
            var u = "http://www.thefancy.com/fancyit?" +
                    "ItemURL=" + encodeURIComponent( window.location.href ) + 
                    "&Title="  + encodeURIComponent( data.product.title ) +
                    "&Category=Other";
            if ( photo.length > 0 ) {
                u += "&ImageURL=" + encodeURIComponent( photo );
            } else { // If no image on page, submit blank image.
                u += "&ImageURL=" + encodeURIComponent( 'http://social-referral.appspot.com/static/imgs/noimage.png' );
            }

            a.href = u;
            a.id = 'FancyButton';
            d.appendChild( a );
            button_div.appendChild( d );

            console.log('Buttons: Fancy attached.');
            console.log('Buttons: appending button scripts');
            
            var head = document.getElementsByTagName('head')[0];
            var tmp  = document.createElement( 'script' );
            tmp.type = 'text/javascript';
            tmp.src = 'http://assets.pinterest.com/js/pinit.js';
            head.appendChild( tmp );
            
            tmp = document.createElement( 'script' );
            tmp.type = 'text/javascript';
            tmp.src = 'http://platform.tumblr.com/v1/share.js';
            head.appendChild( tmp );

            tmp = document.createElement( 'script' );
            tmp.type = 'text/javascript';
            tmp.src = 'http://www.thefancy.com/fancyit.js';
            head.appendChild( tmp );

            console.log('Buttons: scripts attached. Done!');
        } else {
            console.error('Buttons: could not find buttons placeholder on page');
        }

    };

    var _load_remote_script = function(script) {
        /**
         * quick helper function to add scripts to dom
        */
        console.log("Buttons: loading "+script);
        var dom_el  = document.createElement('script'); 
        dom_el.src  = script;
        dom_el.type = 'text/javascript'; 
        document.getElementsByTagName('head')[0].appendChild(dom_el); 
        return dom_el;
    };

    var _check_scripts = function() {
        /**
        * checkScripts checks the scripts var and uses
        * the defined `test` and `callack` methods to tell
        * when a script has been loaded and is ready to be
        * used
        */    
        var all_loaded = true;
        console.log("Buttons: Loading JSON begins");

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
                    row.dom_el = _load_remote_script(row.url);
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
            console.log("Buttons: JSON library loaded, run script");
            _run_scripts();
        } else {
            console.log("Buttons: JSON library loading...");
            window.setTimeout(_check_scripts,100);
        }
    };

    // Run once JSON is ready
    var _run_scripts = function() {
        try {
            console.log("Buttons: initiating product.json request")
            var req = new XMLHttpRequest();
            req.open('GET', here, true);
            req.onreadystatechange = function () {  
                if (req.readyState === 4) {  
                    if (req.status === 200) {
                        console.log("Buttons: recieved product.json request");
                        var data;
                        try {
                            data = JSON.parse(req.responseText);
                        } catch (e) {
                            console.error("Buttons: JSON.parse error: "+e);
                        }
                        if (data) {
                            _init_buttons(data);
                        }
                    } else {  
                        // Didn't work, just silently bail
                        console.error("Buttons: request for product.json failed");
                    }  
                }  
            };  
            req.send(null);
        } catch (e) {
            // Didn't work, just silently bail
            console.error("Buttons: "+e);
        }
    };

    if (typeof (window.JSON) === 'object' && typeof(window.JSON.parse) === 'function') {
        // let's get this party started
        console.log("Buttons: JSON found, run script");
        _run_scripts();
    } else {
        // go get JSON library
        console.log("Buttons: no JSON, load JSON");
        _check_scripts();
    }
})();
