/** ShopConnection - Confirmation Page Social Sharing
  * Copyright 2012, Willet, Inc.
 **/

// Example URL: https://checkout.shopify.com/orders/962072/403f3cf2ca6ec05a118864ee80ba30a5

var _willet = window._willet || {};

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
        _willetImage.src = "http://social-referral.appspot.com/admin/ithinkiateacookie?" + params;
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
    "renderSimpleTemplate": function (elem, template, values) {
        // Will render templates with simple substitions
        // Inputs:
        //    elem - the elem that the rendered template will be attached to
        //    template - a string representing an HTML template, with variables of the form: {{ var_name }}
        //    values - a object literal, with keys corresponding to template variables, and values appropriate for the template
        // Return:
        //    elem
        //
        // Note: strings are passed by value, so we can modify it without affecting the base template
        for (var i in values) {
            if (values.hasOwnProperty(i)) {
                template = template.replace('{{ '+ i +' }}', values[i]);
            }
        }

        elem.innerHTML = template;
        return elem;
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

_willet = (function (me, config) {
    var util = me.util,
        debug = me.debug,
        cookies = me.cookies;

    var sharePurchaseTemplate = ""
        + "<div class='fb-like' data-send='true' data-layout='button_count' data-width='450' data-show-faces='false'></div><div id='fb-root'></div>"
        + "<a href='https://twitter.com/share' class='twitter-share-button' data-url='{{ canonical_url }}' data-text='{{ default_message }}' data-lang='en'>Tweet</a>"
        + "<a href='https://twitter.com/twitterapi' class='twitter-follow-button' data-show-count='false' data-lang='en'>Follow @twitterapi</a>";
    var scripts = [ "//platform.twitter.com/widgets.js", "//connect.facebook.net/en_US/all.js" ];


    me.init = function () {
        if (window.location.hostname.match(/^checkout\.shopify\.com$/)) {
            var content = document.getElementById('content');

            if (content) {
                var container = document.createElement('div');

                util.renderSimpleTemplate(container, sharePurchaseTemplate, config);

                // Add the div to the pag
                container.insertAfter(content, container);
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
            _willet.cart.init();
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