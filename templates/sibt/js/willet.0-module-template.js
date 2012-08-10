var _willet = _willet || {};  // ensure namespace is there

// module description comment
// requires server-side template vars:
// - abc
_willet.moduleName = (function (me) {
    var wm = _willet.mediator || {};

    // default actions
    me.defaultParams = me.defaultParams || null;

    me.customEvent = me.customEvent || function (params) {
        console.log('derp');
    };

    me.autoTriggeredEvent = me.autoTriggeredEvent || function (params) {
        console.log('autoTriggeredEvent will be called when ' +
                    'triggeredEvent is fired');
    };

    // set up your module hooks
    if (_willet.mediator) {
        _willet.mediator.on('customEvent', me.customEvent, defaultParams);
    }

    return me;
} (_willet.moduleName || {}));