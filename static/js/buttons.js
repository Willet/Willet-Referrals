/*
 * Buttons JS. Copyright Willet Inc, 2012
 * 
 */
;// Source: JSON2, Author: Douglas Crockford, http://www.JSON.org/json2.js
var JSON;if(!window.JSON){window.JSON={};}
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

var _willet = window._willet || {};
_willet.buttonsLoaded = _willet.buttonsLoaded || false;

_willet.util = {
    "addListener": function (elem, event, callback) {
        if (elem && elem.addEventListener) {
            elem.addEventListener(event, callback);
        } else if (elem && elem.addEvent) {
            elem.addEvent('on'+event, callback);
        }
    },
    "createBasicButton": function (params) {
        // Returns a DOM element
        var id = params.id || '';
        var buttonAlignment = params.buttonAlignment || "left";
        var buttonSpacing = params.buttonSpacing || "0";

        var d = document.createElement("div");
        d.style.styleFloat = buttonAlignment; //IE
        d.style.cssFloat = buttonAlignment; //FF, Webkit
        d.style.marginTop = "0";
        d.style.marginLeft = "0";
        d.style.marginBottom = "0";
        d.style.marginRight = buttonSpacing;
        d.style.paddingTop = "0";
        d.style.paddingLeft = "0";
        d.style.paddingBottom = "0";
        d.style.paddingRight = "0";
        d.style.border = "none";
        d.style.display = "block";
        d.style.visibility = "visible";
        d.style.height = "21px";
        d.style.position = "relative"; // Need this child positioning
        d.style.overflow = "hidden";

        d.name = "button";
        d.id = "_willet_" + id;
        d.className = "_willet_social_button";

        return d;
    },
    "createStyle": function (rules) {
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
    },
    "dictToArray": function (dict) {
        // Don't use this on DOM Elements, IE will fail
        var result = [];
        for (var key in dict) {
            if (dict.hasOwnProperty(key)) {
                result.push({ "key": key, "value": dict[key] });
            }
        }
        return result;
    },
    "getCanonicalUrl": function (default_url) {
        // Tries to retrieve a canonical link from the header
        // Otherwise, returns default_url
        var url,
            links = document.getElementsByTagName('link'),
            i = links.length;
        while (i--) {
            if (links[i].rel === 'canonical' && links[i].href) {
                url = links[i].href;
            }
        }
        return url || default_url;
    },
    "getElemValue": function (elem, key, default_val) {
        // Tries to retrive value stored on elem as 'data-*key*' or 'button_*key*'
        return elem.getAttribute('data-'+key) || elem.getAttribute('button_'+key) || default_val || null;
    },
    "indexOf": function (arry, obj, start) {
        // IE < 9 doesn't have Array.prototype.indexOf
        // Don't use on strings, all browsers have String.prototype.indexOf
        for (var i = (start || 0), j = arry.length; i < j; i++) {
            if (arry[i] === obj) { return i; }
        }
        return -1;
    },
    "removeChildren": function(elem) {
        // Removes all children elements from DOM element
        var i = elem.childNodes.length;
        while (i--) {
            elem.removeChild(elem.childNodes[i]);
        }
    },
    "xHasKeyY": function (dict, key) {
        return dict[key] ? true : false;
    },
    "isDictEmpty": function(dict) {
        var prop;
        for (prop in dict) {
            if (dict.hasOwnProperty(prop)) {
                return true;
            }
        }
        return false;
    },
    "getInternetExplorerVersion": function() {
        // Returns the version of Internet Explorer or a -1
        // (indicating the use of another browser).

        // http://msdn.microsoft.com/en-us/library/ms537509.aspx
        var rv = 999; // Return value assumes failure.
        if (navigator.appName == 'Microsoft Internet Explorer') {
            var ua = navigator.userAgent;
            var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
            if (re.exec(ua) != null)
                rv = parseFloat( RegExp.$1 );
        }
        return rv;
    }
};

