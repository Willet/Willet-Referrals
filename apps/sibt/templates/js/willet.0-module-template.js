var _willet = _willet || {};  // ensure namespace is there

// module description comment
_willet.ModuleName = (function (me) {
    var wm = _willet.Mediator || {};

    // default actions
    me.defaultParams = me.defaultParams || null;

    me.customEvent = me.customEvent || function (params) {
        console.log('derp');
    };

    // set up your module hooks
    if (_willet.Mediator) {
        _willet.Mediator.on('customEvent', me.customEvent, defaultParams);
    }

    return me;
} (_willet.ModuleName || {}));