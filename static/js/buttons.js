/**
 * Buttons JS. Copyright Willet Inc, 2012
 */
<<<<<<< HEAD
=======
(function () {
    var here = window.location + '.json';
    var console = ( typeof(window.console) === 'object' 
                 && typeof(window.console.log) === 'function' 
                 && typeof(window.console.error) ==='function' ) 
                    ? window.console 
                    : { log: function () {}, error: function () {} };
    
    var JSON;if(!JSON){JSON={};}
    /* JSON2, Author: Douglas Crockford, http://www.JSON.org/json2.js */
    (function(){'use strict';function f(n){return n<10?'0'+n:n;}
    if(typeof Date.prototype.toJSON!=='function'){Date.prototype.toJSON=function(key){return isFinite(this.valueOf())?this.getUTCFullYear()+'-'+
    f(this.getUTCMonth()+1)+'-'+
    f(this.getUTCDate())+'T'+
    f(this.getUTCHours())+':'+
    f(this.getUTCMinutes())+':'+
    f(this.getUTCSeconds())+'Z':null;};String.prototype.toJSON=Number.prototype.toJSON=Boolean.prototype.toJSON=function(key){return this.valueOf();};}
    var cx=/[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,escapable=/[\\\"\x00-\x1f\x7f-\x9f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g,gap,indent,meta={'\b':'\\b','\t':'\\t','\n':'\\n','\f':'\\f','\r':'\\r','"':'\\"','\\':'\\\\'},rep;function quote(string){escapable.lastIndex=0;return escapable.test(string)?'"'+string.replace(escapable,function(a){var c=meta[a];return typeof c==='string'?c:'\\u'+('0000'+a.charCodeAt(0).toString(16)).slice(-4);})+'"':'"'+string+'"';}
    function str(key,holder){var i,k,v,length,mind=gap,partial,value=holder[key];if(value&&typeof value==='object'&&typeof value.toJSON==='function'){value=value.toJSON(key);}
    if(typeof rep==='function'){value=rep.call(holder,key,value);}
    switch(typeof value){case'string':return quote(value);case'number':return isFinite(value)?String(value):'null';case'boolean':case'null':return String(value);case'object':if(!value){return'null';}
    gap+=indent;partial=[];if(Object.prototype.toString.apply(value)==='[object Array]'){length=value.length;for(i=0;i<length;i+=1){partial[i]=str(i,value)||'null';}
    v=partial.length===0?'[]':gap?'[\n'+gap+partial.join(',\n'+gap)+'\n'+mind+']':'['+partial.join(',')+']';gap=mind;return v;}
    if(rep&&typeof rep==='object'){length=rep.length;for(i=0;i<length;i+=1){if(typeof rep[i]==='string'){k=rep[i];v=str(k,value);if(v){partial.push(quote(k)+(gap?': ':':')+v);}}}}else{for(k in value){if(Object.prototype.hasOwnProperty.call(value,k)){v=str(k,value);if(v){partial.push(quote(k)+(gap?': ':':')+v);}}}}
    v=partial.length===0?'{}':gap?'{\n'+gap+partial.join(',\n'+gap)+'\n'+mind+'}':'{'+partial.join(',')+'}';gap=mind;return v;}}
    if(typeof JSON.stringify!=='function'){JSON.stringify=function(value,replacer,space){var i;gap='';indent='';if(typeof space==='number'){for(i=0;i<space;i+=1){indent+=' ';}}else if(typeof space==='string'){indent=space;}
    rep=replacer;if(replacer&&typeof replacer!=='function'&&(typeof replacer!=='object'||typeof replacer.length!=='number')){throw new Error('JSON.stringify');}
    return str('',{'':value});};}
    if(typeof JSON.parse!=='function'){JSON.parse=function(text,reviver){var j;function walk(holder,key){var k,v,value=holder[key];if(value&&typeof value==='object'){for(k in value){if(Object.prototype.hasOwnProperty.call(value,k)){v=walk(value,k);if(v!==undefined){value[k]=v;}else{delete value[k];}}}}
    return reviver.call(holder,key,value);}
    text=String(text);cx.lastIndex=0;if(cx.test(text)){text=text.replace(cx,function(a){return'\\u'+
    ('0000'+a.charCodeAt(0).toString(16)).slice(-4);});}
    if(/^[\],:{}\s]*$/.test(text.replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g,'@').replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g,']').replace(/(?:^|:|,)(?:\s*\[)+/g,''))){j=eval('('+text+')');return typeof reviver==='function'?walk({'':j},''):j;}
    throw new SyntaxError('JSON.parse');};}}());


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
>>>>>>> 4d2fa59... JSON added to buttons.js for faster loading

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
            var button_div = document.getElementById('_willet_buttons_app');

            if (button_div && window.iframe_loaded == undefined) {
                $(button_div).css( {"float"   : "left",
                                    "height"  : "30px",
                                   // "width"   : "225px",
                                    "padding" : "5px"} );

                window.iframe_loaded = "teh fb_iframe haz been loaded";
                var domain = /:\/\/([^\/]+)/.exec(window.location.href)[1];

<<<<<<< HEAD
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
                        "&description=" + "Found on " + domain + "!";
                $(a).attr( 'href', u );
                $(a).attr( 'class', 'pin-it-button' );
                $(a).attr( 'count-layout', "horizontal" );
                $(a).html = "Pin It";
                d.appendChild( a );
                button_div.appendChild( d );

                // The Fancy Button
                var d = document.createElement( 'div' );
                $(d).attr('style', 'float: left; margin-top: 3px;' );

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

=======
    };

    // Get product info, then load scripts
    (function() {
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
                            return;
                        }
                        if (data) {
                            // Proceed!
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
    })();
})();
>>>>>>> 4d2fa59... JSON added to buttons.js for faster loading