_willet.cookies = {
    // Generic cookie library
    // Source: http://www.quirksmode.org/js/cookies.html
    "create": function (name, value, days) {
        if (days) {
            var date = new Date();
            date.setTime(date.getTime()+(days*24*60*60*1000));
            var expires = "; expires="+date.toGMTString();
        }
        else var expires = "";
        document.cookie = name+"="+value+expires+"; path=/";
    },
    "read": function (name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for(var i=0;i < ca.length;i++) {
            var c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
        }
        return null;
    },
    "erase": function (name) {
        _willet.cookies.create(name,"",-1);
    }
};

_willet.debug = (function (willet) {
    var util = willet.util,
        me = {},
        isDebugging = false,
        callbacks = [],
        log_array = [],
        _log = function() { log_array.push(arguments); },
        _error = function() { log_array.push(arguments); };

    if (typeof(window.console) === 'object' 
        && ( ( typeof(window.console.log) === 'function'
        && typeof(window.console.error) ==='function' )
        || (typeof(window.console.log) === 'object' // IE 
        && typeof(window.console.error) ==='object') )) {
        _log = function () {
            if (window.console.log.apply) {
                window.console.log.apply(window.console, arguments);
            } else {
                window.console.log(arguments);
            }
            log_array.push(arguments); // Add to logs
        };
        _error = function () {
            if (window.console.error.apply) {
                window.console.error.apply(window.console, arguments);
            } else {
                window.console.error(arguments);
            }
            log_array.push(arguments); // Add to logs
        };
    }

    me.register = function(callback) {
        // Register a callback to fire when debug.set is called
        callbacks.push(callback);
    };

    me.set = function(debug) {
        // Set debugging on (true) / off (false)
        me.log = (debug) ? _log : function() { log_array.push(arguments) };
        me.error = (debug) ? _error : function() { log_array.push(arguments) };
        isDebugging = debug;

        for(var i = 0; i < callbacks.length; i++) {
            callbacks[i](debug);
        }
    };

    me.isDebugging = function() {
        // True = printing to console & logs, False = only logs
        return isDebugging;
    };

    me.logs = function () {
        // Returns as list of all log & error items
        return log_array;
    };

    me.set(false); //setup proper log functions

    return me;
}(_willet));

