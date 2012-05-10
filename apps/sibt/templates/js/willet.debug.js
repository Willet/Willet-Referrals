var _willet = _willet || {};  // ensure namespace is there

// willet debugger
_willet.debug = (function (me) {
    var isDebugging = ('{{ debug }}' === 'True'),
        callbacks = [],
        log_array = [],
        _log = function() { log_array.push(arguments); },
        _error = function() { log_array.push(arguments); };

    if (typeof(window.console) === 'object'
        && ( ( typeof(window.console.log) === 'function'
        && typeof(window.console.error) ==='function' )
        || (typeof(window.console.log) === 'object' // IE
        && typeof(window.console.error) ==='object') )) {
        _log = function () {
            if (window.console.log.apply) {
                window.console.log.apply(window.console, arguments);
            } else {
                window.console.log(arguments);
            }
            log_array.push(arguments); // Add to logs
        };
        _error = function () {
            if (window.console.error.apply) {
                window.console.error.apply(window.console, arguments);
            } else {
                window.console.error(arguments);
            }
            log_array.push(arguments); // Add to logs
        };
    }

    me.register = function(callback) {
        // Register a callback to fire when debug.set is called
        callbacks.push(callback);
    };

    me.set = function(debug) {
        // Set debugging on (true) / off (false)
        me.log = (debug) ? _log : function() { log_array.push(arguments) };
        me.error = (debug) ? _error : function() { log_array.push(arguments) };
        isDebugging = debug;

        for(var i = 0; i < callbacks.length; i++) {
            callbacks[i](debug);
        }
    };

    me.isDebugging = function() {
        // True = printing to console & logs, False = only logs
        return isDebugging;
    };

    me.logs = function () {
        // Returns as list of all log & error items
        return log_array;
    };

    me.set(isDebugging); //setup proper log functions


    // set up a hook to let log and error be fired
    if (_willet.Mediator) {
        _willet.Mediator.on('log', me._log);
        _willet.Mediator.on('error', me._error);
    }

    return me;
}(_willet.debug || {}));