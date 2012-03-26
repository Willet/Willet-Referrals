/*
 * Buttons JS. Copyright Willet Inc, 2012
 */
;var WILLET = (function(me) {
    var debug = false; //set to false or remove when pushing live!

    var console;
    if(!debug) {
        console = { log: function () {}, error: function () {} };
    } else {
        console = window.console;
    }

    // Private variables
    var PRODUCT_JSON = window.location + '.json';
    var COOKIE_NAME = "_willet_smart_buttons";
    var COOKIE_EXPIRY_IN_DAYS = 30;

    var HEAD = document.getElementsByTagName('head')[0];
    var BUTTONS_DIV_ID = '_willet_buttons_app';
    var DETECT_NETWORKS_DIV_ID = '_willet_buttons_detect_networks';

    var DOMAIN = /:\/\/([^\/]+)/.exec(window.location.href)[1];
    var PROTOCOL = debug ? "http:" : window.location.protocol;

    var ELEMENT_NODE = 1;

    var LOGGED_IN_NETWORKS = {};
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

                    var link = createElement({
                        "nodename": "a",
                        "href": 'http://www.tumblr.com/share',
                        "title": "Share on Tumblr",
                        "innerHTML": "Share on Tumblr",
                        "style": {
                            "display": 'inline-block',
                            "textIndent": '-9999px',
                            "textAlign": 'left',
                            "width": '63px',
                            "height": '20px',
                            "background": "url('http://platform.tumblr.com/v1/share_2.png') top left no-repeat transparent",
                            "styleFloat": 'left', // IE
                            "cssFloat": 'left', // FF, Webkit
                            "marginRight": '5px',
                            "marginTop": '0'
                        }
                    });

                    button.appendChild(link);
                    return button;
                }
            }
        },
        "Facebook": {
            "detect": {
                "method": "api",
                "func": function() {
                    //build the fb-root element if it does not exist
                    if(!document.getElementById("fb-root")) {
                        var fbRoot = createElement({
                            "nodename": "div",
                            "id": "fb-root"
                        });
                        document.body.appendChild(fbRoot);
                    }

                    var detectFBLoggedIn = function() {
                        FB.init({ appId:'132803916820614', status:true,  cookie:true, xfbml:true});
                        FB.getLoginStatus(function(response){
                            var status = response.status != "unknown";
                            updateLoggedInStatus("Facebook", status);
                        });
                    }

                    if (!window.FB) {
                        window.fbAsyncInit = function() {
                            detectFBLoggedIn();
                        };

                        //load the FB SDK if it isn't already loaded;
                        (function(d){
                        var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
                        js = d.createElement('script'); js.id = id; js.async = true;
                        js.src = "//connect.facebook.net/en_US/all.js";
                        d.getElementsByTagName('head')[0].appendChild(js);
                        }(document));
                    } else {
                        detectFBLoggedIn();
                    }
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
                }
            }
        },
        "Pinterest": {
            "detect": {
                "method": "image-hack",
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

                    var link = createElement({
                        "nodename": "a",
                        "href": "http://pinterest.com/pin/create/button/?" +
                            "url=" + encodeURIComponent( window.location.href ) + 
                            "&media=" + encodeURIComponent( params.photo ) + 
                            "&description=" + encodeURIComponent("I found this on " + params.domain),
                        "className": "pin-it-button",
                        "innerHTML": "Pin It"
                    });
                    link.setAttribute('count-layout', "horizontal");

                    button.appendChild(link);
                    return button;
                }
            }
        },
        "Twitter": {
            "detect": {
                "method": "image-hack",
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

                    var link = createElement({
                        "nodename": "a",
                        "href": "https://twitter.com/share",
                        "className": "twitter-share-button"
                    });

                    link.setAttribute('data-lang','en');
                    link.setAttribute('data-count', ( params.buttonCount ? 'horizontal' : 'none' ));

                    button.appendChild(link);
                    return button;
                }
            }
        }, 
        "GooglePlus": {
            "detect": {
                "method": "image-hack",
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
                    button.innerHTML = "<g:plusone size='medium'"+ (params.buttonCount ? '' : " annotation='none'") +"></g:plusone>";
                    
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

                    var link = createElement({
                        "nodename": "a",
                        "id": "FancyButton",
                        "href": u
                    });
                    
                    // a.setAttribute('data-count', ( button_count ? 'true' : 'false' ));
                    button.appendChild(link);
                    return button;
                }
            }
        }
    };

    // Private functions
    // Source: JSON2, Author: Douglas Crockford, http://www.JSON.org/json2.js
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

    // Source: http://www.quirksmode.org/js/cookies.html
    var createCookie = function (name, value, days) {
        if (days) {
            var date = new Date();
            date.setTime(date.getTime()+(days*24*60*60*1000));
            var expires = "; expires="+date.toGMTString();
        }
        else var expires = "";
        document.cookie = name+"="+value+expires+"; path=/";
    };

    // Source: http://www.quirksmode.org/js/cookies.html
    var readCookie = function (name) {
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
    var eraseCookie = function (name) {
        createCookie(name,"",-1);
    };

    var ajax = function(config) {
        var AJAX_RESPONSE_AVAILABLE = 4;
        var HTTP_OK = 200;

        var url = config.url || "";
        var success = config.success || function() {};
        var error = config.error || function() {};
        var method = config.method || "GET";
        var async = config.async || true;

        if (url === "") {
            //TODO: Error
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

    var xHasKeyY = function(dict, key) {
        return dict[key] || false;
    };

    // Source: http://stackoverflow.com/a/383245/165988
    // Slightly modified
    var mergeObject = function (src, obj) {
        for (var prop in obj) {
            try {
                // Property in destination object set; update its value.
                if ( obj[prop].constructor==Object ) {
                    src[prop] = mergeObject(src[prop], obj[prop]);
                } else {
                    src[prop] = obj[prop];
                }
            } catch(e) {
                // Property in destination object not set; create it and set its value.
                src[prop] = obj[prop];
            }
        }
        return src;
    }

    var createElement = function (config) {
        var nodeName = config.nodename || "";

        if (nodeName === "") {
            //ERROR
        }

        var modifiedConfig = config;
        delete modifiedConfig.nodename;

        var element = document.createElement(nodeName);
        
        //apply all properties to this
        element = mergeObject(element, modifiedConfig);

        return element;
    };

    var createBasicButton = function (params) {
        var id = params.id || '';
        var buttonSpacing = params.buttonSpacing || "0";
        var d = createElement({
            "nodename": "div",
            "style": {
                "styleFloat": "left", //IE
                "cssFloat": "left", //FF, Webkit
                "marginTop": "0",
                "marginLeft": "0",
                "marginBottom": "0",
                "marginRight": buttonSpacing,
                "paddingTop": "0",
                "paddingLeft": "0",
                "paddingBottom": "0",
                "paddingRight": "0",
                "border": "none",
                "display": "block",
                "visibility": "visible",
                "height": "21px",
                "position": "relative",
                "overflow": "hidden"
            },
            "name": "button",
            "id": "_willet_" + id,
            "className": "_willet_social_button"
        });
        return d;
    }

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
        return (requiredButtons.length) ? requiredButtons : ['Fancy','Pinterest','Tumblr']; // default for backwards compatibilty;
    };

    var updateLoggedInStatus = function(network, status) {
        LOGGED_IN_NETWORKS[network] = status;
        createCookie(COOKIE_NAME, JSON.stringify(LOGGED_IN_NETWORKS), COOKIE_EXPIRY_IN_DAYS);
    }

    // Public functions
    me.detectNetworks = function () {
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

        var detectNetworksDiv = createElement({
            "nodename": "div",
            "id": DETECT_NETWORKS_DIV_ID
        });

        for (network in SUPPORTED_NETWORKS) {
            var detectNetwork = SUPPORTED_NETWORKS[network]["detect"];
            switch (detectNetwork["method"]) {
                case "image-hack":
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
        document.body.appendChild(detectNetworksDiv);
    };

    me.createButtons = function(productData) {
        console.log("Buttons: finding buttons placeholder on page");
        var buttonsDiv = document.getElementById(BUTTONS_DIV_ID);

        if (buttonsDiv && window._willet_iframe_loaded == undefined) {
            var buttonCount = (buttonsDiv.getAttribute('button_count') === 'true');
            var buttonSpacing = (buttonsDiv.getAttribute('button_spacing') ?  buttonsDiv.getAttribute('button_spacing') : '5') + 'px';
            var buttonPadding = (buttonsDiv.getAttribute('button_padding') ? buttonsDiv.getAttribute('button_padding') : '5') + 'px';

            buttonsDiv = mergeObject(buttonsDiv, {
                "style": {
                    "styleFloat": "left", //IE
                    "cssFloat": "left", //FF, Webkit
                    "minWidth": "240px",
                    "height": "22px",
                    "padding": buttonPadding,
                    "border": "none",
                    "margin": "0"
                }    
            });

            // Grab the photo
            var photo = '';
            if ( productData.product.images[0] != null ) {
                photo = productData.product.images[0].src;
            }

            var requiredButtons = [];
            var networksJSON = readCookie(COOKIE_NAME) || "";
            if (networksJSON === "") {
                requiredButtons = getRequiredButtonsFromElement(buttonsDiv);

                // Now remove all children of #_willet_buttons_app
                var i = buttonsDiv.childNodes.length;
                while (i--) {
                    buttonsDiv.removeChild(buttonsDiv.childNodes[i]);
                }
            } else {
                //TODO: Wrap in try / catch
                var networks = JSON.parse(networksJSON);
                for (var network in networks) {
                    if (xHasKeyY(SUPPORTED_NETWORKS, network)
                        && networks[network] === true) {
                        requiredButtons.push(network);
                    }
                }
            }

            for (var index in requiredButtons) {
                var network = requiredButtons[index];
                var button = SUPPORTED_NETWORKS[network]["button"];
                buttonsDiv.appendChild(button.create({
                    "domain": DOMAIN,
                    "photo": photo,
                    "data": productData,
                    "buttonCount": buttonCount,
                    "buttonSpacing": buttonSpacing,
                    "buttonPadding": buttonPadding
                }));

                var script = createElement({
                    "nodename": "script",
                    "type": "text/javascript",
                    "src": button["script"]
                });
                HEAD.appendChild(script);
                console.log('Buttons: '+ network +' attached');
            }

            // Make visible if hidden
            buttonsDiv.style.display = 'block';

            console.log('Buttons: Done!');
        } else {
            console.log('Buttons: could not find buttons placeholder on page');
        }
    };

    me.init = function() {
        if (!readCookie(COOKIE_NAME)) {
            me.detectNetworks();
        }

        if(!debug) {
            try {
                console.log("Buttons: initiating product.json request")
                ajax({
                    url: PRODUCT_JSON,
                    method: "GET",
                    success: function(request) {
                        console.log("Buttons: recieved product.json request");
                        var data;
                        try {
                            data = JSON.parse(request.responseText);
                        } catch (e) {
                            console.log("Buttons: could not parse product info, stopping.");
                            return;
                        }
                        if (data) {
                            // Proceed!
                            me.createButtons(data);
                        }
                    }
                });   
            } catch(e) {
                console.log("Buttons: request for product.json failed");
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

    me.init();
}(WILLET || {}));