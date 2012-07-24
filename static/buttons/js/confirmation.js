/** ShopConnection - Confirmation Page Social Sharing
  * Copyright 2012, Willet, Inc.
 **/

// Example URL: https://checkout.shopify.com/orders/962072/403f3cf2ca6ec05a118864ee80ba30a5?store=blah.myshopify.com&facebooKUsername=blah&twitterUsername=willetinc

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
            conditionalIndex = template.search(ifStatementRe);
        }

        // Second handle variables of the form {{ var_name }}
        for (var i in values) {
            if (values.hasOwnProperty(i)) {
                template = template.replace('{{ '+ i +' }}', values[i]);
            }
        }
        return template;
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

_willet = (function (me) {
    var util = me.util,
        debug = me.debug,
        cookies = me.cookies;

    var HEAD = document.getElementsByTagName('head')[0];

    var sharePurchaseTemplate = ""
        + "<div class='sharing'>"
        + "  <p>Follow us to get the latest updates:</p>"
        + "  <ul>"
        + "    {% if facebookUsername %}<li><div class='fb-like' href='{{ shop }}' data-send='true' data-layout='button_count' data-width='150' data-show-faces='false'></div></li>{% endif %}"
        + "    {% if pinterestUsername %}<li>"
        + "      <div class='pinterest-button'>"
        + "        <a target='_blank' href='//pinterest.com/{{ pinterestUsername }}/'>"
        + "          <span>Follow us on </span>"
        + "          <i></i>"
        + "        </a>"
        + "      </div>"
        + "    </li>{% endif %}"
        + "    {% if twitterUsername %}<li><a href='//twitter.com/{{ twitterUsername }}' class='twitter-follow-button' data-show-count='false' data-lang='en'>Follow @{{ twitterUsername }}</a></li>{% endif %}"
        + "  </ul>"
        + "</div>";

    var styleRules = ""
        + "div.sharing {"
        + "    padding: 0 15px;"
        + "    margin: 10px 0 0 0;"
        + "    background-color:#FFF !important;"
        + "    color: #000 !important;"
        + "}"
        + "div.sharing>p {"
        + "    text-align: center;"
        + "}"
        + "div.sharing ul {"
        + "    list-style-type:none;"
        + "    padding: 0 40px;"
        + "    line-height:40px;"
        + "    margin-bottom: 0;"
        + "}"
        + "div.sharing li {"
        + "    display: inline-table;"
        + "    width: 140px;"
        + "}"
        + ".pinterest-button,"
        + ".pinterest-button a,"
        + ".pinterest-button span {"
        + "        display: -moz-inline-stack;"
        + "        display: inline-block;"
        + "        vertical-align: top;"
        + "        zoom: 1;"
        + "        margin: 0;"
        + "}"
        + ".pinterest-button {"
        + "        text-align: left;"
        + "        white-space: nowrap;"
        + "        max-width: 100%;"
        + "        font-family: 'Helvetica Neue', Arial, sans-serif;"
        + "        font-size: 11px;"
        + "        font-style: normal;"
        + "        font-variant: normal;"
        + "        font-weight: 500;"
        + "        line-height: 18px;"
        + "        color: #333 !important;"
        + "        background: transparent;"
        + "}"
        + ".pinterest-button a {"
        + "        position: relative;"
        + "        background-color: #f8f8f8;"
        + "        background-image: -webkit-gradient(linear,left top,left bottom,from(#fff),to(#dedede));"
        + "        background-image: -moz-linear-gradient(top,#fff,#dedede);"
        + "        background-image: -o-linear-gradient(top,#fff,#dedede);"
        + "        background-image: -ms-linear-gradient(top,#fff,#dedede);"
        + "        background-image: linear-gradient(top,#fff,#dedede);"
        + "        border: rgb(175,169,169) solid 1px;"
        + "        -moz-border-radius: 3px;"
        + "        -webkit-border-radius: 3px;"
        + "        border-radius: 3px;"
        + "        color: rgb(208,28,43) !important;"
        + "        font-weight: 500;"
        + "        text-shadow: 0 1px 0 rgba(255,255,255,.5);"
        + "        -webkit-user-select: none;"
        + "        -moz-user-select: none;"
        + "        -o-user-select: none;"
        + "        user-select: none;"
        + "        cursor: pointer;"
        + "        height: 18px;"
        + "        max-width: 98%;"
        + "        overflow: hidden;"
        + "}"
        + ".pinterest-button a:focus,"
        + ".pinterest-button a:hover,"
        + ".pinterest-button a:active {"
        + "        border-color: #bbb;"
        + "        background-color: #f8f8f8;"
        + "        background-image: -webkit-gradient(linear,left top,left bottom,from(#f8f8f8),to(#d9d9d9));"
        + "        background-image: -moz-linear-gradient(top,#f8f8f8,#d9d9d9);"
        + "        background-image: -o-linear-gradient(top,#f8f8f8,#d9d9d9);"
        + "        background-image: -ms-linear-gradient(top,#f8f8f8,#d9d9d9);"
        + "        background-image: linear-gradient(top,#f8f8f8,#d9d9d9);"
        + "        -webkit-box-shadow: none;"
        + "        -moz-box-shadow: none;"
        + "        box-shadow: none;"
        + "}"
        + ".pinterest-button a:active {"
        + "        background-color: #efefef;"
        + "        -webkit-box-shadow: inset 0 3px 5px rgba(0,0,0,0.1);"
        + "        -moz-box-shadow: inset 0 3px 5px rgba(0,0,0,0.1);"
        + "        box-shadow: inset 0 3px 5px rgba(0,0,0,0.1);"
        + "}"
        + ".pinterest-button i {"
        + "        position: absolute;"
        + "        top: 50%;"
        + "        right: 3px;"
        + "        margin-top: -7px;"
        + "        width: 14px;"
        + "        height: 14px;"
        + "        background: transparent url(//social-referral.appspot.com/static/buttons/imgs/pinterest-p-14x14.png) 0 0 no-repeat;"
        + "        background-image: url(data:image/png;base64,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);"
        + "}"
        + ".pinterest-button span {"
        + "        padding: 0 22px 0 5px;"
        + "        white-space: nowrap;"
        + "}";

    var scripts = [ "//platform.twitter.com/widgets.js", "//connect.facebook.net/en_US/all.js#xfbml=1" ];

    //var config = {
    //    'shopName': 'Kovacek And Sons',
    //    'shop': 'kovacek-and-sons3219.myshopify.com',
    //    'message': 'We would appreciate if we could update you every once in a while',
    //    'facebookUsername': 'fjharris',
    //    'pinterestUsername': 'fraserharris',
    //    'twitterUsername': 'fjharris'
    //};

    me.getConfigurationFromURL = function () {
        var scripts = document.getElementsByTagName('script');

        var parseQueryString = function (src) {
            var qs = src.indexOf('?') ? src.substr(src.indexOf('?')+1) : null,
                params = {};

            if (qs) {
                // A little hack - convert the query string into JSON format and parse it
                // '&' -> ',' and '=' -> ':'
                var raw_obj = JSON.parse('{"' + decodeURIComponent(qs.replace(/&/g, "\",\"").replace(/=/g,"\":\"")) + '"}');
                params = {
                    "enabled": raw_obj.enabled && (raw_obj.enabled === "true"),
                    "shop":  raw_obj.shop || '',
                    "facebookUsername": raw_obj.facebook_username || '',
                    "twitterUsername":  raw_obj.twitter_username || '',
                    "pinterestUsername": raw_obj.pinterest_username || ''
                };
            }

            return params;
        }

        // Find this script
        for (var i = scripts.length-1; i >= 0; i--) {
            if (scripts[i].src.match('/b/shopify/load/confirmation.js')) {
                // parse query string
                return parseQueryString( scripts[i].src );
            }
        }
    }


    me.init = function () {
        // Only do something on the order confirmation page
        if (window.location.hostname.match(/^checkout\.shopify\.com$/)) {
            // Get hook on page
            var content = document.getElementById('content');

            if (content) {
                var container = document.createElement('div');

                // Retrieve configuration from script query string
                var config = me.getConfigurationFromURL();

                if (config.enabled) {
                    container.innerHTML = util.renderSimpleTemplate(sharePurchaseTemplate, config);
                    container.appendChild( util.createStyle(styleRules) );

                    for (var i = scripts.length; i >= 0; i--) {
                        HEAD.appendChild( util.createScript(scripts[i]) );
                    }

                    // Add the div to the page
                    content.parentNode.insertBefore(container, content);
                } else {
                    debug.log("Confirmation widget not loaded: disabled by configuration");
                }
            }
        } else {
            debug.log("Confirmation widget not loaded: not on confirmation page");
        }
    };

    return me;
}(_willet));

try {
    if (_willet) {
        var info = _willet.util.detectBrowser();
        _willet.debug.set(true); //set to true if you want logging turned on

        if (!_willet.buttonsLoaded
            && !(info.browser === "Explorer" && info.version <= 7)
            && !(info.browser === "An unknown browser")
            && !(_willet.util.isLocalhost()))
        {
            _willet.init();
        } else {
            _willet.debug.log("Confirmation widget not loaded: Unsupported browser or localhost");
        }
    }

} catch(e) {
    //assume, potentially wrongfully, that we have access to _willet.util.error
    _willet.util.error(e, {
       "message": "We're not exactly sure what went wrong. Check the stack trace provided.",
       "type": "Willet.UnexpectedError"
    });
}