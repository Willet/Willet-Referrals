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

            INT_TIME_ANIM = 350; // animation speed in milliseconds
            DEFAULTS = { // add defaults to params
                'width': '180',
                'height': '150', // must be 'int'
                'padding': '5px', // must be 'Npx'
                'border': '1px #bbb solid',
                'border-radius': '5px',
                'background-color': '#fff',
                'overflow': 'hidden',
                'display': 'inline-block',
                'cursor': 'pointer'
            };

            return this.each(function () { // return: chain
                var box_onclick,
                    close_dropdown,
                    dropdown_button,
                    dropdown_is_opened,
                    $expansion,
                    expansion_is_visible,
                    image_mousemove,
                    image_onclick,
                    $images,
                    open_dropdown,
                    settings,
                    $this, // different for each dropdown
                    toggle_dropdown;

                $this = $(this);
                $images = $this.find('img');
                console.log($images);
                settings = $.extend({}, DEFAULTS, params);
                dropdown_button = $('<div />', {
                    'text': "\u2335", // unicode countersink
                    'css': {
                        'float': 'right',
                        'margin-right': '4px',
                        'margin-top': settings.height / 2 - 15
                    }
                });
                dropdown_button.click(box_onclick);

                $images.css({
                    'border-radius': settings['border-radius'],
                    'display': 'block',
                    'width': settings.width - 20,
                    'height': settings.height,
                    'margin-top': '5'
                });
                $this.children('img').css('margin-top', '0');

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
                    $this
                        .css({
                            'border-bottom': '1px transparent solid',
                            'border-bottom-left-radius': '0',
                            'border-bottom-right-radius': '0',
                        });
                    $expansion
                        .css({
                            'border-top': '0',
                            'border-top-left-radius': '0',
                            'border-top-right-radius': '0',
                            'z-index': '999999',
                            'top': $this.position().top, // + $this.outerHeight(),
                            'left': $this.position().left
                        })
                        .slideDown(INT_TIME_ANIM);
                    return true;
                };

                close_dropdown = function () {
                    $expansion.fadeOut(INT_TIME_ANIM);
                    $expansion
                        .css({
                            'border': settings.border,
                            'border-radius': settings['border-radius']
                        });
                    $this
                        .css({
                            'border': settings.border,
                            'border-radius': settings['border-radius']
                        });
                    console.log('closed');
                    return false;
                };

                expansion_is_visible = function () {
                    return !!$expansion.is(':visible');
                };

                toggle_dropdown = function () {
                    if (expansion_is_visible() === true) {
                        return close_dropdown();
                    } else {
                        return open_dropdown();
                    }
                }

                box_onclick = function (event) {
                    event.stopPropagation(); // stop bubbling up, bro
                    toggle_dropdown();
                };

                image_onclick = function (event) {
                    var $selected_image;
                    console.log(event);

                    // remove existing "selected image"
                    $this.children('img').remove();

                    // put on a new "selected image"
                    $selected_image = $(this).clone(true, true);
                    $selected_image.click(open_dropdown);
                    $this.append($selected_image);

                    return close_dropdown();
                };

                image_mousemove = function (event) {

                };

                // add images to the dropdown
                $images
                    .click(image_onclick)
                    .hover(image_mousemove);

                // set up the dropdown container
                $this
                    .click(box_onclick)
                    .append(dropdown_button)
                    .css(settings)
                    .blur(close_dropdown);
                $expansion
                    .css(settings)
                    .css({
                        'height': 'auto',
                        'max-height': '350px',
                        'overflow-y': 'scroll',
                        'display': 'none'
                    })
                    .append($images)
                    .insertAfter($this)
                    .blur(close_dropdown);
                $expansion.find('img').eq(0).click();
            });
        };
    }
})($ || jQuery);