var WILLET_TRACKING = (function($, window, document) {
    var category = "";

	var trackEvent = function (category, action, value) {
	    var iframe = document.createElement( 'iframe' );
	    
	    // category and action are required.
	    // value is cohort id if available
	    if (!category || !action) {
	    	return;
	    }

	    value = value || "";

	    iframe.style.display = 'none';
        iframe.src = "{{ SECURE_URL }}/an/trackEvent?" +
                     "&category=" + category +
                     "&action=" + action +
                     "&value=" + value +
                     "&hostname=" + window.location.hostname +
                     "&pathname=" + window.location.pathname;

        {% if client %}
            iframe.src += "&client=" + "{{ client.uuid }}";
        {% endif %}

        {% if user %}
            iframe.src += "&user=" + "{{ user.uuid }}";
        {% endif %}

        document.body.appendChild( iframe );
    };

    var onCartPage = function() {
        if (window.location.pathname == "/cart") {
            return true;
        }
        return false;
    }

    var fromLeadSpeaker = function() {
    	if (window.location.pathname.indexOf("leadspeaker_cohort_id") != -1) {
			return true;
		}
		return false;
    }

    var fromWhichNetwork = function() {
    	var referrers = {
    		"https://www.facebook.com/": "facebook",
    		"http://www.facebook.com/": "facebook"}

    	return referrers[document.referrer];
    }

    var getCohortId = function() {
    	if (!fromLeadSpeaker()) {
    		return false;
    	}
    	cohort_id = window.location.href.split("leadspeaker_cohort_id=")[1];
        return cohort_id;
    }

    var CartButtonTracking = (function() {
        var cohort_id = getCohortId() || "",
            action = "add_to_cart";

        // set listener for clicks on "add to cart"
        var init = function() {
            // switch away from using page-supplied jquery....
            $("#add-to-cart").click(function() {
                WILLET_TRACKING.cart_button.click();
            })
        }

        var trackAdd = function() {
            trackEvent(category, action, cohort_id);
        }

        return {
            "init": init,
            "click": trackAdd
        }
    }());

    var ProductTracking = (function() {
        var cohort_id = getCohortId() || "",
            action = "open_product";

        var init = function() {
            trackEvent(category, action, cohort_id);
        }

        return {
            "init": init
        }
    }());

    var CartPageTracking = (function() {
        var init = function() {
            var leadspeaker_category = Cookies.read("leadspeaker_category") || "unknown",
                leadspeaker_cid = Cookies.read("leadspeaker_cid") || "",
                action = "open_cart";

            trackEvent(leadspeaker_category, action, leadspeaker_cid);
        }

        return {
            "init": init
        }
    }());

    var Cookies = (function() {
        // Generic cookie library
        // Source: http://www.quirksmode.org/js/cookies.html
        var create = function (name, value, days) {
            if (days) {
                var date = new Date();
                date.setTime(date.getTime()+(days*24*60*60*1000));
                var expires = "; expires="+date.toGMTString();
            } else var expires = "";
            document.cookie = name+"="+value+expires+"; path=/";
        }

        var read = function (name) {
            var nameEQ = name + "=";
            var ca = document.cookie.split(';');
            for(var i=0;i < ca.length;i++) {
                var c = ca[i];
                while (c.charAt(0)==' ') c = c.substring(1,c.length);
                if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
            }
            return null;
        }

        var erase = function (name) {
            create(name,"",-1);
        }

        return {
            "create": create,
            "read": read,
            "erase": erase
        }
    }());

    var init = function() {
        var cohort_id = getCohortId() || "";

        if (fromLeadSpeaker()) {
            category = "leadspeaker";
        } else {
            category = "unknown";
        }

        if (fromWhichNetwork() == "facebook") {
            category += "_facebook";
        }

        if (onCartPage()) {
            CartPageTracking.init();

        // on product page
        } else {
            // set tracking cookies
            Cookies.create("leadspeaker_category", category, 7);
            if (cohort_id) {
                Cookies.create("leadspeaker_cid", cohort_id, 7);
            }
        
            ProductTracking.init();
            CartButtonTracking.init();
        }
    }

    return {
        "init": init,
        "cart_button": CartButtonTracking
    }
})($, window, document);

WILLET_TRACKING.init();