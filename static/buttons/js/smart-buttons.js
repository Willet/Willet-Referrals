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
    "createScript": function (src) {
        // Returns script element
        var s = document.createElement('script');
        s.type = "text/javascript";
        s.src = src;
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
    "error": function (e, config) {
        if (!e) {
            return;
        }

        var message = config.message || "";
        var type    = config.type || "";

        // More information on error object here:
        // https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Error

        // There are better stack trace tools in JS...
        // but they don't work in IE, which is exactly where we need it

        // Format:
        // {ErrorName}: {ErrorDescription}
        // {ErrorStackTrace}
        var prob   = encodeURIComponent("Error initializing smart-buttons");
        var line   = e.lineNumber || "Unknown";
        var script = encodeURIComponent("smart-buttons.js:" +line);

        var errorInfo = e.stack || (e.number & 0xFFFF) || e.toString();
        var errorDesc = message || e.message || e.description;
        var errorName = type || e.name || errorDesc.split(":")[0];

        if (errorInfo === (errorName + ": " + errorDesc)) {
            errorInfo = "No additional information available";
        }

        var errorMsg  = errorName + ": " + errorDesc + "\n" + errorInfo;
        var encError  = encodeURIComponent(errorMsg);

        var params = "error=" + prob
            + "&script=" + script
            + "&st=" + encError
            + "&subject=" + errorName;

        var _willetImage = document.createElement("img");
        _willetImage.src = window.location.protocol + "//social-referral.appspot.com/email/clientsidemessage?" + params;
        _willetImage.style.display = "none";

        document.body.appendChild(_willetImage);
    },
    "getCanonicalUrl": function (default_url) {
        // Tries to retrieve a canonical link from the header
        // Otherwise, returns default_url
        var links = document.getElementsByTagName('link'),
            i = links.length;
        while (i--) {
            if (links[i].rel === 'canonical' && links[i].href) {
                return links[i].href;
            }
        }
        return default_url;
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
    "isLocalhost": function() {
        return ((window.location.href.indexOf("http") >= 0) ? false : true);
    },
    "renderSimpleTemplate": function (template, values) {
        // Will render templates with simple substitions
        // Inputs:
        //    template - a string representing an HTML template, with variables
        //               of the form: {{ var_name }} and condtionals of the form
        //               {% if var_name %} ... {% endif %}
        //               Note: does not support nested if's, and must be exactly
        //                     the form above (no extra whitespace)
        //    values - a object literal, with keys corresponding to template variables,
        //             and values appropriate for the template
        // Return:
        //    rendered template <string>

        var ifStatementRe = /\{% if [\w\-]+ %\}/g,
            ifPrefixLen = '{% if '.length,
            endifLen = '{% endif %}'.length,
            startIndex, endIndex, contionalIndex, varName;

        // First handle conditionals of the form {% if var_name %} ... {% endif %}
        // Note: strings are passed by value, so we can modify template without affecting
        //       the base templates
        conditionalIndex = template.search(ifStatementRe);
        while (conditionalIndex >= 0) {
            // get variable name from conditional
            varName = template.substring(conditionalIndex+ifPrefixLen, template.indexOf(' ', conditionalIndex+ifPrefixLen));

            if (values[varName]) {
                // if variable name exists, strip conditional statements & leave code
                template = template.replace('{% if '+varName+' %}', '');
                template = template.replace('{% endif %}','');
            } else {
                // if variable doesn't exist, strip conditional & contents
                startIndex = conditionalIndex;
                endIndex = template.indexOf('{% endif %}',startIndex)+endifLen;
                template = template.replace( template.substring(startIndex, endIndex), '');
            }

            // Get next one
            conditionalIndex = template.search(re);
        }

        // Second handle variables of the form {{ var_name }}
        for (var i in values) {
            if (values.hasOwnProperty(i)) {
                template = template.replace('{{ '+ i +' }}', values[i]);
            }
        }
        return template;
    },
    "parseQS": function(src) {
        var qs = src.indexOf('?') ? src.substr(src.indexOf('?')+1) : null,
            params = {};

        if (qs) {
            // A little hack - convert the query string into JSON format and parse it
            // '&' -> ',' and '=' -> ':'
            try {
                params = JSON.parse('{"' + decodeURIComponent(qs.replace(/(&amp;|&)/g, "\",\"").replace(/=/g,"\":\"")) + '"}');
            } catch(e) {
                _willet.debug.error("Couldn't parse query string");
            }
        }

        return params;
    },
    "getConfigFromQS": function() {
        // Find ourself
        var i,
            regex = /\.appspot\.com\/.*\/(smart-)?buttons\.js/,
            scripts = document.getElementsByTagName("script"),
            src;

        for (i = 0; i < scripts.length; i++) {
            if (regex.test(scripts[i].src)) {
                src = scripts[i].src;
                break;
            }
        }


        // get the config
        return _willet.util.parseQS(src);
    }
};

// Modified from: http://www.quirksmode.org/js/detect.html
_willet.util.detectBrowser = function() {
    var browser,
        browserVersion,
        operatingSystem,
        operatingSystems,
        searchString,
        searchVersion,
        supportedBrowsers,
        versionSearchString;

    //Trim this list if we want to support less browsers
    supportedBrowsers = [{
        string: navigator.userAgent,
        subString: "Chrome",
        identity: "Chrome"
    }, {
        string: navigator.userAgent,
        subString: "OmniWeb",
        versionSearch: "OmniWeb/",
        identity: "OmniWeb"
    }, {
        string: navigator.vendor,
        subString: "Apple",
        identity: "Safari",
        versionSearch: "Version"
    }, {
        prop: window.opera,
        identity: "Opera",
        versionSearch: "Version"
    }, {
        string: navigator.vendor,
        subString: "iCab",
        identity: "iCab"
    }, {
        string: navigator.vendor,
        subString: "KDE",
        identity: "Konqueror"
    }, {
        string: navigator.userAgent,
        subString: "Firefox",
        identity: "Firefox"
    }, {
        string: navigator.vendor,
        subString: "Camino",
        identity: "Camino"
    }, {   // for newer Netscapes (6+)
        string: navigator.userAgent,
        subString: "Netscape",
        identity: "Netscape"
    }, {
        string: navigator.userAgent,
        subString: "MSIE",
        identity: "Explorer",
        versionSearch: "MSIE"
    }, {
        string: navigator.userAgent,
        subString: "Gecko",
        identity: "Mozilla",
        versionSearch: "rv"
    }, {   // for older Netscapes (4-)
        string: navigator.userAgent,
        subString: "Mozilla",
        identity: "Netscape",
        versionSearch: "Mozilla"
    }];

    operatingSystems = [{
        string: navigator.platform,
        subString: "Win",
        identity: "Windows"
    }, {
        string: navigator.platform,
        subString: "Mac",
        identity: "Mac"
    }, {
        string: navigator.userAgent,
        subString: "iPhone",
        identity: "iPhone/iPod"
    }, {
        string: navigator.platform,
        subString: "Linux",
        identity: "Linux"
    }];

    searchString = function (data) {
        var dataString,
            dataProp,
            i;

        for (i = 0; i < data.length; i++) {
            dataString = data[i].string;
            dataProp   = data[i].prop;

            versionSearchString = data[i].versionSearch || data[i].identity;

            if (dataString) {
                if (dataString.indexOf(data[i].subString) != -1) {
                    return data[i].identity;
                }
            } else if (dataProp) {
                return data[i].identity;
            }
        }
    };

    searchVersion = function (dataString) {
        var index = dataString.indexOf(versionSearchString);
        if (index == -1) {
            return;
        }
        return parseFloat(dataString.substring(index+versionSearchString.length+1));
    };

    operatingSystem = searchString(operatingSystems)  || "an unknown OS";
    browser         = searchString(supportedBrowsers) || "An unknown browser";
    browserVersion  = searchVersion(navigator.userAgent)
        || searchVersion(navigator.appVersion)
        || "an unknown version";

    return {
        browser: browser,
        version: browserVersion,
        os: operatingSystem
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
    /*
        .ajax - Server communication
        .xd -   Cross-domain frame communication
    */
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
        // We do not support cross-domain communication in IE 7 and below
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
            try {
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
                }

                //create the iframe
                var originDomain = window.location.protocol + "//" + window.location.hostname;
                var iframe = document.createElement("iframe");
                iframe.src = url + "?origin=" + originDomain + (debug.isDebugging()? "#debug" : "");
                iframe.style.display = "none";

                document.body.appendChild(iframe);
            } catch (e) {
                _willet.util.error(e, {
                   "message": "Problem initializing cross-domain code. See stack trace.",
                   "type": "Willet.CrossDomainError"
                });
            }
        };

        var getOrCreateIFrame = function (domain, path, listener) {
            var id = "willet.xd:" + domain + path;
            var iFrame = document.getElementById(id);

            if (!iFrame) {
                iFrame = document.createElement("iframe")
                iFrame.style.cssText = "position:absolute;width:1px;height:1px;left:-9999px;";
                document.body.appendChild(iFrame);

                iFrame.src = "//" + domain + path;
                iFrame.id  = id;
            }

            if (listener) {
                if (window.addEventListener) {
                    window.addEventListener("message", listener, false);
                } else if (window.attachEvent) {
                    window.attachEvent("onmessage", listener);
                }
            }

            return iFrame;
        };

        xd.receive = function (domain, path, callback) {
            getOrCreateIFrame(domain, path, callback);
        };

        // TODO: It really makes sense to have a stateful xd object...
        xd.send = function (domain, path, data) {
            // assume that data is a dictionary
            var iFrame = getOrCreateIFrame(domain, path);
            var msg    = JSON.stringify(data);
            var origin = window.location.protocol + "//" + domain;
            iFrame.contentWindow.postMessage(msg, origin);
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
        "AskFriends": {
            "priority": 1,
            "detect": {
                "method": "none",
                "func": function(methods) { return ""; }
            },
            "button": {
                "script": '//social-referral.appspot.com/s/sibt.js?page_url=' + window.location,
                "create": function () {
                    var button = util.createBasicButton({
                        "id": '_mini_sibt_button'
                    });

                    var d = document.createElement("a");
                    d.id = 'mini_sibt_button';
                    d.style.cursor = 'pointer';
                    d.style.display = 'inline-block';
                    d.style.background = "url('//social-referral.appspot.com/static/sibt/imgs/button_bkg.png') 3% 20% no-repeat transparent";
                    d.style.width = '80px';
                    button.appendChild(d);
                    return button;
                }
            }
        },
        "Facebook": {
            "priority": 2,
            "detect": {
                "method": "api",
                "func": function(methods) {
                    messaging.xd.createMessageHandler(function(data) {
                        try {
                            var message = data && data.message || {};
                            var status = (message.Facebook && message.Facebook.status) || false; //use status, if it exists
                            methods.updateLoggedInStatus("Facebook", status);
                        } catch(e) {
                            _willet.util.error(e, {
                                "message": "Problem retrieving cross-domain result. See stack trace.",
                                "type": "Willet.CrossDomainResultError"
                            });
                        }
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
                    button.appendChild(fb);

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
                    link.style.zIndex = "1";
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
                                                +"   background-image: url('//assets.pinterest.com/images/pinit6.png'); "
                                                +"   background-position: 0 -7px; "
                                                +"} "
                                                +"a.willet-pinterest-button:hover { background-position: 0 -28px; cursor: pointer; } "
                                                +"a.willet-pinterest-button:active { background-position: 0 -49px; cursor: pointer; } "
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
                    button.style.width = params.buttonCount ? '90px' : '60px';

                    var link = document.createElement("a");
                    link.href = "https://twitter.com/share";
                    link.className = "twitter-share-button";
                    link.setAttribute('data-url', params.canonicalUrl);
                    link.setAttribute('data-lang','en');
                    link.setAttribute('data-count', ( params.buttonCount ? 'horizontal' : 'none' ));

                    if (params.sharingMessage) {
                        link.setAttribute('data-text', params.sharingMessage);
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

    // Constants
    var MY_APP_URL = "http://fraser-willet2.appspot.com",
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

        MAX_BUTTONS = (config && config.max_buttons) || 3,
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
            // How this regex works: replaces .../products/ or a trailing / with empty string
            // So /collections/this-collection/products/this-product -> this-product

        COOKIE_NAME = "_willet_smart_buttons";

    _willet.APP_URL = APP_URL;

    // Private variables
    var loggedInNetworks = (function () {
        // Load loggedInNetworks with saved array of known networks
        var networks = {},
            networksJSON = cookies.read(COOKIE_NAME);

        if (networksJSON) {
            try {
                networks = JSON.parse(networksJSON);
            } catch(e) {
                debug.log("Buttons: Unable to parse cookie")
            }
        }
        return networks;
    }());

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
        return requiredButtons;
    };

    var updateLoggedInStatus = function(network, status, includeTime) {
        debug.log("Buttons: "+(status ? "" : "Not ")+ network +" user");
        if (status === true) {
            var now = new Date();
            loggedInNetworks[network] = { "status": status };
            if (includeTime === true) {
                loggedInNetworks[network]["accessed"] = now.getTime();
            }
            cookies.create(COOKIE_NAME, JSON.stringify(loggedInNetworks), COOKIE_EXPIRY_IN_DAYS);
        }
    };

    var itemShared = function(network, params) {
        //If someone shares, update the cookie
        updateLoggedInStatus(network, true, true);

        var message = JSON.stringify({
            "name"   : params.data.product.title,
            "network": network,
            "img"    : params.photo
        });

        //Need to append param to avoid caching...
        var queryString = "message="    + encodeURIComponent(message)
                     + "&nocache=" + Math.random();

        var _willetImage = document.createElement("img");
        _willetImage.src = APP_URL + "/b/shopify/item_shared?" + queryString;
        _willetImage.style.display = "none";

        document.body.appendChild(_willetImage)
    };

    // Sorting comparators are hard to remember. For more details on sorting:
    // https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Array/sort#Description
    var sortComparator = function(a, b, descending) {
        var order = descending ? -1 : 1,
            result;

        if (a && b) {
            if (a > b) {
                result = 1;
            } else if (a < b) {
                result = -1;
            } else {
                result = 0;
            }
        } else {
            if (a) {
                result = 1;
            } else if (b) {
                result = -1;
            } else {
                result = 0;
            }
        }

        return result * order;
    };

    // Returns networks sorted by accessed (most recent first), then priority
    var networkPrioritizedSort = function(a, b) {
        var dateA = a.value.accessed,
            dateB = b.value.accessed,
            priorityA = supportedNetworks[a.key]["priority"] || 100,
            priorityB = supportedNetworks[b.key]["priority"] || 100,
            result;

        if (dateA || dateB) {
            result = sortComparator(dateA, dateB, true);
        } else {
            result = sortComparator(priorityA, priorityB)
        }

        return result;
    };

    var determineButtons = function(buttonsDiv) {
        var i,
            networks = [],
            requiredButtons = [];

        // Personalize buttons if not disabled
        // Conditional defaults to true
        if ((typeof config === "undefined")
            || (typeof config.personalization_enabled === "undefined")
            || (config.personalization_enabled === 'true')) {
            // Queue detected networks first, if the cookie exists
            if (loggedInNetworks) {
                networks = util.dictToArray(loggedInNetworks);
                networks = networks.sort(networkPrioritizedSort);

                // Queue detected buttons
                for (i = 0; i < networks.length && requiredButtons.length < MAX_BUTTONS; i++) {
                    var network = networks[i];
                    if (util.xHasKeyY(supportedNetworks, network.key)   //check that this is a network we support
                        && network.value.status === true) {         //check that the network is enabled
                        requiredButtons.push(network.key);
                    }
                }
            }

            // Queue user's buttons if there is space, and they have not already been added
            var usersButtons = getRequiredButtonsFromElement(buttonsDiv);
            for (i = 0; i < usersButtons.length && requiredButtons.length < MAX_BUTTONS; i++) {
                var button = usersButtons[i];
                if (util.indexOf(requiredButtons, button) === NOT_FOUND) {
                    requiredButtons.push(button);
                }
            }
        }

        // Queue default buttons to the end, if they have not already been added
        for (i = 0; i < DEFAULT_BUTTONS.length && requiredButtons.length < MAX_BUTTONS; i++) {
            var button = DEFAULT_BUTTONS[i];
            if (util.indexOf(requiredButtons, button) == NOT_FOUND) {
                requiredButtons.push(button);
            }
        }

        return requiredButtons;
    };

    var addButton = function(elem, network, button, methods, params) {
        elem.appendChild(button.create(methods, params));

        if (button["script"] !== "") {
            var script = document.createElement("script");
            script.type = "text/javascript";
            script.src = button["script"];
            script.onload = function () {
                button["onload"] && button["onload"](methods, params);
            };
            HEAD.appendChild(script);
        }
        debug.log('Buttons: '+ network +' attached');
    };

    // Public functions
    me.detectNetworks = function () {
        // Determines which social networks are in use
        // The detection is asynchronous & saved to a cookie
        // for lookup later
        debug.log("Buttons: Determining networks...")
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

        for (network in supportedNetworks) {
            if (supportedNetworks.hasOwnProperty(network)) {
                var detectNetwork = supportedNetworks[network]["detect"];
                debug.log("Buttons: Attempting to detect " + network);
                switch (detectNetwork["method"]) {
                    case "image":
                        var image = createHiddenImage(network, detectNetwork.func());
                        detectNetworksDiv.appendChild(image);
                    break;

                    case "api":
                        detectNetwork.func({
                            "updateLoggedInStatus": updateLoggedInStatus,
                            "itemShared":           itemShared
                        });
                    break;

                    default:
                        //Nothing to do
                }
            }
        }
    };

    me.createButtons = function(productData) {
        debug.log("Buttons: finding buttons placeholder on page");
        var buttonsDiv = document.getElementById(BUTTONS_DIV_ID);

        if (buttonsDiv) {
            // Initialize values
            var buttonCount    = (util.getElemValue(buttonsDiv, 'count', DEFAULT_COUNT) === 'true'),
                buttonSpacing  = (util.getElemValue(buttonsDiv, 'spacing', DEFAULT_SPACING) + 'px'),
                buttonPadding  = (util.getElemValue(buttonsDiv, 'padding', DEFAULT_PADDING) + 'px'),
                sharingMessage = ("I found this on " + DOMAIN),
                u = undefined, //shorthand
                c;

            // Override with config
            if (config !== u) {
                c = config;
                buttonCount    = ((c.button_count    !== u) ? c.button_count : buttonCount);
                buttonSpacing  = ((c.button_spacing  !== u) && ""+c.button_spacing+"px" ) || buttonSpacing;
                buttonPadding  = ((c.button_padding  !== u) && ""+c.button_padding+"px" ) || buttonPadding;
                sharingMessage = ((c.sharing_message !== u) ? c.sharing_message : sharingMessage);
            }

            var params = {
                "domain":       DOMAIN,
                "photo":        productData.product.images[0] ? productData.product.images[0].src : '',
                "data":         productData,
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
            var network, button, script,
                methods = {
                    "updateLoggedInStatus": updateLoggedInStatus,
                    "itemShared":           itemShared
                };

            for (i = 0; i < requiredButtons.length; i++) {
                network = requiredButtons[i];
                button = supportedNetworks[network]["button"];

                try {
                    addButton(buttonsDiv, network, button, methods, params);
                } catch (e) {
                    debug.error('Buttons: '+network+' encountered error: '+e);
                }
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

        if (!util.isDictEmpty(loggedInNetworks)) {
            me.detectNetworks();
        }

        if (window.location.pathname.match(/^(.*)?\/products\//)) {
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
}(_willet, window._willet_shopconnection_config || {}));

try {
    if (_willet) {
        var info = _willet.util.detectBrowser();
        _willet.debug.set(false); //set to true if you want logging turned on

        if (!_willet.buttonsLoaded
            && !(info.browser === "Explorer" && info.version <= 7)
            && !(info.browser === "An unknown browser")
            && !(_willet.util.isLocalhost()))
        {
            _willet.init();
        } else {
            _willet.debug.log("Buttons not loaded: Unsupported browser or localhost");
        }
    }

} catch(e) {
    //assume, potentially wrongfully, that we have access to _willet.util.error
    _willet.util.error(e, {
       "message": "We're not exactly sure what went wrong. Check the stack trace provided.",
       "type": "Willet.UnexpectedError"
    });
}