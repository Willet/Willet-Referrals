/*
 * Buttons JS. Copyright Willet Inc, 2012
 */
;// Source: JSON2, Author: Douglas Crockford, http://www.JSON.org/json2.js
var JSON;if(!JSON){JSON={};}
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

var _willet = (function(me) {
    // Private variables
    var MY_APP_URL = "http://willet-nterwoord.appspot.com";
    var WILLET_APP_URL = "http://social-referral.appspot.com";
    var APP_URL = WILLET_APP_URL;
    var PRODUCT_JSON = window.location.href.split("#")[0] + '.json';
    var COOKIE_NAME = "_willet_smart_buttons";
    var COOKIE_EXPIRY_IN_DAYS = 30;

    var HEAD = document.getElementsByTagName('head')[0];
    var BUTTONS_DIV_ID = '_willet_buttons_app';
    var DETECT_NETWORKS_DIV_ID = '_willet_buttons_detect_networks';

    var DOMAIN = /:\/\/([^\/]+)/.exec(window.location.href)[1];
    var PROTOCOL = window.location.protocol;

    var ELEMENT_NODE = 1;
    var NOT_FOUND = -1;

    var MAX_BUTTONS = 3;
    var DEFAULT_BUTTONS = ['Pinterest','Tumblr', 'Fancy'];
    var SUPPORTED_NETWORKS = {
        "Tumblr": {
            "detect": {
                "method": "none",
                "func": function() { return ""; }
            },
            "button": {
                "script": PROTOCOL + '//platform.tumblr.com/v1/share.js',
                "create": function (params) {
                    var button = createBasicButton({
                        "id": 'tumblr',
                        "buttonSpacing": params.buttonSpacing
                    });
                    button.style.width = '62px';

                    var link = document.createElement("a");
                    link.href = 'http://www.tumblr.com/share';
                    link.title = "Share on Tumblr";
                    link.innerHTML = "Share on Tumblr";
                    link.style.display = 'inline-block';
                    link.style.textIndent = '-9999px';
                    link.style.textAlign = 'left';
                    link.style.width = '63px';
                    link.style.height = '20px';
                    link.style.background = "url('http://platform.tumblr.com/v1/share_2.png') top left no-repeat transparent"
                    link.style.styleFloat = 'left';
                    link.style.cssFloat = 'left';
                    link.style.marginRight = '5px';
                    link.style.marginTop = 0;

                    link.onload = function() {
                        itemShared("Tumblr");
                    };

                    button.appendChild(link);
                    return button;
                }
            }
        },
        "Facebook": {
            "detect": {
                "method": "api",
                "func": function() {
                    _willet.messaging.xd.createMessageHandler(function(data) {
                        var message = data && data.message || {};
                        var status = (message.Facebook && message.Facebook.status) || false; //use status, if it exists
                        updateLoggedInStatus("Facebook", status);
                    }, APP_URL + "/static/plugin/html/detectFB.html");
                }
            },
            "button": {
                "script": PROTOCOL + '//connect.facebook.net/en_US/all.js#xfbml=1',
                "create": function(params) {
                    var button = createBasicButton({
                        "id": 'facebook',
                        "buttonSpacing": params.buttonSpacing
                    });
                    button.style.width = params.buttonCount ? '90px' : '48px';
                    button.innerHTML = "<fb:like send='false' layout='button_count' width='450' show_faces='false'></fb:like>";
                    return button;
                },
                "onLoad": function() {
                    FB.Event.subscribe('edge.create', function(response) {
                        itemShared("Facebook");
                    });
                }
            }
        },
        "Pinterest": {
            "detect": {
                "method": "image",
                "func": function() { return "https://pinterest.com/login/?next=http://assets.pinterest.com/images/error_404_icon.png"; }
            },
            "button": {
                "script": PROTOCOL + '//assets.pinterest.com/js/pinit.js',
                "create": function(params) {
                    var button = createBasicButton({
                        "id": 'pinterest',
                        "buttonSpacing": params.buttonSpacing
                    });
                    button.style.width = params.buttonCount ? '77px' : '43px';

                    var link = document.createElement("a");
                    link.href = "http://pinterest.com/pin/create/button/?" +
                        "url=" + encodeURIComponent( window.location.href ) + 
                        "&media=" + encodeURIComponent( params.photo ) + 
                        "&description=" + encodeURIComponent("I found this on " + params.domain);
                    link.className = "pin-it-button";
                    link.innerHTML = "Pin It";

                    link.onload = function() {
                        itemShared("Tumblr");
                    };

                    link.setAttribute('count-layout', "horizontal");

                    button.appendChild(link);
                    return button;
                }
            }
        },
        "Twitter": {
            "detect": {
                "method": "image",
                "func": function() { return "https://twitter.com/login?redirect_after_login=%2Fimages%2Fspinner.gif"; }
            },
            "button": {
                "script": PROTOCOL + '//platform.twitter.com/widgets.js',
                "create": function(params) {
                    var button = createBasicButton({
                        "id": 'twitter',
                        "buttonSpacing": params.buttonSpacing
                    });
                    button.style.width = params.buttonCount ? '98px' : '56px';

                    var link = document.createElement("a");
                    link.href = "https://twitter.com/share";
                    link.className = "twitter-share-button";

                    link.setAttribute('data-lang','en');
                    link.setAttribute('data-count', ( params.buttonCount ? 'horizontal' : 'none' ));

                    button.appendChild(link);
                    return button;
                },
                "onLoad": function() {
                    twttr.events.bind('tweet', function(event) {
                        itemShared("Twitter");
                    });
                }
            }
        }, 
        "GooglePlus": {
            "detect": {
                "method": "image",
                "func": function() { return "https://plus.google.com/up/?continue=https://www.google.com/intl/en/images/logos/accounts_logo.png&type=st&gpsrc=ogpy0"; }
            },
            "button": {
                "script": PROTOCOL + '//apis.google.com/js/plusone.js',
                "create": function(params) {
                    var button = createBasicButton({
                        "id": 'googleplus',
                        "buttonSpacing": params.buttonSpacing
                    });
                    button.style.width = params.buttonCount ? '90px' : '32px';

                    var gPlus = document.createElement("g:plusone");
                    gPlus.setAttribute("size", "medium");
                    if (!params.buttonCount) {
                        gPlus.setAttribute("annotation", "none");
                    }
                    gPlus.setAttribute("callback", "_willet.gPlusShared");

                    button.appendChild(gPlus);

                    //button.innerHTML = "<g:plusone size='medium'"+ (params.buttonCount ? '' : " annotation='none'") +" callback='_willet.gPlusShared'></g:plusone>";

                    // Google Plus will only execute a callback in the global namespace, so expose this one...
                    // https://developers.google.com/+/plugins/+1button/#plusonetag-parameters
                    me.gPlusShared = function(response) {
                        itemShared("GooglePlus");
                    };
                    
                    // Google is using the Open Graph spec
                    var t, p, 
                        m = [ { property: 'og:title', content: params.data.product.title },
                              { property: 'og:image', content: params.photo },
                              { property: 'og:description', content: 'I found this on '+ params.domain } ]
                    while (m.length) {
                        p = m.pop();
                        t = document.createElement('meta');
                        t.setAttribute('property', p.property);
                        t.setAttribute('content', p.content);
                        HEAD.appendChild(t);
                    }
                    return button;
                }
            }
        },
        "Fancy": {
            "detect": {
                "method": "none",
                "func": function() { return ""; }
            },
            "button": {
                "script": PROTOCOL + '//www.thefancy.com/fancyit.js',
                "create": function(params) {
                    var button = createBasicButton({
                        "id": 'fancy',
                        "buttonSpacing": params.buttonSpacing
                    });
                    button.style.width = params.buttonCount ? '96px' : '57px';

                    var u = "http://www.thefancy.com/fancyit?" +
                            "ItemURL=" + encodeURIComponent( window.location.href ) + 
                            "&Title="  + encodeURIComponent( params.data.product.title ) +
                            "&Category=Other";
                    if ( params.photo.length > 0 ) {
                        u += "&ImageURL=" + encodeURIComponent( params.photo );
                    } else { // If no image on page, submit blank image.
                        u += "&ImageURL=" + encodeURIComponent( 'http://social-referral.appspot.com/static/imgs/noimage.png' );
                    }

                    var link = document.createElement("a");
                    link.id = "FancyButton";
                    link.href = u;

                    link.onload = function() {
                        itemShared("Tumblr");
                    };
                    
                    link.setAttribute('data-count', ( params.buttonCount ? 'true' : 'false' ));
                    button.appendChild(link);
                    return button;
                }
            }
        }
    };
    var loggedInNetworks = {};

    // Private functions
    var xHasKeyY = function(dict, key) {
        if (dict[key]) {
            return true
        } else {
            return false
        }
    };

    var createBasicButton = function (params) {
        var id = params.id || '';
        var buttonSpacing = params.buttonSpacing || "0";

        var d = document.createElement("div");

        d.style.styleFloat = "left"; //IE
        d.style.cssFloat = "left"; //FF, Webkit
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
        d.style.position = "relative";
        d.style.overflow = "hidden";

        d.name = "button";
        d.id = "_willet_" + id;
        d.className = "_willet_social_button";

        return d;
    };

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
                    if(xHasKeyY(SUPPORTED_NETWORKS, network)) {
                        requiredButtons.push(network);
                    }
                }
            }
        }
        return (requiredButtons.length) ? requiredButtons : DEFAULT_BUTTONS; // default for backwards compatibilty;
    };

    var updateLoggedInStatus = function(network, status) {
        _willet.debug.log("Buttons: User is " + (status ? "" : "not ") + "logged in to " + network);
        var now = new Date();
        loggedInNetworks[network] = { "status": status, "accessed": now.getTime()};
        _willet.cookies.create(COOKIE_NAME, JSON.stringify(loggedInNetworks), COOKIE_EXPIRY_IN_DAYS);
    };

    var itemShared = function(network) {
        //If someone shares, update the cookie
        updateLoggedInStatus(network, true);
    };

    var dictToArray = function(dict) {
        var result = [];

        for (var key in dict) {
            if (dict.hasOwnProperty(key)) {
                result.push({
                    "key": key,
                    "value": dict[key]
                });
            }
        }

        return result;
    };

    // Public functions
    me.detectNetworks = function () {
        _willet.debug.log("Buttons: Detecting networks...")
        var createHiddenImage = function(network, source) {
            var image = document.createElement("img");
            image.onload = function () {
                updateLoggedInStatus(network, true);
            };
            image.onerror = function() {
                updateLoggedInStatus(network, false);
            };
            image.src = source;
            image.style.display = "none";
            return image;
        };

        var detectNetworksDiv = document.createElement("div");
        detectNetworksDiv.id = DETECT_NETWORKS_DIV_ID;

        document.body.appendChild(detectNetworksDiv);

        for (network in SUPPORTED_NETWORKS) {
            if (SUPPORTED_NETWORKS.hasOwnProperty(network)) {
                var detectNetwork = SUPPORTED_NETWORKS[network]["detect"];
                _willet.debug.log("Buttons: Attempting to detect " + network);
                switch (detectNetwork["method"]) {
                    case "image":
                        var image = createHiddenImage(network, detectNetwork.func());
                        detectNetworksDiv.appendChild(image);
                    break;

                    case "api":
                        detectNetwork.func();
                    break;

                    default:
                        //Nothing to do
                }
            }
        }
        return _willet.cookies.read(COOKIE_NAME);
    };

    me.createButtons = function(productData) {
        _willet.debug.log("Buttons: finding buttons placeholder on page");
        var buttonsDiv = document.getElementById(BUTTONS_DIV_ID);

        if (buttonsDiv && window._willet_iframe_loaded == undefined) {
            var buttonCount = (buttonsDiv.getAttribute('button_count') === 'true');
            var buttonSpacing = (buttonsDiv.getAttribute('button_spacing') ?  buttonsDiv.getAttribute('button_spacing') : '5') + 'px';
            var buttonPadding = (buttonsDiv.getAttribute('button_padding') ? buttonsDiv.getAttribute('button_padding') : '5') + 'px';

            buttonsDiv.style.styleFloat = "left"; //IE
            buttonsDiv.style.cssFloat = "left"; //FF, Webkit
            buttonsDiv.style.minWidth = "240px";
            buttonsDiv.style.height = "22px";
            buttonsDiv.style.padding = "buttonPadding";
            buttonsDiv.style.border = "none";
            buttonsDiv.style.margin = "0";

            // Grab the photo
            var photo = '';
            if ( productData.product.images[0] != null ) {
                photo = productData.product.images[0].src;
            }

            var requiredButtons = [];
            var networksJSON = _willet.cookies.read(COOKIE_NAME) || "";
            if (networksJSON === "") {
                requiredButtons = getRequiredButtonsFromElement(buttonsDiv);

                // Now remove all children of #_willet_buttons_app
                var i = buttonsDiv.childNodes.length;
                while (i--) {
                    buttonsDiv.removeChild(buttonsDiv.childNodes[i]);
                }
            } else {
                var networks = {};
                try {
                    networks = JSON.parse(networksJSON);
                } catch(e) {
                    _willet.debug.log("Buttons: Unable to parse cookie")
                }

                networks = dictToArray(networks);
                networks = networks.sort(function(a,b) {
                    return b.value.accessed - a.value.accessed;
                });

                for (var i = 0; i < networks.length && requiredButtons.length < MAX_BUTTONS; i++) {
                    var network = networks[i];
                    if (xHasKeyY(SUPPORTED_NETWORKS, network.key)   //check that this is a network we support
                        && network.value.status === true) {         //check that the network is enabled
                        requiredButtons.push(network.key);
                    }
                }

                //append default buttons to the end, if they have not already been added
                for (var i = 0; i < DEFAULT_BUTTONS.length && requiredButtons.length < MAX_BUTTONS; i++) {
                    var button = DEFAULT_BUTTONS[i];
                    if (requiredButtons.indexOf(button) == NOT_FOUND) {
                        requiredButtons.push(button);
                    }
                }
            }

            for (var i = 0; i < requiredButtons.length; i++) {
                var network = requiredButtons[i];
                var button = SUPPORTED_NETWORKS[network]["button"];
                buttonsDiv.appendChild(button.create({
                    "domain": DOMAIN,
                    "photo": photo,
                    "data": productData,
                    "buttonCount": buttonCount,
                    "buttonSpacing": buttonSpacing,
                    "buttonPadding": buttonPadding
                }));

                var script = document.createElement("script");
                script.type = "text/javascript";
                script.src = button["script"];
                script.onload = button["onLoad"];

                HEAD.appendChild(script);
                _willet.debug.log('Buttons: '+ network +' attached');
            }

            // If Facebook is already loaded,
            // trigger it to enable Like button
            try {
                window.FB && window.FB.XFBML.parse(); 
            } catch(e) {}

            // Make visible if hidden
            buttonsDiv.style.display = 'block';

            _willet.debug.log('Buttons: Done!');
        } else {
            _willet.debug.log('Buttons: could not find buttons placeholder on page');
        }
    };

    me.init = function() {
        var isDebugging = _willet.debug.isDebugging();
        _willet.debug.register(function(debug) {
            APP_URL = (debug) ? MY_APP_URL : WILLET_APP_URL;
            PROTOCOL = (debug) ? "http:" : window.location.protocol;
        });
        _willet.debug.set(isDebugging);

        if (!_willet.cookies.read(COOKIE_NAME)) {
            me.detectNetworks();
        }

        if(!isDebugging) {
            try {
                _willet.debug.log("Buttons: initiating product.json request")
                _willet.messaging.ajax({
                    url: PRODUCT_JSON,
                    method: "GET",
                    success: function(request) {
                        _willet.debug.log("Buttons: recieved product.json request");
                        var data;
                        try {
                            data = JSON.parse(request.responseText);
                        } catch (e) {
                            _willet.debug.log("Buttons: could not parse product info, stopping.");
                            return;
                        }
                        if (data) {
                            // Proceed!
                            me.createButtons(data);
                        }
                    }
                });   
            } catch(e) {
                _willet.debug.log("Buttons: request for product.json failed");
            }
        } else {
            me.createButtons({
                product: {
                    images: [
                        { created_at: "2012-02-03T11:42:17+09:00",
                        id: 166600132,
                        position: 1,
                        product_id: 81809292,
                        updated_at: "2012-02-03T11:42:17+09:00",
                        src:'/static/imgs/beer_200.png' }
                    ]
                },
                title: "Glass of beer"
            });
        }
    };

    return me;
} (_willet || {}));

