var _willet = _willet || {};  // ensure namespace is there

// Loader agent
// Loader.js() is a function written by Fraser Harris.
_willet.Loader = (function (me) {

    me.css = me.css || function (url) {
        var tag = document.createElement("link");
        tag.setAttribute("rel", "stylesheet");
        tag.setAttribute("type", "text/css");
        tag.setAttribute("href", url);
        document.getElementsByTagName("head")[0].appendChild(tag);
    };

    me.cssText = me.cssText || function (style) {
        var willet_style = document.createElement('style');
        willet_style.type = 'text/css';
        willet_style.setAttribute('type','text/css');
        willet_style.setAttribute('charset','utf-8');
        willet_style.setAttribute('media','all');
        try { // try inserting CSS all ways (IE)
            willet_style.styleSheet.cssText = style;
        } catch (e) { }
        try { // try inserting CSS all ways (DOM)
            willet_style.appendChild(document.createTextNode(style));
        } catch (e) { }
        head_elem.appendChild(willet_style);
    };

    me.js = function (param) {
        // Loads scripts in parallel, and executes param.callback when all are finished loading
        /* correct layout of param:
         * {
         *      'scripts': [url, url, url],
         *      'callback': func
         * }
         */
        var i, scripts_not_ready;
        i = scripts_not_ready = param.scripts.length;
        param.callback = param.callback || function () {};

        var script_loaded = function () {
            // Checks if the scripts are all loaded
            if (!--scripts_not_ready) {
                param.callback();  // Good to go!
            }
        };

        var load = function (url) {
            // Load one script
            var script = document.createElement('script');
            var loaded = false;
            script.setAttribute('type', 'text/javascript');
            script.setAttribute('src', url);
            script.onload = script.onreadystatechange = function() {
                var rs = this.readyState;
                if (loaded || (rs && rs !== 'complete' && rs !== 'loaded')) {
                    return;
                }
                loaded = true;
                document.body.removeChild(script); // Clean up DOM
                script_loaded(); // Script done, update manager
            };
            document.body.appendChild(script);
        };

        // Start asynchronously loading all scripts
        while (i--) {
            load(param.scripts[i], i);
        }
    };

    // set up your module hooks
    if (_willet.Mediator) {
        _willet.Mediator.on('loadCSS', me.css);
        _willet.Mediator.on('loadCSSText', me.cssText);
        _willet.Mediator.on('loadJS', me.js);
    }

    return me;
} (_willet.Loader || {}));