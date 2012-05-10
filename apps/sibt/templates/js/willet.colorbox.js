var _willet = _willet || {};  // ensure namespace is there

// le colorbox for willet (has a custom name, willet_colorbox)
_willet.Colorbox = (function (me) {

    me._cboxobj = null;

    me.defaultParams = me.defaultParams || {
        transition: 'fade',
        close: '',
        scrolling: false,
        iframe: true,
        initialWidth: 0,
        initialHeight: 0,
        innerWidth: '600px',
        innerHeight: '420px',
        fixed: true,
        onClosed: function () {}
    };

    me.init = me.init || function () {
        me._cboxobj = me._cboxobj || $.willet_colorbox || jQuery.willet_colorbox;
        if (!me._cboxobj) { // colorbox cannot be loaded twice on a page.
            $.getScript('{{URL}}/s/js/jquery.colorbox.js', function () {
                if (jQuery.willet_colorbox) {
                    $.willet_colorbox = jQuery.willet_colorbox;
                }
                me._cboxobj = $.willet_colorbox;
                me._cboxobj.init();

                // watch for message; Create IE + others compatible event handler
                $(window).bind('onmessage message', function(e) {
                    if (e.originalEvent.data === 'close') {
                        me._cboxobj.close();
                    }
                });
            });
        }
    };

    // well, opens it.
    // if you don't supply params, the default ones will be used instead.
    me.open = me.open || function (options) {
        me._cboxobj = me._cboxobj || $.willet_colorbox || jQuery.willet_colorbox;
        if (!me._cboxobj) { // colorbox cannot be loaded twice on a page.
            me.init();
        }

        if (me._cboxobj) {
            _willet.Mediator.fire('log', "Colorbox module: opening colorbox");
            me._cboxobj(options);
        } else { // backup
            _willet.Mediator.fire('log', "Colorbox module: opening window");
            var width = parseInt(options.innerWidth);
            var height = parseInt(options.innerHeight);
            var left = (screen.width - width) / 2;
            var top = (screen.height - height) / 2;
            var new_window = window.open(
                options.href, // url
                '_blank', // name
                'width=' + width + ',' +
                'height=' + height + ',' +
                'left=' + left + ',' +
                'top=' + top,
                true //.preserve history
            );
            new_window.focus();
        }
    };

    // set up your module hooks
    if (_willet.Mediator) {
        _willet.Mediator.on('hasjQuery', me.init);
        _willet.Mediator.on('openColorbox', me.open, me.defaultParams);
    }

    return me;
} (_willet.Colorbox || {}));