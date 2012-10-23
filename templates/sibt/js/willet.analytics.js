var _willet = _willet || {};  // ensure namespace is there

// Google Analytics events tracker
// requires server-side template vars:
// - evnt
// requires this module:
// - loader
_willet.analytics = (function (me) {
    var wm = _willet.mediator || {};

    // default actions
    me.defaultEvent = me.defaultEvent || '{{ evnt }}';
    me.gaq = null;
    me.gat = null;
    me.pageTracker = null;
    me.ANALYTICS_ID = me.ANALYTICS_ID || 'UA-23764505-9'; // DerpShop: UA-31001469-1

    me.init = me.init || function () {
        var domain = me.host || window.location.host;

        wm.fire('loadJS', [('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js']);
        me.gaq = window._gaq || document._gaq || [];
        me.gaq.push(function() {
            var ourTracker = _gat._createTracker(me.ANALYTICS_ID, 'willet');
            ourTracker._setDomainName(domain);
            ourTracker._setAllowLinker(true);
        });
    };

    // send some google analytics thing to the server.
    // message and extras are optional, but if you leave out message, you
    // aren't recording anything meaningful.
    me.store = me.store || function (message, extras) {
        var message = message || me.defaultEvent;

        if (!message) return;  // do not record nothing

        // extra google analytics component
        {% if debug %}
        // TODO: Distinguish between debug / non-debug
        {% endif %}

        // in-house memcache logging
        (new Image).src = "{{ URL }}{% url TrackTallyAction %}?evnt=" +
                          encodeURIComponent(message);
        try {
            // async
//            me.gaq.push([
//                '_trackEvent',
//                'TrackSIBTAction',
//                encodeURIComponent(message),
//                encodeURIComponent(extras)
//            ]);
            me.gat = me.gat || window._gat || document._gat || [];
            me.pageTracker = me.pageTracker || me.gat._getTrackerByName('willet');
            if (me.pageTracker) {
                me.pageTracker._trackEvent(
                    'TrackSIBTAction',
                    encodeURIComponent(message),
                    encodeURIComponent(extras)
                );
            }
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
} (_willet.analytics || {}));