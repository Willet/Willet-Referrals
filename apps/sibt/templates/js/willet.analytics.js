var _willet = _willet || {};  // ensure namespace is there

// Google Analytics events tracker
_willet.Analytics = (function (me) {
    var wm = _willet.Mediator || {};

    // default actions
    me.defaultEvent = me.defaultEvent || '{{ evnt }}';
    me.gaq = null;
    me.gat = null;
    me.pageTracker = null;
    me.ANALYTICS_ID = 'UA-23764505-9'; // DerpShop: UA-31001469-1

    me.init = me.init || function () {
        wm.fire('loadJS', [('https:' == d.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js']);
        me.gaq = window._gaq || document._gaq || [];
        me.gaq.push(['_setAccount', me.ANALYTICS_ID]);
        me.gaq.push(['_setDomainName', window.location.host]);
        me.gaq.push(['_setAllowLinker', true]);
    };

    // send some google analytics thing to the server.
    // message and extras are optional, but if you leave out message, you
    // aren't recording anything meaningful.
    me.store = me.store || function (message, extras) {
        var message = message || me.defaultEvent;

        if (!message) return;  // do not record nothing

        // extra google analytics component
        try {
            // async
            me.gaq.push([
                '_trackEvent',
                'TrackSIBTAction',
                encodeURIComponent(message),
                encodeURIComponent(extras)
            ]);
            me.gat = me.gat || window._gat || document._gat || [];
            me.pageTracker = me.pageTracker || me.gat._getTracker(me.ANALYTICS_ID);
            me.pageTracker._trackEvent(
                'TrackSIBTAction',
                encodeURIComponent(message),
                encodeURIComponent(extras)
            );
            wm.fire('log', "Success! We have secured the enemy intelligence: " + message);
        } catch (e) { // log() is {} on live.
            wm.fire('log', "We have DROPPED the enemy intelligence: " + e);
        }
    };

    // set up a hook to let storeAnalytics be fired
    if (wm) {
        wm.on('storeAnalytics', me.store, me.defaultEvent);
    }

    me.init();
    return me;
} (_willet.Analytics || {}));