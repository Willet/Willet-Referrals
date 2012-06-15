(function (w, d) {
    "use strict";
    /*
     * Willet's "Should I Buy This"
     * Copyright Willet Inc, 2012
     *
     * w and d are aliases of window and document.
     */

    var sys = {
        'debug': ('{{debug}}' === 'True'),
        '$_conflict': !(w.$ && w.$.fn && w.$.fn.jquery)
    };

    w._willet = w._willet || {};
    var _willet = w._willet;
    {% include "js/willet.mediator.js" %}
    {% include "js/willet.debug.js" %}
    {% include "js/willet.loader.js" %}
    {% include "js/willet.analytics.js" %}
    {% include "js/willet.colorbox.js" %}
    {% include "js/willet.sibt.js" %}

    // Load CSS onto the page.
    var colorbox_css = '{% spaceless %}{% include "../../plugin/templates/css/colorbox.css" %}{% endspaceless %}';
    var topbar_css = '{% spaceless %}{% include "../../plugin/templates/css/topbar.css" %}{% endspaceless %}';
    var popup_css = '{% spaceless %}{% include "../../plugin/templates/css/popup.css" %}{% endspaceless %}';
    var app_css = '{% spaceless %}{{ app_css }}{% endspaceless %}';

    // load CSS for colorbox as soon as possible!!
    var styles = [app_css, colorbox_css, topbar_css, popup_css];
    for (var i = 0; i < styles.length; i++) {
        _willet.mediator.fire('loadCSSText', styles[i]);
    }


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

            // jQuery shaker plugin
            (function(a){var b={};var c=4;a.fn.shaker=function(){b=a(this);b.css("position","relative");b.run=true;b.find("*").each(function(b,c){a(c).css("position","relative")});var c=function(){a.fn.shaker.animate(a(b))};setTimeout(c,25)};a.fn.shaker.animate=function(c){if(b.run==true){a.fn.shaker.shake(c);c.find("*").each(function(b,c){a.fn.shaker.shake(c)});var d=function(){a.fn.shaker.animate(c)};setTimeout(d,25)}};a.fn.shaker.stop=function(a){b.run=false;b.css("top","0px");b.css("left","0px")};a.fn.shaker.shake=function(b){var d=a(b).position();a(b).css("left",d["left"]+Math.random()<.5?Math.random()*c*-1:Math.random()*c)}})($);

            // jQuery cookie plugin (included to solve lagging requests)
            {% include '../../plugin/templates/js/jquery.cookie.js' %}

            _willet.mediator.fire('hasjQuery', $);
            _willet.mediator.fire('scriptComplete');
        });
    });

    // Go time! Load script dependencies
    try {
        // set up a list of scripts to load asynchronously.
        var scripts_to_load = [
            ('https:' == d.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js' // Google analytics
        ];

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