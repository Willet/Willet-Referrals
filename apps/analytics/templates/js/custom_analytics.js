(function() {
    // this code is a mod of the standard GA insert.
    var ANALYTICS_ID = 'UA-31001469-1';

    var _gaq = _gaq || [];
    _gaq.push(['_setAccount', ANALYTICS_ID]);
    // _gaq.push(['_setDomainName', window.location.host]);
    _gaq.push(['_setDomainName', 'none']); // https://developers.google.com/analytics/devguides/collection/gajs/gaTrackingSite#domainToNone
    _gaq.push(['_setAllowLinker', true]);
    // _gaq.push(['_trackPageview']);

    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();