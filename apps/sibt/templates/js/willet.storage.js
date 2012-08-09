var _willet = _willet || {};  // ensure namespace is there

// localStorage library
// (designed to be swapped in and out with other storage libraries, with
// its mediator interface constant)
// requires server-side template vars:
// - (none)
_willet.storage = (function (me) {
    var wm = _willet.mediator || {};

    // default actions
    me.localStorage = window.localStorage || null;

    me.get = me.get || function (name, defaultValue) {
        // will always return defaultValue if localStorage is not supported!
        if (me.localStorage) {
            var value = me.localStorage.getItem(name);
            if (value === null || value === undefined) {
                value = defaultValue;
            }
        } else {
            value = defaultValue;
            me.reportError();
        }
        return value;
    };
    me.read = me.get;  // compat alias

    me.set = me.set || function (name, value) {
        if (me.localStorage) {
            try {
                // why: http://stackoverflow.com/questions/2603682
                me.del(name);

                me.localStorage.setItem(name, value);
            } catch (err) {  // 95% QUOTA_EXCEEDED_ERR
                me.reportError('localStorage failed to set something: ' + err);
            }
        } else {
            me.reportError();
        }
    };
    me.create = me.set;  // compat alias

    me.del = me.del || function (name) {
        if (me.localStorage) {
            me.localStorage.removeItem(name);
        } else {
            me.reportError();
        }
    };

    me.reportError = me.reportError || function (msg) {
        // fire off a harshly-worded letter to the dev team about how
        // the browser is misbehaving.
        wm.fire('error', msg || 'localStorage could not be found on this browser!');
    };

    // set up your module hooks
    if (_willet.mediator) {
        // use mediator.getResult('storageGet', ...) to get a return value.
        _willet.mediator.on('storageGet', me.get);
        _willet.mediator.on('storageSet', me.set);
        _willet.mediator.on('storageDel', me.del);
    }

    return me;
} (_willet.storage || {}));