_willet.messaging = (function (willet) {
    var debug = willet.debug,
        util = willet.util,
        me = {};

    me.ajax = function(config) {
        var AJAX_RESPONSE_AVAILABLE = 4;
        var HTTP_OK = 200;

        var url = config.url || "";
        var success = config.success || function() {};
        var error = config.error || function() {};
        var method = config.method || "GET";
        var async = config.async || true;

        if (url === "") {
            debug.error("Messaging: No URL provided");
            error();
        }

        if (typeof XMLHttpRequest == "undefined") {
            XMLHttpRequest = function () {
                try { return new ActiveXObject("Msxml2.XMLHTTP.6.0"); } catch (e) {}
                try { return new ActiveXObject("Msxml2.XMLHTTP.3.0"); } catch (e) {}
                try { return new ActiveXObject("Microsoft.XMLHTTP"); } catch (e) {}
                throw new Error("This browser does not support XMLHttpRequest.");
            };
        }

        var request = new XMLHttpRequest();
        request.open(method, url, async);
        request.onreadystatechange = function () {
            if (request.readyState === AJAX_RESPONSE_AVAILABLE) {
                if (request.status === HTTP_OK) {
                    success(request);
                } else {
                    error(request);
                }
            }
        };
        request.send(null);
    };

    me.xd = (function(){
        var xd = {};

        var PAYLOAD_IDENTIFIER = "willet";
        var MESSAGE_TOKEN = "message";

        var stopCommunication;

        var parseMessage = function (hash) {
            if (typeof(hash) === 'string' && hash.substr(0, 7) === '#willet') {
                var splitHash = hash.split("?" + MESSAGE_TOKEN + "=");

                if(splitHash.length) {
                    var dataJSONString = splitHash[1];
                    var data = JSON.parse(dataJSONString);
                    return data;
                }
            }
            return {};
        };

        /*
            sendMessage is always called from the child window (e.g. iframe)
            messages are always assumed to be JSON of the following form:
                {
                     "event": "?", //the name of an event
                     "message": "" //valid JSON
                }
        */
        xd.sendMessage = function(message, targetOrigin) {
            var target = targetOrigin || "*";
            var payload = "#" + PAYLOAD_IDENTIFIER + "?";
            if (!message) {
                debug.log("Messaging.XD: No message provided");
                return;
            }

            payload += MESSAGE_TOKEN + "=" + JSON.stringify(message);
            
            debug.log("Messaging.XD: Sending payload..." + payload);
            if (window.parent.postMessage) {
                // Try HTML5 postMessage
                window.parent.postMessage(payload, target);
            } else {
                // Try hash manipulation
                window.parent.location.hash = payload;
            }
        };

        // sets up message handling
        xd.createMessageHandler = function(callback, url) {
            var baseUrl = /https?:\/\/([^\/]+)/.exec(url)[0];

            if (window.postMessage) {
                // Note: IE w/ HTML5 supports addEventListener
                var listener = function (event) {
                    if (event.origin === baseUrl) {
                        var data = parseMessage(event.data);
                        callback(data);
                    }
                };

                if (window.addEventListener) {
                    window.addEventListener('message', listener, false); //Standard method
                } else {
                    window.attachEvent('onmessage', listener); //IE
                }

                stopCommunication = function() {
                     if(window.removeEventListener) {
                        window.removeEventListener('message', listener, false); //Standard method
                     } else {
                        window.detachEvent('onmessage', listener); //IE
                     }
                }
            } else {
                // Set up window.location.hash polling
                // Expects hash messages of the form:
                //  #willet?message=____
                var interval = setInterval(function () {
                    var hash = window.location.hash;
                    callback(parseMessage(hash));
                }, 1000);

                stopCommunication = function () {
                    clearInterval(interval);
                };
            }

            //create the iframe
            var originDomain = /https?:\/\/([^\/]+)/.exec(window.location.href)[0];
            var iframe = document.createElement("iframe");
            iframe.src = url + "?origin=" + originDomain + (debug.isDebugging()? "#debug" : "");
            iframe.style.display = "none";

            document.body.appendChild(iframe);
        };

        return xd;
    }());

    return me;
}(_willet));

