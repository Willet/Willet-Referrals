var _willet = _willet || {};  // ensure namespace is there

// Browser detection module
// http://www.quirksmode.org/js/detect.html
_willet.browser = (function (me) {
    // browser.name, browser.version, and browser.os will be available to you.

    var wm = _willet.mediator || {};

    me.init = me.init || function () {
        me.name = me.searchString(me.dataBrowser) || 'unknown';
        me.version = me.searchVersion(window.navigator.userAgent)
                  || this.searchVersion(window.navigator.appVersion)
                  || 'unknown';
        this.os = this.searchString(this.dataOS) || 'unknown';
    };

    me.searchString = me.searchString || function (data) {
        for (var i = 0; i < data.length; i++) {
            var dataString = data[i].string;
            var dataProp = data[i].prop;
            this.versionSearchString = data[i].versionSearch || data[i].identity;
            if (dataString) {
                if (dataString.indexOf(data[i].subString) != -1)
                    return data[i].identity;
            }
            else if (dataProp)
                return data[i].identity;
        }
    };

    me.searchVersion = me.searchVersion || function (dataString) {
        var index = dataString.indexOf(this.versionSearchString);
        if (index == -1) return;
        return parseFloat(
            dataString.substring(index + this.versionSearchString.length+1));
    };

    me.dataBrowser = me.dataBrowser || [{
        string: navigator.userAgent,
        subString: "Chrome",
        identity: "Chrome"
    }, {
        string: navigator.userAgent,
        subString: "OmniWeb",
        versionSearch: "OmniWeb/",
        identity: "OmniWeb"
    }, {
        string: navigator.vendor,
        subString: "Apple",
        identity: "Safari",
        versionSearch: "Version"
    }, {
        prop: window.opera,
        identity: "Opera",
        versionSearch: "Version"
    }, {
        string: navigator.vendor,
        subString: "iCab",
        identity: "iCab"
    }, {
        string: navigator.vendor,
        subString: "KDE",
        identity: "Konqueror"
    }, {
        string: navigator.userAgent,
        subString: "Firefox",
        identity: "Firefox"
    }, {
        string: navigator.vendor,
        subString: "Camino",
        identity: "Camino"
    }, {       // for newer Netscapes (6+)
        string: navigator.userAgent,
        subString: "Netscape",
        identity: "Netscape"
    }, {
        string: navigator.userAgent,
        subString: "MSIE",
        identity: "Explorer",
        versionSearch: "MSIE"
    }, {
        string: navigator.userAgent,
        subString: "Gecko",
        identity: "Mozilla",
        versionSearch: "rv"
    }, {       // for older Netscapes (4-)
        string: navigator.userAgent,
        subString: "Mozilla",
        identity: "Netscape",
        versionSearch: "Mozilla"
    }];

    me.dataOS = me.dataOS || [{
        string: navigator.platform,
        subString: "Win",
        identity: "Windows"
    }, {
        string: navigator.platform,
        subString: "Mac",
        identity: "Mac"
    }, {
        string: navigator.userAgent,
        subString: "iPhone",
        identity: "iPhone/iPod"
    }, {
        string: navigator.platform,
        subString: "Linux",
        identity: "Linux"
    }];

    // set up your module hooks
    if (_willet.mediator) {
        _willet.mediator.on('init', me.init);
        _willet.mediator.on('detectBrowsers', me.init);
    }

    return me;
} (_willet.browser || {}));