_willet.debug = (function(){
    var me = {};
    var isDebugging = false;
    var callbacks = [];

    var _log = function() {};
    var _error = function() {};

    if (window.console) {
        _log = function () {
            var log = window.console.log;
            if (log.apply) {
                log.apply(window.console, arguments);
            } else {
                log(arguments)
            }
        };
        _error = function () {
            var error = window.console.error;
            if (error.apply) {
                error.apply(window.console, arguments);
            } else {
                error(arguments)
            }
        };
    }

    me.register = function(callback) {
        callbacks.push(callback);
    };

    me.set = function(debug) {
        me.log = (debug) ? _log: function() {};
        me.error = (debug) ? _error: function() {};
        isDebugging = debug;

        for(var i = 0; i < callbacks.length; i++) {
            callbacks[i](debug);
        }
    }

    me.isDebugging = function() {
        return isDebugging;
    };

    me.set(false); //setup proper log functions

    return me;
}());

_willet.cookies = (function(){
    var me = {};

    // Source: http://www.quirksmode.org/js/cookies.html
    me.create = function (name, value, days) {
        if (days) {
            var date = new Date();
            date.setTime(date.getTime()+(days*24*60*60*1000));
            var expires = "; expires="+date.toGMTString();
        }
        else var expires = "";
        document.cookie = name+"="+value+expires+"; path=/";
    };

    // Source: http://www.quirksmode.org/js/cookies.html
    me.read = function (name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for(var i=0;i < ca.length;i++) {
            var c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
        }
        return null;
    };

    // Source: http://www.quirksmode.org/js/cookies.html
    me.erase = function (name) {
        me.create(name,"",-1);
    };

    return me;
}());

_willet.messaging = (function(){
    var me = {};

    me.ajax = function(config) {
        var AJAX_RESPONSE_AVAILABLE = 4;
        var HTTP_OK = 200;

        var url = config.url || "";
        var success = config.success || function() {};
        var error = config.error || function() {};
        var method = config.method || "GET";
        var async = config.async || true;

        if (url === "") {
            _willet.debug.error("Messaging: No URL provided");
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
                _willet.debug.log("Messaging.XD: No message provided");
                return;
            }

            payload += MESSAGE_TOKEN + "=" + JSON.stringify(message);
            
            _willet.debug.log("Messaging.XD: Sending payload..." + payload);
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
            iframe.src = url + "?origin=" + originDomain + (_willet.debug.isDebugging()? "#debug" : "");
            iframe.style.display = "none";

            document.body.appendChild(iframe);
        };

        return xd;
    }());

    return me;
}());

try {
    _willet.debug.set(false); //set to true if you want logging turned on
    _willet.init();
} catch(e) {
    //TODO: Fire an email
}