(function ($) {
    // jQuery image dropdown box (CC) Brian Lai
    // Got problems? Don't come to me.
    "use strict";
    if ($ && $.fn) {
        $.fn.imageDropdown = function (params) {
            // there's no need to do $(this) because
            // "this" is already a jquery object
            var DEFAULTS,
                INT_TIME_ANIM;

            INT_TIME_ANIM = 400; // animation speed in milliseconds
            DEFAULTS = { // add defaults to params
                'width': '120',
                'height': '100',
                'padding': '0',
                'border': '1px #ddd solid',
                'border-radius': '5px',
                'background-color': '#fff',
                'overflow': 'hidden'
            };

            return this.each(function () { // return: chain
                var box_onclick,
                    close_dropdown,
                    $expansion,
                    expansion_is_visible,
                    image_onclick,
                    $images,
                    open_dropdown,
                    settings,
                    $this; // different for each dropdown

                $this = $(this);
                $images = $this.find('img');
                settings = $.extend({}, DEFAULTS, params);

                $images.css({
                    'display': 'block',
                    'width': settings.width - 20,
                    'height': settings.height
                });

                $expansion = $('<div />', {
                    'class': 'expansion',
                    'css': {
                        'display': 'none',
                        'width': settings.width - 20,
                        'height': $images.length * settings.height,
                        'border-radius': settings['border-radius'],
                        'position': 'absolute'
                    }
                });

                open_dropdown = function () {
                    $expansion.slideDown(INT_TIME_ANIM);
                    return true;
                };

                close_dropdown = function () {
                    $expansion.fadeOut(INT_TIME_ANIM);
                    return false;
                };

                expansion_is_visible = function () {
                    return !!$expansion.is(':visible');
                };

                box_onclick = function (event) {
                    event.stopPropagation(); // stop bubbling up, bro
                    if (expansion_is_visible === true) {
                        return close_dropdown();
                    } else {
                        return open_dropdown();
                    }
                };

                image_onclick = function (event) {
                    var $selected_image;

                    // remove existing "selected image"
                    $this.children('img').remove();

                    // put on a new "selected image"
                    $selected_image = $(this).clone(true, true);
                    $selected_image.on('click', open_dropdown);
                    $this.append($selected_image);

                    return close_dropdown();
                };

                // add images to the dropdown
                $images.on('click', image_onclick);
                $expansion.append($images);

                // set up the dropdown container
                $this
                    .append($expansion)
                    .css(settings)
                    .on('click', box_onclick);
            });
        };
    }
})($ || jQuery);
