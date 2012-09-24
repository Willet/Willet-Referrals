var willetTracking = (function ($, window, document) {
    "use strict";

    var category = "",
        landing_site = "{{ landing_site }}",

        trackEvent = function (category, action, value) {
            var iframe = document.createElement('iframe');

            // category and action are required.
            if (!category || !action) {
                return;
            }

            value = value || "";

            iframe.style.display = 'none';
            iframe.src = "{{ SECURE_URL }}{% url TrackEvent %}?" +
                         "category=" + category +
                         "&action=" + action +
                         "&value=" + value +
                         "&pathname=" + window.location.pathname +
                         "&hostname=" + "{{ shop_hostname }}" || window.location.hostname;

            document.body.appendChild(iframe);
        },

        onCartPage = function () {
            if (window.location.pathname === "/cart") {
                return true;
            }
            return false;
        },

        onThankYouPage = function () {
            if (window.location.hostname === "checkout.shopify.com") {
                return true;
            }
            return false;
        },

        fromLeadSpeaker = function () {
            if (window.location.pathname.indexOf("leadspeaker_cohort_id") !== -1) {
                return true;
            }
            return false;
        },

        referrerName = function () {
            var referrers = {
                "facebook.com": "facebook",
                "t.co": "twitter",
                "pinterest.com": "pinterest",
                "reddit.com": "reddit",
                "tumblr.com": "tumblr"
            }, host;

            if (document.referrer === "") {
                return "noref";
            }

            host = parseUri(document.referrer).host;
            // want top level domain name (i.e. tumblr.com, not site.tumblr.com)
            host = referrers[host.split(".").slice(host.split(".").length - 2, host.split(".").length).join(".")];

            if (referrers[host] === undefined) {
                return host;
            }

            return referrers[host];
        },

        getCohortId = function () {
            if (!fromLeadSpeaker()) {
                return false;
            }
            var cohort_id = window.location.href.split("leadspeaker_cohort_id=")[1];
            return cohort_id;
        },

        CartButtonTracking = (function () {
            var cohort_id = getCohortId() || "",
                action = "add_to_cart",

                // set listener for clicks on "add to cart"
                init = function () {
                    // switch away from using page-supplied jquery....
                    $("#add-to-cart").click(function () {
                        willetTracking.cart_button.click();
                    });
                },

                trackAdd = function () {
                    trackEvent(category, action, cohort_id);
                };

            return {
                "init": init,
                "click": trackAdd
            };
        }()),

        ProductTracking = (function () {
            var cohort_id = getCohortId() || "",
                action = "open_product",

                init = function () {
                    trackEvent(category, action, cohort_id);
                };

            return {
                "init": init
            };
        }()),

        CartPageTracking = (function () {
            var init = function () {
                var leadspeaker_category = willetTracking.cookies.read("leadspeaker_category") || "unknown",
                    leadspeaker_cid = willetTracking.cookies.read("leadspeaker_cid") || "",
                    action = "open_cart";

                trackEvent(leadspeaker_category, action, leadspeaker_cid);
            };

            return {
                "init": init
            };
        }()),

        ThankYouTracking = (function () {
            var init = function () {
                var action = "thankyou_page",
                    // this assumes that landing_site will end, if it's there, in our cohort_id
                    split_url = landing_site.split("leadspeaker_cohort_id="),
                    leadspeaker_category = "unkown",
                    leadspeaker_cid = "";

                // in the instance of tracking.js invoked through script_tags
                // and not through additional script added through store admin
                if (!landing_site) {
                    return;
                }

                // from us, but not sure which social network we're coming from
                if (split_url.length !== 1) {
                    leadspeaker_category = "leadspeaker";
                    leadspeaker_cid = split_url[1];
                }

                trackEvent(leadspeaker_category, action, leadspeaker_cid);
            };

            return {
                "init": init
            };
        }()),

        Cookies = (function () {
            // Generic cookie library
            // Source: http://www.quirksmode.org/js/cookies.html
            var create = function (name, value, days) {
                    var expires = "",
                        date = new Date();

                    if (days) {
                        date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
                        expires = "; expires=" + date.toGMTString();
                    }
                    document.cookie = name + "=" + value + expires + "; path=/";
                },

                read = function (name) {
                    var nameEQ = name + "=",
                        ca = document.cookie.split(';'),
                        c,
                        i;

                    for (i = 0; i < ca.length; i++) {
                        c = ca[i];
                        while (c.charAt(0) === ' ') {
                            c = c.substring(1, c.length);
                        }
                        if (c.indexOf(nameEQ) === 0) {
                            return c.substring(nameEQ.length, c.length);
                        }
                    }
                    return null;
                },

                erase = function (name) {
                    create(name, "", -1);
                };

            return {
                "create": create,
                "read": read,
                "erase": erase
            };
        }()),

        init = function () {
            var cohort_id = getCohortId() || "";

            if (fromLeadSpeaker()) {
                category = "leadspeaker";
            } else {
                category = "unknown";
            }

            category += "_" + referrerName();

            if (onCartPage()) {
                CartPageTracking.init();

            } else if (onThankYouPage()) {
                ThankYouTracking.init();

            // on product page
            } else {
                // set tracking cookies
                willetTracking.cookies.create("leadspeaker_category", category, 7);
                if (cohort_id) {
                    willetTracking.cookies.create("leadspeaker_cid", cohort_id, 7);
                }

                ProductTracking.init();
                CartButtonTracking.init();
            }
        },

        // parseUri 1.2.2
        // (c) Steven Levithan <stevenlevithan.com>
        // MIT License

        parseUri = function (str) {
            var o   = parseUri.options,
                m   = o.parser[o.strictMode ? "strict" : "loose"].exec(str),
                uri = {},
                i   = 14;

            while (i--) uri[o.key[i]] = m[i] || "";

            uri[o.q.name] = {};
            uri[o.key[12]].replace(o.q.parser, function ($0, $1, $2) {
                if ($1) uri[o.q.name][$1] = $2;
            });

            return uri;
        };

        parseUri.options = {
            strictMode: false,
            key: ["source","protocol","authority","userInfo","user","password","host","port","relative","path","directory","file","query","anchor"],
            q:   {
                name:   "queryKey",
                parser: /(?:^|&)([^&=]*)=?([^&]*)/g
            },
            parser: {
                strict: /^(?:([^:\/?#]+):)?(?:\/\/((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?))?((((?:[^?#\/]*\/)*)([^?#]*))(?:\?([^#]*))?(?:#(.*))?)/,
                loose:  /^(?:(?![^:@]+:[^:@\/]*@)([^:\/?#.]+):)?(?:\/\/)?((?:(([^:@]*)(?::([^:@]*))?)?@)?([^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?)/
            }
        };

    return {
        "init": init,
        "cart_button": CartButtonTracking,
        "cookies": Cookies
    };
}($, window, document));

willetTracking.init();