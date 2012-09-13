(function(window) {
	var trackEvent = function (category, action, value) {
	    var iframe = document.createElement( 'iframe' );
	    
	    // category and action are required.
	    // label (client id) will be figured out on the server side
	    // value is cohort id if available
	    if (!category || !action) {
	    	return;
	    }

	    value = value || "";

	    iframe.style.display = 'none';
        iframe.src = "https://willet-grigory.appspot.com/an/trackEvent?" +
                     "&category=" + category +
                     "&action=" + action +
                     "&value=" + value +
                     "&url=" + window.location.href;
        document.body.appendChild( iframe );
    };

    var fromLeadSpeaker = function() {
    	if (window.location.hash.indexOf("leadspeaker_on") != -1) {
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
    	if (window.location.pathname.indexOf("leadspeaker_cohort_id") == -1) {
    		return false;
    	}
    	cohort_id = window.location.href.split("leadspeaker_cohort_id=")[1];
    	cohort_id.replace("/#leadspeaker_on", "");
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
}(window));
