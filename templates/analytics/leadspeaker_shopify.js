(function(window) {
	var trackEvent = function (category, action, value) {
        console.log("trackEvent: ", category, action, value);
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
                     "&url=" + window.location.href;

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
            console.log("from leadspeaker");
			return true;
		}
        console.log("not from leadspeaker");
		return false;
    }

    var fromWhichNetwork = function() {
    	var referrers = {
    		"https://www.facebook.com/": "facebook",
    		"http://www.facebook.com/": "facebook"}

        console.log("from network: ", referrers[document.referrer]);
    	return referrers[document.referrer];
    }

    var getCohortId = function() {
    	if (!fromLeadSpeaker()) {
            console.log("no cohort id");
    		return false;
    	}
    	cohort_id = window.location.href.split("leadspeaker_cohort_id=")[1];
    	console.log("cohort id", cohort_id);
        return cohort_id;
    }

    var category = "";
    var action = "";
    var cohort_id = getCohortId() || "";

    if (fromLeadSpeaker()) {
    	category = "leadspeaker";
    	action = "open_product";
    } else {
    	category = "unknown";
    }

    if (fromWhichNetwork() == "facebook") {
    	category += "_facebook";
    }

    trackEvent(category, action, cohort_id);
})(window);
