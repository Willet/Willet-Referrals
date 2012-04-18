(function() {
    // this code is a mod of the standard GA insert.
    var ANALYTICS_ID = 'UA-31001469-1';

    var _gaq = _gaq || [];
    _gaq.push(['_setAccount', ANALYTICS_ID]);
    _gaq.push(['_setDomainName', window.location.hostname]);
    _gaq.push(['_setAllowLinker', true]);
    _gaq.push(['_trackPageview']);

    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);

    window._willet = window._willet || {};
    window._willet.storeAnalytics = function (event, action, value) {
        // function signature is the same as the default storeAnalytics.
        // event (required)[, everything after it] (optional)
        // value must be an integer.
        var baby,
            CATEGORY_DEFAULT = 'Action',
            EVENT_DEFAULT = 'SIBTShowingButton',
            tracker,
            TRACKER_NAME = 'willet';

        tracker = _gat._getTrackerByName(TRACKER_NAME) ||
                  _gat._createTracker(ANALYTICS_ID, TRACKER_NAME);
        baby = [
            '_trackEvent',
            action || CATEGORY_DEFAULT, // category
            event || EVENT_DEFAULT, // action
            'user_uuid', // opt_label
            value || 1 // opt_value
        ];

        tracker._trackEvent(
            action || CATEGORY_DEFAULT, // category
            event || EVENT_DEFAULT, // action
            'user_uuid', // opt_label
            value || 1 // opt_value
        );
        console.log(baby);
    };
})();

document.getElementById('derp').onclick = function () {
    _willet.storeAnalytics('derp');
}