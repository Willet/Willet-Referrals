var _willet = _willet || {};  // ensure namespace is there

// Google Analytics events tracker
_willet.Analytics = (function (me) {

    // default actions
    me.default = me.default || '{{ evnt }}';
    me.gaq = null;
    me.gat = null;
    me.pageTracker = null;

    me.init = me.init || function () {
        var ANALYTICS_ID = 'UA-23764505-9'; // DerpShop: UA-31001469-1
        me.gaq = window._gaq || document._gaq || [];
        me.gaq.push(['_setAccount', ANALYTICS_ID]);
        me.gaq.push(['_setDomainName', window.location.host]);
        me.gaq.push(['_setAllowLinker', true]);
    };

    // send some google analytics thing to the server.
    me.store = me.store || function (message, extras) {
        var message = message || me.default;

        // extra google analytics component
        try {
            // async
            me.gaq.push([
                '_trackEvent',
                'TrackSIBTAction',
                encodeURIComponent(message),
                encodeURIComponent(extras)
            ]);
            if (!pageTracker) {
                // synchronous tracking
            }
            me.gat = me.gat || window._gat || document._gat || [];
            me.pageTracker = me.pageTracker || me.gat._getTracker(ANALYTICS_ID);
            me.pageTracker._trackEvent(
                'TrackSIBTAction',
                encodeURIComponent(message),
                encodeURIComponent(extras)
            );
            console.log("Success! We have secured the enemy intelligence.");
        } catch (e) { // log() is {} on live.
            console.log("We have dropped the enemy intelligence: " + e);
        }
    };

    // set up a hook to let storeAnalytics be fired
    if (_willet.Mediator) {
        _willet.Mediator.on('storeAnalytics', me.store, me.default);
    }

    me.init();
    return me;
} (_willet.Analytics || {}));