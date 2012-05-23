{%block js_includes %}{% endblock %}

var _willet = _willet || {};  // ensure namespace is there

{% include "../../../sibt/templates/js/willet.mediator.js" %}
{% include "../../../sibt/templates/js/willet.loader.js" %}
{% include "../../../sibt/templates/js/willet.analytics.js" %}

/* jQuery postMessage - v0.5 - 9/11/2009
 * http://benalman.com/projects/jquery-postmessage-plugin/
 * (c) 2009 Ben Alman, MIT / GPL
 */

(function($){
  '$:nomunge'; // Used by YUI compressor.

  // A few vars used in non-awesome browsers.
  var interval_id,
    last_hash,
    cache_bust = 1,

    // A var used in awesome browsers.
    rm_callback,

    // A few convenient shortcuts.
    window = this,
    FALSE = !1,

    // Reused internal strings.
    postMessage = 'postMessage',
    addEventListener = 'addEventListener',

    p_receiveMessage,

    // I couldn't get window.postMessage to actually work in Opera 9.64!
    has_postMessage = window[postMessage] && !$.browser.opera;

  // Method: jQuery.postMessage
  //
  // This method will call window.postMessage if available, setting the
  // targetOrigin parameter to the base of the target_url parameter for maximum
  // security in browsers that support it. If window.postMessage is not available,
  // the target window's location.hash will be used to pass the message. If an
  // object is passed as the message param, it will be serialized into a string
  // using the jQuery.param method.
  //
  // Usage:
  //
  // > jQuery.postMessage( message, target_url [, target ] );
  //
  // Arguments:
  //
  //  message - (String) A message to be passed to the other frame.
  //  message - (Object) An object to be serialized into a params string, using
  //    the jQuery.param method.
  //  target_url - (String) The URL of the other frame this window is
  //    attempting to communicate with. This must be the exact URL (including
  //    any query string) of the other window for this script to work in
  //    browsers that don't support window.postMessage.
  //  target - (Object) A reference to the other frame this window is
  //    attempting to communicate with. If omitted, defaults to `parent`.
  //
  // Returns:
  //
  //  Nothing.

  $[postMessage] = function( message, target_url, target ) {
    if ( !target_url ) { return; }

    // Serialize the message if not a string. Note that this is the only real
    // jQuery dependency for this script. If removed, this script could be
    // written as very basic JavaScript.
    message = typeof message === 'string' ? message : $.param( message );

    // Default to parent if unspecified.
    target = target || parent;

    if ( has_postMessage ) {
      // The browser supports window.postMessage, so call it with a targetOrigin
      // set appropriately, based on the target_url parameter.
      target[postMessage]( message, target_url.replace( /([^:]+:\/\/[^\/]+).*/, '$1' ) );

    } else if ( target_url ) {
      // The browser does not support window.postMessage, so set the location
      // of the target to target_url#message. A bit ugly, but it works! A cache
      // bust parameter is added to ensure that repeat messages trigger the
      // callback.
      target.location = target_url.replace( /#.*$/, '' ) + '#' + (+new Date) + (cache_bust++) + '&' + message;
    }
  };

  // Method: jQuery.receiveMessage
  //
  // Register a single callback for either a window.postMessage call, if
  // supported, or if unsupported, for any change in the current window
  // location.hash. If window.postMessage is supported and source_origin is
  // specified, the source window will be checked against this for maximum
  // security. If window.postMessage is unsupported, a polling loop will be
  // started to watch for changes to the location.hash.
  //
  // Note that for simplicity's sake, only a single callback can be registered
  // at one time. Passing no params will unbind this event (or stop the polling
  // loop), and calling this method a second time with another callback will
  // unbind the event (or stop the polling loop) first, before binding the new
  // callback.
  //
  // Also note that if window.postMessage is available, the optional
  // source_origin param will be used to test the event.origin property. From
  // the MDC window.postMessage docs: This string is the concatenation of the
  // protocol and "://", the host name if one exists, and ":" followed by a port
  // number if a port is present and differs from the default port for the given
  // protocol. Examples of typical origins are https://example.org (implying
  // port 443), http://example.net (implying port 80), and http://example.com:8080.
  //
  // Usage:
  //
  // > jQuery.receiveMessage( callback [, source_origin ] [, delay ] );
  //
  // Arguments:
  //
  //  callback - (Function) This callback will execute whenever a <jQuery.postMessage>
  //    message is received, provided the source_origin matches. If callback is
  //    omitted, any existing receiveMessage event bind or polling loop will be
  //    canceled.
  //  source_origin - (String) If window.postMessage is available and this value
  //    is not equal to the event.origin property, the callback will not be
  //    called.
  //  source_origin - (Function) If window.postMessage is available and this
  //    function returns false when passed the event.origin property, the
  //    callback will not be called.
  //  delay - (Number) An optional zero-or-greater delay in milliseconds at
  //    which the polling loop will execute (for browser that don't support
  //    window.postMessage). If omitted, defaults to 100.
  //
  // Returns:
  //
  //  Nothing!

  $.receiveMessage = p_receiveMessage = function( callback, source_origin, delay ) {
    if ( has_postMessage ) {
      // Since the browser supports window.postMessage, the callback will be
      // bound to the actual event associated with window.postMessage.

      if ( callback ) {
        // Unbind an existing callback if it exists.
        rm_callback && p_receiveMessage();

        // Bind the callback. A reference to the callback is stored for ease of
        // unbinding.
        rm_callback = function(e) {
          if ( ( typeof source_origin === 'string' && e.origin !== source_origin )
            || ( $.isFunction( source_origin ) && source_origin( e.origin ) === FALSE ) ) {
            return FALSE;
          }
          callback( e );
        };
      }

      if ( window[addEventListener] ) {
        window[ callback ? addEventListener : 'removeEventListener' ]( 'message', rm_callback, FALSE );
      } else {
        window[ callback ? 'attachEvent' : 'detachEvent' ]( 'onmessage', rm_callback );
      }

    } else {
      // Since the browser sucks, a polling loop will be started, and the
      // callback will be called whenever the location.hash changes.

      interval_id && clearInterval( interval_id );
      interval_id = null;

      if ( callback ) {
        delay = typeof source_origin === 'number'
          ? source_origin
          : typeof delay === 'number'
            ? delay
            : 100;

        interval_id = setInterval(function(){
          var hash = document.location.hash,
            re = /^#?\d+&/;
          if ( hash !== last_hash && re.test( hash ) ) {
            last_hash = hash;
            callback({ data: hash.replace( re, '' ) });
          }
        }, delay );
      }
    }
  };

})(jQuery);

// ColorBox v1.3.17.2 - a full featured, light-weight, customizable lightbox based on jQuery 1.3+
// Copyright (c) 2011 Jack Moore - jack@colorpowered.com
// Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

(function ($, document, window) {
    var
    // ColorBox Default Settings.
    // See http://colorpowered.com/colorbox for details.
    defaults = {
        transition: "elastic",
        speed: 300,
        width: false,
        initialWidth: "600",
        innerWidth: false,
        maxWidth: false,
        height: false,
        initialHeight: "450",
        innerHeight: false,
        maxHeight: false,
        scalePhotos: true,
        scrolling: true,
        inline: false,
        html: false,
        iframe: false,
        fastIframe: true,
        photo: false,
        href: false,
        title: false,
        rel: false,
        opacity: 0.9,
        preloading: true,
        current: "image {current} of {total}",
        previous: "previous",
        next: "next",
        close: "close",
        friendPick: "friendPick",
        open: false,
        returnFocus: true,
        loop: true,
        slideshow: false,
        slideshowAuto: true,
        slideshowSpeed: 2500,
        slideshowStart: "start slideshow",
        slideshowStop: "stop slideshow",
        onOpen: false,
        onLoad: false,
        onComplete: false,
        onCleanup: false,
        onClosed: false,
        overlayClose: true,
        escKey: true,
        arrowKey: true,
        top: false,
        bottom: false,
        left: false,
        right: false,
        fixed: false,
        data: false
    },

    // Abstracting the HTML and event identifiers for easy rebranding
    colorbox = 'willet_colorbox',
    prefix = 'cbox',
    willet_prefix = 'willet_' + prefix,
    boxElement = willet_prefix + 'Element',

    // Events
    event_open = willet_prefix + '_open',
    event_load = willet_prefix + '_load',
    event_complete = willet_prefix + '_complete',
    event_cleanup = willet_prefix + '_cleanup',
    event_closed = willet_prefix + '_closed',
    event_purge = willet_prefix + '_purge',

    // Special Handling for IE
    isIE = $.browser.msie && !$.support.opacity, // Detects IE6,7,8.  IE9 supports opacity.  Feature detection alone gave a false positive on at least one phone browser and on some development versions of Chrome, hence the user-agent test.
    isIE6 = isIE && $.browser.version < 7,
    event_ie6 = willet_prefix + '_IE6',

    // Cached jQuery Object Variables
    $overlay,
    $box,
    $wrap,
    $content,
    $topBorder,
    $leftBorder,
    $rightBorder,
    $bottomBorder,
    $related,
    $window,
    $loaded,
    $loadingBay,
    $loadingOverlay,
    $title,
    $current,
    $slideshow,
    $next,
    $prev,
    $close,
    $groupControls,

    // Variables for cached values or use across multiple functions
    settings,
    interfaceHeight,
    interfaceWidth,
    loadedHeight,
    loadedWidth,
    element,
    index,
    photo,
    open,
    active,
    closing,
    handler,
    loadingTimer,
    publicMethod;

    // ****************
    // HELPER FUNCTIONS
    // ****************

    // jQuery object generator to reduce code size
    function $div(id, cssText, div) {
        div = document.createElement('div');
        if (id) {
            div.id = willet_prefix + id;
        }
        div.style.cssText = cssText || '';
        return $(div);
    }

    // Convert '%' and 'px' values to integers
    function setSize(size, dimension) {
        return Math.round((/%/.test(size) ? ((dimension === 'x' ? $window.width() : $window.height()) / 100) : 1) * parseInt(size, 10));
    }

    // Checks an href to see if it is a photo.
    // There is a force photo option (photo: true) for hrefs that cannot be matched by this regex.
    function isImage(url) {
        return settings.photo || /\.(gif|png|jpg|jpeg|bmp)(?:\?([^#]*))?(?:#(\.*))?$/i.test(url);
    }

    // Assigns function results to their respective settings.  This allows functions to be used as values.
    function makeSettings(i) {
        settings = $.extend({}, $.data(element, colorbox));

        for (i in settings) {
            if ($.isFunction(settings[i]) && i.substring(0, 2) !== 'on') { // checks to make sure the function isn't one of the callbacks, they will be handled at the appropriate time.
                settings[i] = settings[i].call(element);
            }
        }

        settings.rel = settings.rel || element.rel || 'nofollow';
        settings.href = settings.href || $(element).attr('href');
        settings.title = settings.title || element.title;

        if (typeof settings.href === "string") {
            settings.href = $.trim(settings.href);
        }
    }

    function trigger(event, callback) {
        if (callback) {
            callback.call(element);
        }
        $.event.trigger(event);
    }

    // Slideshow functionality
    function slideshow() {
        var
        timeOut,
        className = willet_prefix + "Slideshow_",
        click = "click." + prefix,
        start,
        stop,
        clear;

        if (settings.slideshow && $related[1]) {
            start = function () {
                $slideshow
                    .text(settings.slideshowStop)
                    .unbind(click)
                    .bind(event_complete, function () {
                        if (index < $related.length - 1 || settings.loop) {
                            timeOut = setTimeout(publicMethod.next, settings.slideshowSpeed);
                        }
                    })
                    .bind(event_load, function () {
                        clearTimeout(timeOut);
                    })
                    .one(click + ' ' + event_cleanup, stop);
                $box.removeClass(className + "off").addClass(className + "on");
                timeOut = setTimeout(publicMethod.next, settings.slideshowSpeed);
            };

            stop = function () {
                clearTimeout(timeOut);
                $slideshow
                    .text(settings.slideshowStart)
                    .unbind([event_complete, event_load, event_cleanup, click].join(' '))
                    .one(click, start);
                $box.removeClass(className + "on").addClass(className + "off");
            };

            if (settings.slideshowAuto) {
                start();
            } else {
                stop();
            }
        } else {
            $box.removeClass(className + "off " + className + "on");
        }
    }

    function launch(target) {
        if (!closing) {

            element = target;

            makeSettings();

            $related = $(element);

            index = 0;

            if (settings.rel !== 'nofollow') {
                $related = $('.' + boxElement).filter(function () {
                    var relRelated = $.data(this, colorbox).rel || this.rel;
                    return (relRelated === settings.rel);
                });
                index = $related.index(element);

                // Check direct calls to ColorBox.
                if (index === -1) {
                    $related = $related.add(element);
                    index = $related.length - 1;
                }
            }

            if (!open) {
                open = active = true; // Prevents the page-change action from queuing up if the visitor holds down the left or right keys.

                $box.show();

                if (settings.returnFocus) {
                    try {
                        element.blur();
                        $(element).one(event_closed, function () {
                            try {
                                this.focus();
                            } catch (e) {
                                // do nothing
                            }
                        });
                    } catch (e) {
                        // do nothing
                    }
                }

                // +settings.opacity avoids a problem in IE when using non-zero-prefixed-string-values, like '.5'
                $overlay.css({"opacity": +settings.opacity, "cursor": settings.overlayClose ? "pointer" : "auto"}).show();

                // Opens inital empty ColorBox prior to content being loaded.
                settings.w = setSize(settings.initialWidth, 'x');
                settings.h = setSize(settings.initialHeight, 'y');
                publicMethod.position();

                if (isIE6) {
                    $window.bind('resize.' + event_ie6 + ' scroll.' + event_ie6, function () {
                        $overlay.css({width: $window.width(), height: $window.height(), top: $window.scrollTop(), left: $window.scrollLeft()});
                    }).trigger('resize.' + event_ie6);
                }

                trigger(event_open, settings.onOpen);

                $groupControls.add($title).hide();

                $close.html(settings.close).show();
            }

            publicMethod.load(true);
        }
    }

    // ****************
    // PUBLIC FUNCTIONS
    // Usage format: $.fn.colorbox.close();
    // Usage from within an iframe: parent.$.fn.colorbox.close();
    // ****************

    publicMethod = $.fn[colorbox] = $[colorbox] = function (options, callback) {
        var $this = this;

        options = options || {};

        if (!$this[0]) {
            if ($this.selector) { // if a selector was given and it didn't match any elements, go ahead and exit.
                return $this;
            }
            // if no selector was given (ie. $.colorbox()), create a temporary element to work with
            $this = $('<a/>');
            options.open = true; // assume an immediate open
        }

        if (callback) {
            options.onComplete = callback;
        }

        $this.each(function () {
            $.data(this, colorbox, $.extend({}, $.data(this, colorbox) || defaults, options));
            $(this).addClass(boxElement);
        });

        if (($.isFunction(options.open) && options.open.call($this)) || options.open) {
            launch($this[0]);
        }

        return $this;
    };

    // Initialize ColorBox: store common calculations, preload the interface graphics, append the html.
    // This preps ColorBox for a speedy open when clicked, and minimizes the burdon on the browser by only
    // having to run once, instead of each time colorbox is opened.
    publicMethod.init = function () {
        // Create & Append jQuery Objects
        $window = $(window);
        $box = $div().attr({id: colorbox, 'class': isIE ? willet_prefix + (isIE6 ? 'IE6' : 'IE') : ''});
        $overlay = $div("Overlay", isIE6 ? 'position:absolute' : '').hide();

        $wrap = $div("Wrapper");
        $content = $div("Content").append(
            $loaded = $div("LoadedContent", 'width:0; height:0; overflow:hidden'),
            $loadingOverlay = $div("LoadingOverlay").add($div("LoadingGraphic")),
            $title = $div("Title"),
            $current = $div("Current"),
            $next = $div("Next"),
            $prev = $div("Previous"),
            $slideshow = $div("Slideshow").bind(event_open, slideshow),
            $close = $div("Close")
        );
        $wrap.append( // The 3x3 Grid that makes up ColorBox
            $div().append(
                $div("TopLeft"),
                $topBorder = $div("TopCenter"),
                $div("TopRight")
            ),
            $div(false, 'clear:left').append(
                $leftBorder = $div("MiddleLeft"),
                $content,
                $rightBorder = $div("MiddleRight")
            ),
            $div(false, 'clear:left').append(
                $div("BottomLeft"),
                $bottomBorder = $div("BottomCenter"),
                $div("BottomRight")
            )
        ).children().children().css({'float': 'left'});

        $loadingBay = $div(false, 'position:absolute; width:9999px; visibility:hidden; display:none');

        $('body').prepend($overlay, $box.append($wrap, $loadingBay));

        $(document.getElementById(willet_prefix + "TopRight")).click( function() { publicMethod.topRightClose(); } );

        $content.children()
        .hover(function () {
            $(this).addClass('hover');
        }, function () {
            $(this).removeClass('hover');
        }).addClass('hover');

        // Cache values needed for size calculations
        interfaceHeight = $topBorder.height() + $bottomBorder.height() + $content.outerHeight(true) - $content.height();//Subtraction needed for IE6
        interfaceWidth = $leftBorder.width() + $rightBorder.width() + $content.outerWidth(true) - $content.width();
        loadedHeight = $loaded.outerHeight(true) - 20;
        loadedWidth = $loaded.outerWidth(true);

        // Setting padding to remove the need to do size conversions during the animation step.
        $box.css({"padding-bottom": interfaceHeight, "padding-right": interfaceWidth}).hide();

        // Setup button events.
        // Anonymous functions here keep the public method from being cached, thereby allowing them to be redefined on the fly.
        $next.click(function () {
            publicMethod.next();
        });
        $prev.click(function () {
            publicMethod.prev();
        });
        $close.click(function () {
            publicMethod.close();
        });

        $groupControls = $next.add($prev).add($current).add($slideshow);

        // Adding the 'hover' class allowed the browser to load the hover-state
        // background graphics in case the images were not part of a sprite.  The class can now can be removed.
        $content.children().removeClass('hover');

        $overlay.click(function () {
            if (settings.overlayClose) {
                publicMethod.overlayClose();
            }
        });

        // Set Navigation Key Bindings
        $(document).bind('keydown.' + prefix, function (e) {
            var key = e.keyCode;
            if (open && settings.escKey && key === 27) {
                e.preventDefault();
                publicMethod.overlayClose();
            }
            if (open && settings.arrowKey && $related[1]) {
                if (key === 37) {
                    e.preventDefault();
                    $prev.click();
                } else if (key === 39) {
                    e.preventDefault();
                    $next.click();
                }
            }
        });
    };

    {%block js_analytics %}
    publicMethod.topRightClose = function( ) {
        publicMethod.storeAnalytics( publicMethod.closeState );
        publicMethod.close();
    };

    publicMethod.overlayClose = function( ) {
        publicMethod.storeAnalytics( "SIBTOverlayCancelled" );
        publicMethod.close();
    };

    publicMethod.storeAnalytics = function( message ) {
        if (_willet && _willet.mediator) {
            _willet.mediator.fire('storeAnalytics', message);
        }
    };

    publicMethod.closeState = "SIBTAskIframeCancelled";
    {% endblock %}

    publicMethod.remove = function () {
        $box.add($overlay).remove();
        $('.' + boxElement).removeData(colorbox).removeClass(boxElement);
    };

    publicMethod.position = function (speed, loadedCallback) {
        var top = 0, left = 0;

        $window.unbind('resize.' + prefix);

        // remove the modal so that it doesn't influence the document width/height
        $box.hide();

        if (settings.fixed && !isIE6) {
            $box.css({position: 'fixed'});
        } else {
            top = $window.scrollTop();
            left = $window.scrollLeft();
            $box.css({position: 'absolute'});
        }

        // keeps the top and left positions within the browser's viewport.
        if (settings.right !== false) {
            left += Math.max($window.width() - settings.w - loadedWidth - interfaceWidth - setSize(settings.right, 'x'), 0);
        } else if (settings.left !== false) {
            left += setSize(settings.left, 'x');
        } else {
            left += Math.round(Math.max($window.width() - settings.w - loadedWidth - interfaceWidth, 0) / 2);
        }

        if (settings.bottom !== false) {
            top += Math.max(document.documentElement.clientHeight - settings.h - loadedHeight - interfaceHeight - setSize(settings.bottom, 'y'), 0);
        } else if (settings.top !== false) {
            top += setSize(settings.top, 'y');
        } else {
            top += Math.round(Math.max(document.documentElement.clientHeight - settings.h - loadedHeight - interfaceHeight, 0) / 2);
        }

        $box.show();

        // setting the speed to 0 to reduce the delay between same-sized content.
        speed = ($box.width() === settings.w + loadedWidth && $box.height() === settings.h + loadedHeight) ? 0 : speed || 0;

        // this gives the wrapper plenty of breathing room so it's floated contents can move around smoothly,
        // but it has to be shrank down around the size of div#colorbox when it's done.  If not,
        // it can invoke an obscure IE bug when using iframes.
        $wrap[0].style.width = $wrap[0].style.height = "9999px";

        function modalDimensions(that) {
            // loading overlay height has to be explicitly set for IE6.
            $topBorder[0].style.width = $bottomBorder[0].style.width = $content[0].style.width = that.style.width;
            $loadingOverlay[0].style.height = $loadingOverlay[1].style.height = $content[0].style.height = $leftBorder[0].style.height = $rightBorder[0].style.height = that.style.height;
        }

        $box.dequeue().animate({width: settings.w + loadedWidth, height: settings.h + loadedHeight, top: top, left: left}, {
            duration: speed,
            complete: function () {
                modalDimensions(this);

                active = false;

                // shrink the wrapper down to exactly the size of colorbox to avoid a bug in IE's iframe implementation.
                $wrap[0].style.width = (10 + settings.w + loadedWidth + interfaceWidth) + "px";
                $wrap[0].style.height = (settings.h + loadedHeight + interfaceHeight) + "px";

                if (loadedCallback) {
                    loadedCallback();
                }

                setTimeout(function(){  // small delay before binding onresize due to an IE8 bug.
                    $window.bind('resize.' + prefix, publicMethod.position);
                }, 1);
            },
            step: function () {
                modalDimensions(this);
            }
        });
    };

    publicMethod.resize = function (options) {
        if (open) {
            options = options || {};

            if (options.width) {
                settings.w = setSize(options.width, 'x') - loadedWidth - interfaceWidth;
            }
            if (options.innerWidth) {
                settings.w = setSize(options.innerWidth, 'x');
            }
            $loaded.css({width: settings.w});

            if (options.height) {
                settings.h = setSize(options.height, 'y') - loadedHeight - interfaceHeight;
            }
            if (options.innerHeight) {
                settings.h = setSize(options.innerHeight, 'y');
            }
            if (!options.innerHeight && !options.height) {
                var $child = $loaded.wrapInner("<div style='overflow:auto'></div>").children(); // temporary wrapper to get an accurate estimate of just how high the total content should be.
                settings.h = $child.height();
                $child.replaceWith($child.children()); // ditch the temporary wrapper div used in height calculation
            }
            $loaded.css({height: settings.h});

            publicMethod.position(settings.transition === "none" ? 0 : settings.speed);
        }
    };

    publicMethod.prep = function (object) {
        if (!open) {
            return;
        }

        var callback, speed = settings.transition === "none" ? 0 : settings.speed;

        $loaded.remove();
        $loaded = $div('LoadedContent').append(object);

        function getWidth() {
            settings.w = settings.w || $loaded.width();
            settings.w = settings.mw && settings.mw < settings.w ? settings.mw : settings.w;
            return settings.w;
        }
        function getHeight() {
            settings.h = settings.h || $loaded.height();
            settings.h = settings.mh && settings.mh < settings.h ? settings.mh : settings.h;
            return settings.h;
        }

        $loaded.hide()
        .appendTo($loadingBay.show())// content has to be appended to the DOM for accurate size calculations.
        .css({width: getWidth(), overflow: settings.scrolling ? 'auto' : 'hidden'})
        .css({height: getHeight()})// sets the height independently from the width in case the new width influences the value of height.
        .prependTo($content);

        $loadingBay.hide();

        // floating the IMG removes the bottom line-height and fixed a problem where IE miscalculates the width of the parent element as 100% of the document width.
        //$(photo).css({'float': 'none', marginLeft: 'auto', marginRight: 'auto'});

        $(photo).css({'float': 'none'});

        // Hides SELECT elements in IE6 because they would otherwise sit on top of the overlay.
        if (isIE6) {
            $('select').not($box.find('select')).filter(function () {
                return this.style.visibility !== 'hidden';
            }).css({'visibility': 'hidden'}).one(event_cleanup, function () {
                this.style.visibility = 'inherit';
            });
        }

        callback = function () {
            var prev, prevSrc, next, nextSrc, total = $related.length, iframe, complete;

            if (!open) {
                return;
            }

            function removeFilter() {
                if (isIE) {
                    $box[0].style.removeAttribute('filter');
                }
            }

            complete = function () {
                clearTimeout(loadingTimer);
                $loadingOverlay.hide();
                trigger(event_complete, settings.onComplete);
            };

            if (isIE) {
                //This fadeIn helps the bicubic resampling to kick-in.
                if (photo) {
                    $loaded.fadeIn(100);
                }
            }

            $title.html(settings.title).add($loaded).show();

            if (total > 1) { // handle grouping
                if (typeof settings.current === "string") {
                    $current.html(settings.current.replace('{current}', index + 1).replace('{total}', total)).show();
                }

                $next[(settings.loop || index < total - 1) ? "show" : "hide"]().html(settings.next);
                $prev[(settings.loop || index) ? "show" : "hide"]().html(settings.previous);

                prev = index ? $related[index - 1] : $related[total - 1];
                next = index < total - 1 ? $related[index + 1] : $related[0];

                if (settings.slideshow) {
                    $slideshow.show();
                }

                // Preloads images within a rel group
                if (settings.preloading) {
                    nextSrc = $.data(next, colorbox).href || next.href;
                    prevSrc = $.data(prev, colorbox).href || prev.href;

                    nextSrc = $.isFunction(nextSrc) ? nextSrc.call(next) : nextSrc;
                    prevSrc = $.isFunction(prevSrc) ? prevSrc.call(prev) : prevSrc;

                    if (isImage(nextSrc)) {
                        $('<img/>')[0].src = nextSrc;
                    }

                    if (isImage(prevSrc)) {
                        $('<img/>')[0].src = prevSrc;
                    }
                }
            } else {
                $groupControls.hide();
            }

            if (settings.iframe) {
                iframe = $('<iframe/>').addClass(willet_prefix + 'Iframe')[0];

                if (settings.fastIframe) {
                    complete();
                } else {
                    $(iframe).one('load', complete);
                }
                iframe.name = willet_prefix + (+new Date());
                iframe.src = settings.href;

                if (!settings.scrolling) {
                    iframe.scrolling = "no";
                }

                if (isIE) {
                    iframe.frameBorder = 0;
                    iframe.allowTransparency = "true";
                }

                $(iframe).appendTo($loaded).one(event_purge, function () {
                    iframe.src = "//about:blank";
                });
            } else {
                complete();
            }

            if (settings.transition === 'fade') {
                $box.fadeTo(speed, 1, removeFilter);
            } else {
                removeFilter();
            }
        };

        if (settings.transition === 'fade') {
            $box.fadeTo(speed, 0, function () {
                publicMethod.position(0, callback);
            });
        } else {
            publicMethod.position(speed, callback);
        }
    };

    publicMethod.load = function (launched) {
        var href, setResize, prep = publicMethod.prep;

        active = true;

        photo = false;

        element = $related[index];

        if (!launched) {
            makeSettings();
        }

        trigger(event_purge);

        trigger(event_load, settings.onLoad);

        settings.h = settings.height ?
                setSize(settings.height, 'y') - loadedHeight - interfaceHeight :
                settings.innerHeight && setSize(settings.innerHeight, 'y');

        settings.w = settings.width ?
                setSize(settings.width, 'x') - loadedWidth - interfaceWidth :
                settings.innerWidth && setSize(settings.innerWidth, 'x');

        // Sets the minimum dimensions for use in image scaling
        settings.mw = settings.w;
        settings.mh = settings.h;

        // Re-evaluate the minimum width and height based on maxWidth and maxHeight values.
        // If the width or height exceed the maxWidth or maxHeight, use the maximum values instead.
        if (settings.maxWidth) {
            settings.mw = setSize(settings.maxWidth, 'x') - loadedWidth - interfaceWidth;
            settings.mw = settings.w && settings.w < settings.mw ? settings.w : settings.mw;
        }
        if (settings.maxHeight) {
            settings.mh = setSize(settings.maxHeight, 'y') - loadedHeight - interfaceHeight;
            settings.mh = settings.h && settings.h < settings.mh ? settings.h : settings.mh;
        }

        href = settings.href;

        loadingTimer = setTimeout(function () {
            $loadingOverlay.show();
        }, 100);

        if (settings.inline) {
            // Inserts an empty placeholder where inline content is being pulled from.
            // An event is bound to put inline content back when ColorBox closes or loads new content.
            $div().hide().insertBefore($(href)[0]).one(event_purge, function () {
                $(this).replaceWith($loaded.children());
            });
            prep($(href));
        } else if (settings.iframe) {
            // IFrame element won't be added to the DOM until it is ready to be displayed,
            // to avoid problems with DOM-ready JS that might be trying to run in that iframe.
            prep(" ");
        } else if (settings.html) {
            prep(settings.html);
        } else if (isImage(href)) {
            $(photo = new Image())
            .addClass(willet_prefix + 'Photo')
            .error(function () {
                settings.title = false;
                prep($div('Error').text('This image could not be loaded'));
            })
            .load(function () {
                var percent;
                photo.onload = null; //stops animated gifs from firing the onload repeatedly.

                if (settings.scalePhotos) {
                    setResize = function () {
                        photo.height -= photo.height * percent;
                        photo.width -= photo.width * percent;
                    };
                    if (settings.mw && photo.width > settings.mw) {
                        percent = (photo.width - settings.mw) / photo.width;
                        setResize();
                    }
                    if (settings.mh && photo.height > settings.mh) {
                        percent = (photo.height - settings.mh) / photo.height;
                        setResize();
                    }
                }

                if (settings.h) {
                    photo.style.marginTop = Math.max(settings.h - photo.height, 0) / 2 + 'px';
                }

                if ($related[1] && (index < $related.length - 1 || settings.loop)) {
                    photo.style.cursor = 'pointer';
                    photo.onclick = function () {
                        publicMethod.next();
                    };
                }

                if (isIE) {
                    photo.style.msInterpolationMode = 'bicubic';
                }

                setTimeout(function () { // A pause because Chrome will sometimes report a 0 by 0 size otherwise.
                    prep(photo);
                }, 1);
            });

            setTimeout(function () { // A pause because Opera 10.6+ will sometimes not run the onload function otherwise.
                photo.src = href;
            }, 1);
        } else if (href) {
            $loadingBay.load(href, settings.data, function (data, status, xhr) {
                prep(status === 'error' ? $div('Error').text('Request unsuccessful: ' + xhr.statusText) : $(this).contents());
            });
        }
    };

    // Navigates to the next page/image in a set.
    publicMethod.next = function () {
        if (!active && $related[1] && (index < $related.length - 1 || settings.loop)) {
            index = index < $related.length - 1 ? index + 1 : 0;
            publicMethod.load();
        }
    };

    publicMethod.prev = function () {
        if (!active && $related[1] && (index || settings.loop)) {
            index = index ? index - 1 : $related.length - 1;
            publicMethod.load();
        }
    };

    // Note: to use this within an iframe use the following format: parent.$.fn.colorbox.close();
    publicMethod.close = function () {
        if (open && !closing) {

            closing = true;

            open = false;

            trigger(event_cleanup, settings.onCleanup);

            $window.unbind('.' + prefix + ' .' + event_ie6);

            $overlay.fadeTo(200, 0);

            $box.stop().fadeTo(300, 0, function () {

                $box.add($overlay).css({'opacity': 1, cursor: 'auto'}).hide();

                trigger(event_purge);

                $loaded.remove();

                setTimeout(function () {
                    closing = false;
                    trigger(event_closed, settings.onClosed);
                }, 1);
            });
        }
    };

    // A method for fetching the current element ColorBox is referencing.
    // returns a jQuery object.
    publicMethod.element = function () {
        return $(element);
    };

    publicMethod.settings = defaults;

    // Bind the live event before DOM-ready for maximum performance in IE6 & 7.
    handler = function (e) {
        // checks to see if it was a non-left mouse-click and for clicks modified with ctrl, shift, or alt.
        if (!((e.button !== 0 && typeof e.button !== 'undefined') || e.ctrlKey || e.shiftKey || e.altKey)) {
            e.preventDefault();
            launch(this);
        }
    };

    if ($.fn.delegate) {
        $(document).delegate('.' + boxElement, 'click', handler);
    } else {
        $('.' + boxElement).live('click', handler);
    }

    // Initializes ColorBox when the DOM has loaded
    $(publicMethod.init);

    // Set up handler for calls from iframe
    $.receiveMessage(
                function(e){
                    publicMethod.closeState = e.data;
                },
                "{{URL}}"
            );


}(jQuery, document, this));

if (typeof jQuery.cookie != 'function') {
    /**
    * jQuery Cookie plugin
    *
    * Copyright (c) 2010 Klaus Hartl (stilbuero.de)
    * Dual licensed under the MIT and GPL licenses:
    * http://www.opensource.org/licenses/mit-license.php
    * http://www.gnu.org/licenses/gpl.html
    *
    */
    jQuery.cookie = function (key, value, options) {
        // key and at least value given, set cookie...
        if (arguments.length > 1 && String(value) !== "[object Object]") {
            options = jQuery.extend({}, options);

            if (value === null || value === undefined) {
                options.expires = -1;
            }

            if (typeof options.expires === 'number') {
                var days = options.expires, t = options.expires = new Date();
                t.setDate(t.getDate() + days);
            }

            value = String(value);

            return (document.cookie = [
                encodeURIComponent(key), '=',
                options.raw ? value : encodeURIComponent(value),
                options.expires ? '; expires=' + options.expires.toUTCString() : '', // use expires attribute, max-age is not supported by IE
                options.path ? '; path=' + options.path : '',
                options.domain ? '; domain=' + options.domain : '',
                options.secure ? '; secure' : ''
            ].join(''));
        }

        // key and possibly options given, get cookie...
        options = value || {};
        var result, decode = options.raw ? function (s) { return s; } : decodeURIComponent;
        return (result = new RegExp('(?:^|; )' + encodeURIComponent(key) + '=([^;]*)').exec(document.cookie)) ? decode(result[1]) : null;
    };
}
