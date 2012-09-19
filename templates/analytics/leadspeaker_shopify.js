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
                     "&url=" + window.location.hostname;

        {% if client %}
            iframe.src += "&client=" + "{{ client }}";
        {% endif %}

        {% if user %}
            iframe.src += "&user=" + "{{ user }}";
        {% endif %}

        document.body.appendChild( iframe );
    };

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

    var CartTracking = (function() {
        var cohort_id = getCohortId() || "",
            action = "add_to_cart";

        // set listener for clicks on "add to cart"
        var init = function() {
            // switch away from using page-supplied jquery....
            $("#add-to-cart").click(function() {
                WILLET_TRACKING.cart.add();
            })
        }

        var trackAdd = function() {
            trackEvent(category, action, cohort_id);
        }

        return {
            "init": init,
            "add": trackAdd
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

    var init = function() {
        if (fromLeadSpeaker()) {
            category = "leadspeaker";
        } else {
            category = "unknown";
        }

        if (fromWhichNetwork() == "facebook") {
            category += "_facebook";
        }

        // @TODO: invoke these conditionally if on product page or on cart page
        ProductTracking.init();
        CartTracking.init();
    }

    return {
        "init": init,
        "cart": CartTracking
    }
})($, window, document);

WILLET_TRACKING.init();