var _willet = _willet || {};  // ensure namespace is there

// bulletin board for module hooks
_willet.Mediator = (function (me) {
    me.hooks = me.hooks || {
        /* event1: [
            [func, params],
            [func, params],
            [func, params],
            ...
        ], event2: [
            ...
        ]
        */
    };

    // trigger an event. fire all functions assigned to that event.
    me.fire = me.fire || function (event, params) {
        if (!me.hooks[event]) {
            return; // no functions registered with this event.
        }
        for (var i = 0; i < me.hooks[event].length; i++) {
            try {
                params = params || me.hooks[event][i][1];
                me.hooks[event][i][0](params);
            } catch (err) {
                // continue running other hooks.
                me.fire('log', 'failed to load a hook: ' + err);
            }
        }
        return me;
    };

    // subscribing to an event - fire a function when it happens.
    me.on = me.on || function (event, func, params) {
        var hooks = me.hooks;
        hooks[event] = hooks[event] || [];
        hooks[event].push([func, params]);
        return me;
    };
    me.listen = me.on;  // alias

    // unregistering an event.
    me.off = me.off || function (event) {
        delete me.hooks[event];
        return me;
    };

    // replace all previous hooks with this single one.
    me.replace = me.replace || function (event, func, params) {
        me.off(event).on(event, func, params);
        return me;
    };

    return me;
} (_willet.Mediator || {}));