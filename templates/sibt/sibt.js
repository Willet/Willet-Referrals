(function (w, d) {
    "use strict";
    /*
     * Willet's "Should I Buy This"
     * Copyright Willet Inc, 2012
     *
     * w and d are aliases of window and document.
     */

    {% ifequal client.name "Shu Uemura USA" %}
        // do this first for shu uemura to "appear fast".
        // beware! everything is hardcoded.
        (function () {
            try {
                // try to "prefetch" the image
                (new Image).src = '//{{ DOMAIN }}/static/sibt/imgs/sibt-shu-askfriends-blue.png';
                console.log('preloading shu script');

                var shuTargetClass = '_vendor_sibt',
                    shuTarget = d.getElementsByClassName(shuTargetClass)[0];
                (function (style) {
                    console.log('preloading icon');
                    style.display = 'block';
                    style.width = '92px';
                    style.height = '24px';
                    style.clear = 'both';
                    style.backgroundImage = 'url("//{{ DOMAIN }}/static/sibt/imgs/sibt-shu-askfriends-blue.png")';
                    style.backgroundPosition = '3% 20%';
                })(shuTarget.style);
            } catch (e) {
                // too bad (including cases where console doesn't exist)
                console.log(e);
            }
        })();
    {% endifequal %}

    var sys = {
        'debug': ('{{debug}}' === 'True'),
        '$_conflict': !(w.$ && w.$.fn && w.$.fn.jquery)
    };

    w._willet = w._willet || {};
    var _willet = w._willet;

    if (_willet.sibt) {
        // if SIBT has already been loaded on this page, do not load again.
        if (window.console && window.console.log) {
            window.console.log(
                'Warning: Willet SIBT snippet appeared on page more than once'
            );
        }
        return;
    }

    {% include "js/willet.mediator.js" %}
    {% include "js/willet.debug.js" %}
    {% include "js/willet.browserdetection.js" %}
    {% include "js/willet.loader.js" %}
    {% include "js/willet.storage.js" %}
    {% include "js/willet.analytics.js" %}
    {% include "js/willet.sibt.js" %}
    {% include "js/willet.colorbox.js" %}

    // Load CSS onto the page.
    var colorbox_css = '{% spaceless %}{% include "../plugin/css/colorbox.css" %}{% endspaceless %}';
    var popup_css = '{% spaceless %}{% include "../plugin/css/popup.css" %}{% endspaceless %}';
    var app_css = '{% spaceless %}{{ app_css }}{% endspaceless %}';

    // load CSS for colorbox as soon as possible!!
    _willet.mediator.fire('loadCSSText', app_css + colorbox_css + popup_css);

    // Stores user_uuid for all browsers - differently for Safari.
    var setCookieStorageFlag = function () {
        w.cookieSafariStorageReady = true;
    };

    // Safari cookie storage backup
    var firstTimeSession = 0;
    var doSafariCookieStorage = function () {
        if (firstTimeSession === 0) {
            firstTimeSession = 1;
            d.getElementById('sessionform').submit()
            setTimeout(setCookieStorageFlag, 2000);
        }
    };

    // "Fixes" Safari's problems with XD-storage.
    if (navigator.userAgent.indexOf('Safari') !== -1) {
        var holder = d.createElement('div');
        var storageIframeLoaded = false;
        var storageIFrame = d.createElement('iframe');
        storageIFrame.setAttribute('src', window.location.protocol + "//{{ DOMAIN }}{% url UserCookieSafariHack %}");
        storageIFrame.setAttribute('id', "sessionFrame");
        storageIFrame.setAttribute('name', "sessionFrame");
        storageIFrame.setAttribute('onload', "doSafariCookieStorage();");
        storageIFrame.onload = storageIFrame.onreadystatechange = function() {
            var rs = this.readyState;
            if(rs && rs !== 'complete' && rs !== 'loaded') return;
            if(storageIframeLoaded) return;
            storageIframeLoaded = true;
            doSafariCookieStorage();
        };
        storageIFrame.style.display = 'none';

        var storageForm = d.createElement('form');
        storageForm.setAttribute('id', 'sessionform');
        storageForm.setAttribute('action', window.location.protocol + "//{{ DOMAIN }}{% url UserCookieSafariHack %}");
        storageForm.setAttribute('method', 'post');
        storageForm.setAttribute('target', 'sessionFrame');
        storageForm.setAttribute('enctype', 'application/x-www-form-urlencoded');
        storageForm.style.display = 'none';

        var storageInput = d.createElement('input');
        storageInput.setAttribute('type', 'text');
        storageInput.setAttribute('value', '{{user.uuid}}');
        storageInput.setAttribute('name', 'user_uuid');

        holder.appendChild(storageIFrame);
        storageForm.appendChild( storageInput );
        holder.appendChild(storageForm);
        d.body.appendChild(holder);
    } else {
        setCookieStorageFlag();
    }



    // Once all dependencies are loading, fire this function
    _willet.mediator.on('scriptsReady', function () {

        if (sys.$_conflict) {
            jQuery.noConflict(); // Suck it, Prototype!
        }

        // wait for DOM elements to appear + $ closure!
        jQuery(d).ready(function($) {
            _willet.mediator.fire('hasjQuery', $);
            _willet.mediator.fire('scriptComplete');
        });
    });

    // Go time! Load script dependencies
    try {
        // set up a list of scripts to load asynchronously.
        var scripts_to_load = [];

        // load localStorage variable into window if browser doesn't natively have one
        if (!w.localStorage) {
            scripts_to_load.push('//{{ DOMAIN }}/static/js/localstorage/storage.min.js');
        }

        // load analytics code if page doesn't already have it
        if (!w._gat) {
            scripts_to_load.push(
                ('https:' == d.location.protocol ? 'https://ssl' : 'http://www') + 
                '.google-analytics.com/ga.js'
            );
        }

        // turns out we need at least 1.4 for the $(<tag>,{props}) notation
        if (!w.jQuery || w.jQuery.fn.jquery < "1.4.4") {
            scripts_to_load.push('https://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.js');
        }

        _willet.mediator.fire('loadJS', {
            'scripts': scripts_to_load,
            'callback': _willet.mediator.callback('scriptsReady')
        });
    } catch (e) {
        var error   = encodeURIComponent("SIBT Error");
        var line    = e.number || e.lineNumber || "Unknown";
        var script  = encodeURIComponent("sibt.js: " + line);
        var message = e.stack || e.toString();
        var st      = encodeURIComponent(message);
        var params  = "error=" + error + "&script=" + script + "&st=" + st;
        var err_img = d.createElement("img");
        err_img.src = window.location.protocol + "//{{ DOMAIN }}{% url ClientSideMessage %}?" + params;
        err_img.style.display = "none";
        d.body.appendChild(err_img);

        _willet.mediator.fire('error', "Error:", line, message);
    }
})(window, document);