_willet.networks = (function (willet) {
    // List of supported networks with required functions to initialize their buttons
    //
    // Format for social network:
    // name: {
    //      detect: {
    //          method: <string> "api" | "image" | "none"
    //          func: <function> for method api, will call button api
    //                           for method image, will return an image url
    //                           for method none, empty function
    //                           takes inputs methods
    //      }
    //      button: {
    //          script: <string> url for script that will load the button
    //          create: <function> function which creates the button, takes inputs methods & params
    //          onLoad: <function> (optional) function which fires when the script is loaded
    //      }
    // }
    var debug     = willet.debug,
        messaging = willet.messaging,
        util      = willet.util;
    return {
        "Facebook": {
            "priority": 2,
            "detect": {
                "method": "api",
                "func": function(methods) {
                    messaging.xd.createMessageHandler(function(data) {
                        var message = data && data.message || {};
                        var status = (message.Facebook && message.Facebook.status) || false; //use status, if it exists
                        methods.updateLoggedInStatus("Facebook", status);
                    }, willet.APP_URL + "/static/plugin/html/detectFB.html");
                }
            },
            "button": {
                "script": '//connect.facebook.net/en_US/all.js#xfbml=1',
                "create": function(methods, params) {
                    var button = util.createBasicButton({
                        "id": 'facebook',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.overflow = "visible";
                    button.style.width = params.buttonCount ? '90px' : '48px';
                    var fb = document.createElement('div');
                    fb.className = 'fb-like';
                    fb.setAttribute('data-send', 'false');
                    fb.setAttribute('data-layout', 'button_count');
                    fb.setAttribute('data-width', (params.buttonCount ? '90' : '48'));
                    fb.setAttribute('data-show-faces', 'false');
                    fb.setAttribute('data-href', params.canonicalUrl);
                    var style = util.createStyle(".fb_edge_widget_with_comment iframe { width:"+button.style.width+" !important; } "
                             +"span.fb_edge_comment_widget.fb_iframe_widget iframe { width:401px !important; }");
                    button.appendChild(fb);
                    button.appendChild(style);

                    return button;
                },
                "onload": function(methods, params) {
                    FB.Event.subscribe('edge.create', function(response) {
                        methods.itemShared("Facebook", params);
                    });
                    // If Facebook is already loaded,
                    // trigger it to enable Like button
                    try {
                        window.FB && window.FB.XFBML.parse(); 
                    } catch(e) {}
                }
            }
        },
        "Fancy": {
            "priority": 6,
            "detect": {
                "method": "none",
                "func": function(methods) { return ""; }
            },
            "button": {
                "script": '//www.thefancy.com/fancyit.js',
                "create": function(methods, params) {
                    var button = util.createBasicButton({
                        "id": 'fancy',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.width = params.buttonCount ? '90px' : '57px';

                    var u = "http://www.thefancy.com/fancyit?"
                          + "ItemURL=" + encodeURIComponent( params.canonicalUrl )
                          + "&Title="  + encodeURIComponent( params.data.product.title )
                          + "&Category=Other";
                    if ( params.photo.length > 0 ) {
                        u += "&ImageURL=" + encodeURIComponent( params.photo );
                    } else { // If no image on page, submit blank image.
                        u += "&ImageURL=" + encodeURIComponent( 'http://social-referral.appspot.com/static/imgs/noimage.png' );
                    }

                    var link = document.createElement("a");
                    link.id = "FancyButton";
                    link.href = u;

                    link.onclick = function() {
                        methods.itemShared("Fancy", params);
                    };
                    
                    link.setAttribute('data-count', ( params.buttonCount ? 'true' : 'false' ));
                    button.appendChild(link);
                    return button;
                }
            }
        },
        "GooglePlus": {
            "priority": 4,
            "detect": {
                "method": "image",
                "func": function(methods) { return "https://plus.google.com/up/?continue=https://www.google.com/intl/en/images/logos/accounts_logo.png&type=st&gpsrc=ogpy0"; }
            },
            "button": {
                "script": '//apis.google.com/js/plusone.js',
                "create": function(methods, params) {
                    var button = util.createBasicButton({
                        "id": 'googleplus',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.overflow = 'visible';
                    button.style.width = params.buttonCount ? '90px' : '32px';

                    var gPlus = document.createElement("div");
                    gPlus.className = 'g-plusone';
                    gPlus.setAttribute("data-size", "medium");
                    gPlus.setAttribute("data-annotation", (params.buttonCount ? "bubble" : "none"));
                    gPlus.setAttribute('data-href', params.canonicalUrl);
                    gPlus.setAttribute("data-callback", "_willet_GooglePlusShared");

                    button.appendChild(gPlus);

                    // Google Plus will only execute a callback in the global namespace, so expose this one...
                    // https://developers.google.com/+/plugins/+1button/#plusonetag-parameters
                    window._willet_GooglePlusShared = function(response) {
                        if (response && response.state && response.state === "on") {
                            methods.itemShared("GooglePlus", params);
                        }
                    };
                    
                    // Google is using the Open Graph spec
                    var t, p, 
                        m = [ { property: 'og:title', content: params.data.product.title },
                              { property: 'og:image', content: params.photo },
                              { property: 'og:description', content: params.sharingMessage } ];
                    while (m.length) {
                        p = m.pop();
                        t = document.createElement('meta');
                        t.setAttribute('property', p.property);
                        t.setAttribute('content', p.content);
                        document.getElementsByTagName('head')[0].appendChild(t);
                    }
                    return button;
                }
            }
        },
        "Pinterest": {
            "priority": 1,
            "detect": {
                "method": "image",
                "func": function(methods) { return "https://pinterest.com/login/?next=http://assets.pinterest.com/images/error_404_icon.png"; }
            },
            "button": {
                // Workaround until Pinterest has an API:
                // http://stackoverflow.com/questions/9622503/pinterest-button-has-a-callback
                "script": '//assets.pinterest.com/js/pinit.js',
                "create": function(methods, params) {
                    var button = util.createBasicButton({
                        "id": 'pinterest',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.width = params.buttonCount ? '90px' : '43px';

                    var link = document.createElement("a");
                    link.className = 'willet-pinterest-button';
                    link.innerHTML = "Pin It";
                    link.style.position = 'absolute';
                    link.style.top = '0';
                    link.style.left = '0';
                    link.style.font = "11px Arial, sans-serif";
                    link.style.textIndent = "-9999em";
                    link.style.fontSize = ".01em";
                    link.style.color = "#CD1F1F";
                    link.style.height = "20px";
                    link.style.width = "43px";
                    link.style.zIndex = "100";
                    link.onclick = function() {
                        methods.itemShared("Pinterest", params);
                        window.open("//pinterest.com/pin/create/button/?" +
                            "url=" + encodeURIComponent( params.canonicalUrl ) + 
                            "&media=" + encodeURIComponent( params.photo ) + 
                            "&description=" + encodeURIComponent(params.sharingMessage),
                            'signin',
                            'height=300,width=665');
                        link.className = 'willet-pinterest-button clicked';
                        return false;
                    };
                    var style = util.createStyle("a.willet-pinterest-button { "
                                                +"   background-image: url('http://assets.pinterest.com/images/pinit6.png'); "
                                                +"   background-position: 0 -7px; "
                                                +"} "
                                                +"a.willet-pinterest-button:hover { background-position: 0 -28px; cursor: hand; } "
                                                +"a.willet-pinterest-button:active { background-position: 0 -49px; cursor: hand; } "
                                                +"a.willet-pinterest-button.clicked { background-position: 0 -70px !important; }");
                    button.appendChild(link);
                    button.appendChild(style);

                    if (params.buttonCount) {
                        // Hidden under link is a Pinterest button with the count visible
                        var count = document.createElement('div');
                        count.style.position = 'relative';
                        count.style.zIndex = "0";
                        count.style.height = "20px";
                        count.style.width = '77px';
                        var countLink = document.createElement("a");
                        countLink.href = "//pinterest.com/pin/create/button/?" +
                            "url=" + encodeURIComponent( params.canonicalUrl ) + 
                            "&media=" + encodeURIComponent( params.photo ) + 
                            "&description=" + encodeURIComponent(params.sharingMessage);
                        countLink.className = 'pin-it-button';
                        countLink.setAttribute('count-layout', 'horizontal');
                        count.appendChild(countLink);
                        button.appendChild(count);
                    }
                    return button;
                }
            }
        },
        "Svpply": {
            "priority": 5,
            "detect": {
                "method": "none",
                "func": function(methods) { return ""; }
            },
            "button": {
                "script": '//svpply.com/api/all.js#xsvml=1',
                "create": function (methods, params) {
                    var button = util.createBasicButton({
                        "id": 'svpply',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.width = params.buttonCount ? '90px' : '70px';

                    var sv = document.createElement("sv:product-button");
                    sv.setAttribute("type", "boxed");

                    button.appendChild(sv);
                    // Svpply assumes it has to wait for window.onload before running
                    // But window.onload has already fired at this point
                    // So set up polling for when Svpply is ready, then fire it off
                    var interval = setInterval(function () {
                        if (window.svpply_api && window.svpply_api.construct) {
                            window.svpply_api.construct();
                            button.onclick = function () { methods.itemShared("Svpply", params); };
                            clearInterval(interval);
                        }
                    }, 100);
                    return button;
                }
            }
        },
        "Tumblr": {
            "priority": 7,
            "detect": {
                "method": "none",
                "func": function(methods) { return ""; }
            },
            "button": {
                "script": '//platform.tumblr.com/v1/share.js',
                "create": function (methods, params) {
                    var button = util.createBasicButton({
                        "id": 'tumblr',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.width = params.buttonCount ? '90px' : '62px';

                    var link = document.createElement("a");
                    link.href = 'http://www.tumblr.com/share';
                    link.title = "Share on Tumblr";
                    link.innerHTML = "Share on Tumblr";
                    link.style.display = 'inline-block';
                    link.style.textIndent = '-9999px';
                    link.style.textAlign = 'left';
                    link.style.width = '63px';
                    link.style.height = '20px';
                    link.style.background = "url('http://platform.tumblr.com/v1/share_2.png') top left no-repeat transparent";
                    link.style.styleFloat = 'left';
                    link.style.cssFloat = 'left';
                    link.style.marginRight = '5px';
                    link.style.marginTop = 0;

                    link.onclick = function() {
                        methods.itemShared("Tumblr", params);
                    };

                    button.appendChild(link);
                    return button;
                }
            }
        },
        "Twitter": {
            "priority": 3,
            "detect": {
                "method": "image",
                "func": function(methods) { return "https://twitter.com/login?redirect_after_login=%2Fimages%2Fspinner.gif"; }
            },
            "button": {
                "script": '//platform.twitter.com/widgets.js',
                "create": function(methods, params) {
                    var button = util.createBasicButton({
                        "id": 'twitter',
                        "buttonSpacing": params.buttonSpacing,
                        "buttonAlignment": params.buttonAlignment
                    });
                    button.style.width = params.buttonCount ? '90px' : '56px';

                    var link = document.createElement("a");
                    link.href = "https://twitter.com/share";
                    link.className = "twitter-share-button";
                    link.setAttribute('data-url', params.canonicalUrl);
                    link.setAttribute('data-lang','en');
                    link.setAttribute('data-count', ( params.buttonCount ? 'horizontal' : 'none' ));

                    if (params.sharing_message) {
                        link.setAttribute('data-text', params.sharing_message);
                    }

                    button.appendChild(link);
                    return button;
                },
                "onload": function(methods, params) {
                    twttr.events.bind('tweet', function(event) {
                        methods.itemShared("Twitter", params);
                    });
                }
            }
        }
    };
}(_willet));

_willet = (function (me, config) {
    // ***
    // Basic & Smart buttons difference should only exist within this function
    // ***
    // Linking
    var cookies = me.cookies,
        debug = me.debug,
        messaging = me.messaging,
        supportedNetworks = me.networks,
        util = me.util;

    // Private variables
    var MY_APP_URL = "http://willet-nterwoord.appspot.com",
        WILLET_APP_URL = "http://social-referral.appspot.com",
        APP_URL = WILLET_APP_URL,
        PRODUCT_JSON = window.location.protocol
                     + '//'
                     + window.location.hostname
                     + window.location.pathname.replace(/\/$/, '') // remove trailing slash
                     + '.json',
        COOKIE_EXPIRY_IN_DAYS = 30,

        HEAD = document.getElementsByTagName('head')[0],
        BUTTONS_DIV_ID = '_willet_buttons_app',
        DETECT_NETWORKS_DIV_ID = '_willet_buttons_detect_networks',

        DOMAIN = document.domain,
        PROTOCOL = window.location.protocol,

        ELEMENT_NODE = 1,
        NOT_FOUND = -1,

        MAX_BUTTONS = 3,
        DEFAULT_BUTTONS = (config && config.button_order) ||
                          ['Pinterest', 'Tumblr', 'Fancy'],
        DEFAULT_COUNT = 'false',
        DEFAULT_SPACING = '5',
        DEFAULT_PADDING = '5',
        DEFAULT_ALIGNMENT = 'left',
        DEFAULT_CANONICAL_URL = window.location.protocol
                              + '//'
                              + window.location.hostname
                              + '/products/'
                              + window.location.pathname.replace(/^(.*)?\/products\/|\/$/, ''),
            // How this regex works: replaces .../products/ or a trailing / with empty spring 
            // So /collections/this-collection/products/this-product -> this-product

        COOKIE_NAME = "_willet_smart_buttons";

    _willet.APP_URL = APP_URL;

    // Private functions
    var getRequiredButtonsFromElement = function(container) {
        // Get the buttons, should be children of #_willet_buttons_app
        //      ex: <div>Facebook</div>
        var requiredButtons = [];
        if (container.childNodes.length > 0) {
            // Search for supported buttons
            var containerLength = container.childNodes.length;
            for(var i = 0; i < containerLength; i++) {
                var node = container.childNodes[i];
                if (node.nodeType === ELEMENT_NODE) {
                    var network = node.innerHTML;
                    if(util.xHasKeyY(supportedNetworks, network)) {
                        requiredButtons.push(network);
                    }
                }
            }
        }
        return (requiredButtons.length) ? requiredButtons : DEFAULT_BUTTONS; // default for backwards compatibilty;
    };

    var determineButtons = function(buttonsDiv) {
        return getRequiredButtonsFromElement(buttonsDiv) || DEFAULT_BUTTONS;
    };

    var addButton = function(elem, network, button, methods, params) {
        elem.appendChild(button.create(methods, params));

        if (button["script"] !== "") {
            var script = document.createElement("script");
            script.type = "text/javascript";
            script.src = button["script"];
            HEAD.appendChild(script);
        }
        debug.log('Buttons: '+ network +' attached');
    };

    // Public functions
    me.createButtons = function(productData) {
        debug.log("Buttons: finding buttons placeholder on page");
        var buttonsDiv = document.getElementById(BUTTONS_DIV_ID);

        if (buttonsDiv) {

            // Generate button parameters
            var buttonCount = (config && config.button_count) ||
                (util.getElemValue(buttonsDiv, 'count', DEFAULT_COUNT) === 'true');
            var buttonSpacing = ((config && config.button_spacing) ||
                util.getElemValue(buttonsDiv, 'spacing', DEFAULT_SPACING))+'px';
            var buttonPadding = ((config && config.button_padding) ||
                util.getElemValue(buttonsDiv, 'padding', DEFAULT_PADDING))+'px';
            var sharingMessage = (config && config.sharing_message) ||
                ("I found this on " + DOMAIN);

            var params = {
                "domain":           DOMAIN,
                "photo":            productData.product.images[0] ? productData.product.images[0].src : '',
                "data":             productData,
                "buttonAlignment":  util.getElemValue(buttonsDiv, 'align', DEFAULT_ALIGNMENT),
                "buttonCount":  buttonCount,
                "buttonSpacing": buttonSpacing,
                "buttonPadding": buttonPadding,
                "canonicalUrl":  util.getCanonicalUrl(DEFAULT_CANONICAL_URL),
                "sharingMessage": sharingMessage
            };

            // Style container
            buttonsDiv.style.styleFloat = params.buttonAlignment; //IE
            buttonsDiv.style.cssFloat = params.buttonAlignment; //FF, Webkit
            buttonsDiv.style.minWidth = "240px";
            buttonsDiv.style.height = "22px";
            buttonsDiv.style.padding = params.buttonPadding;
            buttonsDiv.style.border = "none";
            buttonsDiv.style.margin = "0";

            // Determine buttons & clean container
            var requiredButtons = determineButtons(buttonsDiv);
            util.removeChildren(buttonsDiv);

            // Create the required buttons
            var network, button,
                methods = {
                    // Not used in basic buttons, but networks still expect it
                    "updateLoggedInStatus": function () {},
                    "itemShared":           function () {}
                };

            for (var i = 0; i < requiredButtons.length; i++) {
                network = requiredButtons[i];
                button = supportedNetworks[network]["button"];

                try {
                    addButton(buttonsDiv, network, button, methods, params);
                } catch (e) {
                    debug.error('Buttons: '+network+' encountered error: '+e);
                }
            }

            // If FB script was already loaded, fire it off again
            if (window.FB && window.FB.XFBML && window.FB.XFBML.parse) {
                try {
                    window.FB.XFBML.parse();
                } catch(e) {}
            }

            // Make visible if hidden
            buttonsDiv.style.display = 'block';

            debug.log('Buttons: Done!');
        } else {
            debug.log('Buttons: could not find buttons placeholder on page');
        }
    };

    me.init = function() {
        // If on /cart page, silently bail
        if (/\/cart\/?$/.test(window.location.pathname)) {
            debug.log("Buttons: on cart page, not running.");
            return;
        }

        // Initialize debugging
        var isDebugging = debug.isDebugging();
        debug.register(function(debug) {
            APP_URL = (debug) ? MY_APP_URL : WILLET_APP_URL;
            PROTOCOL = (debug) ? "http:" : window.location.protocol;
        });
        debug.set(isDebugging);

        if (DOMAIN === 'localhost') {
            // Shopify won't respond on localhost, so use example data
            me.createButtons({
                product: {
                    images: [{ 
                        created_at: "2012-02-03T11:42:17+09:00",
                        id: 166600132,
                        position: 1,
                        product_id: 81809292,
                        updated_at: "2012-02-03T11:42:17+09:00",
                        src:'/static/imgs/beer_200.png'
                    }]
                },
                title: "Glass of beer"
            });
        } else if (window.location.pathname.match(/^(.*)?\/products\//)) {
            // only attempt to load smart-buttons if we are on a product page
            try {
                debug.log("Buttons: initiating product.json request");
                messaging.ajax({
                    url: PRODUCT_JSON,
                    method: "GET",
                    success: function(request) {
                        debug.log("Buttons: recieved product.json request");
                        var data;
                        try {
                            data = JSON.parse(request.responseText);
                        } catch (e) {
                            debug.log("Buttons: could not parse product info, stopping.");
                            return;
                        }
                        if (data) {
                            // Proceed!
                            me.createButtons(data);
                            me.buttonsLoaded = true;
                        }
                    }
                });   
            } catch(e) {
                debug.log("Buttons: request for product.json failed");
            }
        }
    };

    return me;
}(_willet));

try {
    if (_willet && !_willet.buttonsLoaded && (_willet.util.getInternetExplorerVersion() > 7)) {
        _willet.debug.set(false); //set to true if you want logging turned on
        _willet.init();
    }
} catch(e) {
    (function() {
        // Apparently, IE9 can fail for really stupid reasons.
        // This is problematic.
        // http://msdn.microsoft.com/en-us/library/ie/gg622930(v=vs.85).aspx

        // There are better stack trace tools in JS...
        // but they don't work in IE, which is exactly where we need it
        var error = encodeURIComponent("Error initializing buttons");
        var line    = e.number || e.lineNumber || "Unknown";
        var script  = encodeURIComponent("buttons.js:" +line);
        var message = e.stack || e.toString();
        var st      = encodeURIComponent(message);

        var params = "error=" + error + "&script=" + script + "&st=" + st;

        var _willetImage = document.createElement("img");
        _willetImage.src = "http://social-referral.appspot.com/admin/ithinkiateacookie?" + params;
        _willetImage.style.display = "none";

        document.body.appendChild(_willetImage)
    }()); 
}