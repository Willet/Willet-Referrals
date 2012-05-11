var _willet = _willet || {};  // ensure namespace is there

// bulletin board for module hooks.
// idea from http://goo.gl/mLVK2; contains no code from it.
_willet.mediator = (function (me) {
    // example on: _willet.mediator.on('eventName', function (params) {
    //     alert(params);
    // });
    // example fire: _willet.mediator.fire('eventName', 'hello world');

    // you shouldn't need to manipulate this object, but you can if you want.
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

    // get a callback for a given event.
    // it allows other applications to call our registered events.
    me.callback = me.callback || function (event) {
        return function (params) {
            me.fire(event, params);
        };
    }

    // trigger an event. fire all functions assigned to that event.
    // params is optional.
    me.fire = me.fire || function (event, params) {
        if (!me.hooks[event]) {
            return me; // no functions registered with this event.
        }
        // console.log(me.hooks[event].length + ' events to run');
        for (var i = 0; i < me.hooks[event].length; i++) {
            try {
                params = params || me.hooks[event][i][1];

                // the following shitty line executes one of the callback
                // functions for this event.
                me.hooks[event][i][0](params);

                // if (event !== 'log') {
                //     me.fire('log', 'called event: ' + event);
                // }
            } catch (err) {
                // continue running other hooks.
                if (event !== 'log') {  // prevent stack overflow (fo cereals)
                    me.fire('log', 'failed to call an event: ' + err);
                }
            }
        }
        return me;
    };

    // subscribing to an event - fire a function when it happens. (FIFO)
    // params is optional.
    me.on = me.on || function (event, func, params) {
        var hooks = me.hooks;
        hooks[event] = hooks[event] || [];
        hooks[event].push([func, params]);
        return me;
    };
    // aliases. just because they are there and they make sense,
    // it doesn't mean you *should* use all of them.
    // try to stick to one of them in each project.
    me.listen = me.register = me.on;

    // unregistering an event.
    // name of the event is required.
    me.off = me.off || function (event) {
        delete me.hooks[event];
        return me;
    };
    me.unregister = me.on;

    // replace all previous hooks with this single one.
    // params is optional.
    me.replace = me.replace || function (event, func, params) {
        me.off(event).on(event, func, params);
        return me;
    };

    return me;
} (_willet.mediator || {}));