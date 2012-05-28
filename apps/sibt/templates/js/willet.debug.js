var _willet = _willet || {};  // ensure namespace is there

// willet debugger. This is mostly code by Nicholas Terwoord.
// requires server-side template vars:
// - debug
// - URL
_willet.debug = (function (me) {
    var wm = _willet.mediator || {};
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
            me.emailError(arguments[0]);
            log_array.push(arguments); // Add to logs
        };
    }

    // found this gem that Twitter uses:
    // window.console||function(){var a=["log","debug","info","warn","error","assert","dir","dirxml","group","groupEnd","time","timeEnd","count","trace","profile","profileEnd"];window.console={};for(var b=0;b<a.length;++b)window.console[a[b]]=function(){}}();

    me.register = me.register || function(callback) {
        // Register a callback to fire when debug.set is called
        callbacks.push(callback);
    };

    me.set = me.set || function(debug) {
        // Set debugging on (true) / off (false)
        me.log = (debug) ? _log : function() { log_array.push(arguments) };
        me.error = (debug) ? _error : function() { log_array.push(arguments) };
        isDebugging = debug;

        for(var i = 0; i < callbacks.length; i++) {
            callbacks[i](debug);
        }
    };

    me.isDebugging = me.isDebugging || function() {
        // True = printing to console & logs, False = only logs
        return isDebugging;
    };

    me.logs = me.logs || function () {
        // Returns as list of all log & error items
        return log_array;
    };

    me.set(isDebugging); //setup proper log functions

    me.emailError = me.emailError || function (msg) {
        // email if module-scope error is called.
        var error   = encodeURIComponent("SIBT Module Error");
        var script  = encodeURIComponent("sibt.js");
        var st      = encodeURIComponent(msg);
        var params  = "error=" + error + "&script=" + script + "&st=" + st;
        var err_img = d.createElement("img");
        err_img.src = "{{URL}}{% url ClientSideMessage %}?" + params;
        err_img.style.display = "none";
        d.body.appendChild(err_img);
    };

    // set up a hook to let log and error be fired
    if (wm) {
        wm.on('log', _log);
        wm.on('error', _error);
    }

    return me;
}(_willet.debug || {}));