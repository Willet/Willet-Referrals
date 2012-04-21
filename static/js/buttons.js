;(function () {
    /**
     * Buttons JS. Copyright Willet Inc, 2012
     */
    "use strict";
    var DEBUG = true,
        DEFAULT_COUNT = 'false',
        DEFAULT_SPACING = '5',
        DEFAULT_PADDING = '5',
        DEFAULT_BUTTONS = ['Tumblr','Fancy','Pinterest'];
    var product_json = window.location.protocol + '//' + window.location.hostname + window.location.pathname + '.json';
    var console = DEBUG && ( typeof(window.console) === 'object' 
                           && ( ( typeof(window.console.log) === 'function' 
                           && typeof(window.console.error) ==='function' )
                        || (typeof(window.console.log) === 'object' // IE 
                           && typeof(window.console.error) ==='object') ) )
                ? window.console : { log: function () {}, error: function () {} }; // debugging

    // If on /cart page, silently bail
    if (/\/cart\/?$/.test(window.location.pathname)) {
        console.log("Buttons: on cart page, not running.");
        return;
    }
    
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

    var getElemValue = function (elem, key, default_val) {
        // Tries to retrive value stored on elem as 'data-*key*' or 'button_*key*'
        return elem.getAttribute('data-'+key) || elem.getAttribute('button_'+key) || default_val || null;
    };

    var addButton = function (elem, bname, button) {
        // Assumes button has method create and attribute script
        // Appends generated button div to elem and script to head
        elem.appendChild(button.create());
        console.log('Buttons: '+ bname +' tag attached');
        var script  = document.createElement('script');
        script.type = 'text/javascript';
        script.src = button.script;
        document.getElementsByTagName('head')[0].appendChild(script);
        console.log('Buttons: '+ bname +' script appended');
    };

    var createStyle = function (rules) {
        // Returns stylesheet element
        var s = document.createElement('style');
        s.type = 'text/css';
        s.media = 'screen';
        if (s.styleSheet) {
            s.styleSheet.cssText = rules; // IE
        } else { 
            s.appendChild(document.createTextNode(rules)); // Every other browser
        }
        return s;
    };

    var getCanonicalUrl = function (default_url) {
        var links = document.getElementsByTagName('link');
        var i = links.length, url;
        while (i--) {
            if (links[i].rel === 'canonical' && links[i].href) {
                url = links[i].href;
            }
        }
        return url || default_url;
    };

    var button_div = document.getElementById('_willet_buttons_app');

    var _init_buttons = function(data) {
        console.log("Buttons: finding buttons placeholder on page");

        if (button_div && !getElemValue(button_div, 'loaded', false) ) {
            console.log("Buttons: found placeholder, attaching iframe");

            // Get options from tag
            var i, j, k, button_count, button_spacing, button_padding,
                head = document.getElementsByTagName('head')[0],
                domain = document.domain,
                protocol = window.location.protocol, //'http:'; // For local testing
                canonical_url = getCanonicalUrl(window.location.protocol
                                                +'//'
                                                +window.location.hostname
                                                +'/products/'
                                                +window.location.pathname.replace(/^(.*)?\/products\/|\/$/, '') );
                // How this regex works: replaces .../products/ or a trailing / with empty spring 
                // So /collections/this-collection/products/this-product -> this-product

            button_count = (getElemValue(button_div, 'count', DEFAULT_COUNT) === 'true');
            button_spacing = getElemValue(button_div, 'spacing', DEFAULT_SPACING)+'px';
            button_padding = getElemValue(button_div, 'padding', DEFAULT_PADDING)+'px',

            button_div.style.styleFloat = 'left'; // IE
            button_div.style.cssFloat = 'left'; // FF, Webkit
            button_div.style.minWidth = '240px';
            button_div.style.height = '22px';
            button_div.style.padding = button_padding;
            button_div.style.border = 'none';
            button_div.style.margin = '0';

            // Supported buttons
            var supported_networks = {
                "AskFriends": { // does not allow asking/voting unless SIBT-JS is also installed!
                    "create": function () {
                        var d = createButton();
                        d.id = 'mini_sibt_button';
                        d.style.cursor = 'pointer';
                        d.style.display = 'inline-block';
                        d.style.background = "url('" + protocol + "//social-referral.appspot.com/static/sibt/imgs/button_bkg.png') 3% 20% no-repeat transparent";
                        d.style.width = '80px';
                        return d;
                    },
                    "script": '//brian-willet.appspot.com/s/sibt.js?url='+canonical_url
                },
                "Facebook": {
                    "create": function () {
                        var d = createButton('facebook');
                        d.style.overflow = 'visible';
                        d.style.width = button_count ? '90px' : '48px';
                        var fb = document.createElement('div');
                        fb.className = 'fb-like';
                        fb.setAttribute('data-send', 'false');
                        fb.setAttribute('data-layout', 'button_count');
                        fb.setAttribute('data-width', (button_count ? '90' : '48') );
                        fb.setAttribute('data-show-faces', 'false');
                        fb.setAttribute('data-href',canonical_url);
                        d.appendChild(fb);
                        var s = createStyle(".fb_edge_widget_with_comment iframe { width:"+d.style.width+" !important; } "
                                      +"span.fb_edge_comment_widget.fb_iframe_widget iframe { width:401px !important; }");
                        d.appendChild(s);
                        return d;
                    },
                    "script": '//connect.facebook.net/en_US/all.js#xfbml=1'
                },
                "Fancy": {
                    "create": function () {
                        var d = createButton('fancy');
                        d.style.width = button_count ? '96px' : '57px';

                        var a = document.createElement( 'a' );
                        var u = "http://www.thefancy.com/fancyit?" +
                                "ItemURL=" + encodeURIComponent( canonical_url ) + 
                                "&Title="  + encodeURIComponent( data.product.title ) +
                                "&Category=Other";
                        if ( photo.length > 0 ) {
                            u += "&ImageURL=" + encodeURIComponent( photo );
                        } else { // If no image on page, submit blank image.
                            u += "&ImageURL=" + encodeURIComponent( 'http://social-referral.appspot.com/static/imgs/noimage.png' );
                        }

                        a.href = u;
                        a.id = 'FancyButton';
                        a.setAttribute('data-count', ( button_count ? 'true' : 'false' ));
                        d.appendChild( a );
                        return d;
                    },
                    "script": '//www.thefancy.com/fancyit.js'
                },
                "GooglePlus": {
                    "create": function () {
                        var d = createButton('googleplus');
                        d.style.overflow = 'visible';
                        d.style.width = button_count ? '74px' : '32px';
                        var g = document.createElement("div");
                        g.className = 'g-plusone';
                        g.setAttribute("data-size", "medium");
                        g.setAttribute("data-annotation", (button_count ? "bubble" : "none"));
                        g.setAttribute('data-href', canonical_url);
                        d.appendChild(g);
                        // Google is using the Open Graph spec
                        var t, p, 
                            m = [ { property: 'og:title', content: data.product.title },
                                  { property: 'og:image', content: photo },
                                  { property: 'og:description', content: 'I found this on '+ domain } ]
                        while (m.length) {
                            p = m.pop();
                            t = document.createElement('meta');
                            t.setAttribute('property', p.property);
                            t.setAttribute('content', p.content);
                            head.appendChild(t);
                        }
                        return d;
                    },
                    "script": '//apis.google.com/js/plusone.js'
                },
                "Pinterest": {
                    "create": function () {
                        var d = createButton('pinterest');
                        d.style.width = button_count ? '77px' : '43px';

                        var a = document.createElement( 'a' );
                        a.href = "http://pinterest.com/pin/create/button/?" +
                                "url=" + encodeURIComponent( canonical_url ) + 
                                "&media=" + encodeURIComponent( photo ) + 
                                "&description=" + encodeURIComponent("I found this on " + domain);
                        a.className = 'pin-it-button';
                        a.setAttribute('count-layout', button_count ? "horizontal" : "none");
                        a.innerHTML = "Pin It";
                        d.appendChild(a);
                        return d;
                    },
                    "script": '//assets.pinterest.com/js/pinit.js'
                },
                "Svpply": {
                    "create": function () {
                        // Svpply assumes it has to wait for window.onload before running
                        // But window.onload has already fired at this point
                        // So set up polling for when Svpply is ready, then fire it off
                        var interval = setInterval(function () {
                            if (window.svpply_api && window.svpply_api.construct) {
                                window.svpply_api.construct();
                                clearInterval(interval);
                            }
                        }, 100);
                        var d = createButton('svpply');
                        var sv = document.createElement("sv:product-button");
                        sv.setAttribute("type", "boxed");
                        sv.style.width = '70px';
                        d.appendChild(sv);
                        return d;
                    },
                    "script": '//svpply.com/api/all.js#xsvml=1'
                },
                "Twitter": {
                    "create": function () {
                        var d = createButton('twitter');
                        d.style.width = button_count ? '100px' : '56px';
                        var a = document.createElement('a');
                        a.href = 'https://twitter.com/share';
                        a.className = 'twitter-share-button';
                        a.setAttribute('data-lang','en');
                        a.setAttribute('data-url', canonical_url);
                        if (!button_count) {
                            a.setAttribute('data-count', 'none');
                        }
                        d.appendChild(a);
                        return d;
                    },
                    "script": '//platform.twitter.com/widgets.js'
                },
                "Tumblr": {
                    "create": function () {
                        var d = createButton('tumblr');
                        d.style.width = '62px';
                        
                        var a = document.createElement( 'a' );
                        a.href = 'http://www.tumblr.com/share';
                        a.title = "Share on Tumblr";
                        a.style.display = 'inline-block';
                        a.style.textIndent = '-9999px';
                        a.style.textAlign = 'left';
                        a.style.width = '63px';
                        a.style.height = '20px';
                        a.style.background = "url('http://platform.tumblr.com/v1/share_2.png') top left no-repeat transparent";
                        a.style.styleFloat = 'left'; // IE
                        a.style.cssFloat = 'left'; // FF, Webkit
                        a.style.marginRight = '5px';
                        a.style.marginTop = '0';
                        a.innerHTML = "Share on Tumblr";
                        d.appendChild( a );
                        return d;
                    },
                    "script": '//platform.tumblr.com/v1/share.js'
                }
            };
            
            var createButton = function (id) {
                id = id || '';
                var d = document.createElement('div');
                d.style.styleFloat = 'left'; // IE
                d.style.cssFloat = 'left'; // FF, Webkit
                d.style.marginTop = '0';
                d.style.marginLeft = '0';
                d.style.marginBottom = '0';
                d.style.marginRight = button_spacing;
                d.style.paddingTop = '0';
                d.style.paddingBottom = '0';
                d.style.paddingLeft = '0';
                d.style.paddingRight = '0';
                d.style.border = 'none';
                d.style.display = 'block';
                d.style.visibility = 'visible';
                d.style.height = '21px';
                d.style.position = 'relative'; // Need this child positioning
                d.style.overflow = 'hidden';
                d.name = 'button';
                d.id = '_willet_'+id;
                d.className = '_willet_social_button';
                return d;
            };

            // Grab the photo
            var photo = '';
            if ( data.product.images[0] != null ) {
                photo = data.product.images[0].src;
            }
            
            // Get the buttons, should be children of #_willet_buttons_app
            //      ex: <div>Facebook</div>
            var req_buttons = [];
            if (button_div.childNodes.length > 0) {
                // Search for supported buttons
                i = button_div.childNodes.length;
                while (i--) {
                    j = button_div.childNodes[i];
                    if (j.nodeType === 1) {
                        k = j.innerHTML;
                        if (supported_networks[k]) {
                            req_buttons.push(k);
                        }
                    }
                    button_div.removeChild(button_div.childNodes[i]);
                }
            } else {
                // default for backwards compatibilty
                var req_buttons = DEFAULT_BUTTONS;
            }
            
            // Create buttons & add activating scripts!
            var j = req_buttons.length;
            while (j--) {
                try {
                    addButton(button_div, req_buttons[j], supported_networks[req_buttons[j]]);
                } catch (e) {
                    console.error('Buttons: '+req_buttons[j]+' encountered error: '+e);
                }
            }

            // Make visible if hidden
            button_div.style.display = 'block';
            // Set to loaded
            button_div.setAttribute('data-loaded', true);

            // If Facebook is already loaded,
            // trigger it to enable Like button
            try {
                window.FB && window.FB.XFBML.parse(); 
            } catch(e) {}

            console.log('Buttons: Done!');
        } else {
            console.log('Buttons: could not find buttons placeholder on page');
        }

    };

    // Get product info, then load scripts
    (function() {
        try {
            console.log("Buttons: initiating product.json request")
            var req = new XMLHttpRequest();
            req.open('GET', product_json, true);
            req.onreadystatechange = function () {  
                if (req.readyState === 4) {
                    // 4 means something has been returned by the request
                    if (req.status === 200) {
                        // 200 -> HTTP Status OK
                        console.log("Buttons: recieved product.json request");
                        var data;
                        try {
                            data = JSON.parse(req.responseText);
                        } catch (e) {
                            console.log("Buttons: could not parse product info, stopping.");
                            return;
                        }
                        if (data) {
                            // Proceed!
                            _init_buttons(data);
                        } else {
                            console.log("No data");
                        }
                    } else {  
                        // Didn't work, just silently bail
                        console.log("Buttons: request for product.json failed");
                    }
                } else {
                    console.log("state is not 4 yet");
                }
            };
            req.send(null);
        } catch (e) {
            // Didn't work, just silently bail
            console.log("Buttons: "+e);
        }
    })();
})();
