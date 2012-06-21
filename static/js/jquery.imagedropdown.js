(function ($) {
    // jQuery image dropdown box (CC) Brian Lai
    // Got problems? Don't come to me.
    "use strict";
    if ($ && $.fn) {
        $.fn.imageDropdown = function (params) {
            // there's no need to do $(this) because
            // "this" is already a jquery object
            var DEFAULTS,
                INT_TIME_ANIM = 350; // animation speed in milliseconds

            DEFAULTS = { // add defaults to params
                'width': '180px',
                'height': '150px',
                'padding': '5px', // must be 'Npx'
                'border': '1px #bbb solid',
                'border-radius': '5px',
                'background-color': '#fff',
                'overflow': 'hidden',
                // 'display': 'inline-block',
                'cursor': 'pointer',
                'click': function () {},  // custom event
                'select': function (selection) {},  // custom event
                'hover': function () {},  // custom event
            };

            return this.each(function () { // return: chain
                var box_onclick,
                    closeDropdown,
                    dropdown_button,
                    dropdown_is_opened,
                    $expansion,
                    expansionIsVisible,
                    image_onclick,
                    $images,
                    openDropdown,
                    settings,
                    $this, // different for each dropdown
                    toggleDropdown;

                $this = $(this);
                $images = $this.find('img');
                settings = $.extend({}, DEFAULTS, params);
                dropdown_button = $('<div />', {
                    // 'text': "\u2335", // unicode countersink doesn't work in IE
                    'css': {
                        'background-image': "url('/static/imgs/dropdown_icon.png')",
                        'display': 'inline-block',
                        'width': '25px',
                        'height': '26px',
                        'float': 'right',
                        'margin-top': parseInt(settings.height) / 2 - 15
                    }
                });
                dropdown_button.click(box_onclick);

                $images.css({
                    'border-radius': settings['border-radius'],
                    'display': 'block',
                    'width': parseInt(settings.width) - 30,
                    'height': parseInt(settings.height),
                    'margin-top': '5'
                }).hover(
                    function () {
                        $(this).css({
                            // http://stackoverflow.com/questions/5162993/jquery-how-to-bright-up-an-image
                            'opacity': '0.5'
                        });
                    }, function () {
                        $(this).css({
                            'opacity': '1'
                        });
                    }
                );
                $this.children('img').css('margin-top', '0');

                $expansion = $('<div />', {
                    'class': 'expansion',
                    'css': {
                        'display': 'none',
                        'width': parseInt(settings.width) - 20,
                        'height': $images.length * parseInt(settings.height),
                        'border-radius': settings['border-radius'],
                        'position': 'absolute',
                        'tabindex': '1'
                    }
                });

                openDropdown = function () {
                    $expansion.css({
                        'z-index': '999999',
                        'top': $this.position().top,
                        'left': $this.position().left
                    })
                    .fadeIn(INT_TIME_ANIM);
                    return true;
                };

                closeDropdown = function () {
                    $expansion.fadeOut(INT_TIME_ANIM);
                    return false;
                };
                $expansion.blur(closeDropdown);

                expansionIsVisible = function () {
                    return $expansion.is(':visible');
                };

                toggleDropdown = function () {
                    if (expansionIsVisible() === true) {
                        return closeDropdown();
                    } else {
                        return openDropdown();
                    }
                }

                box_onclick = function (event) {
                    event.stopPropagation(); // stop bubbling up, bro
                    toggleDropdown();
                    settings.click();  // call custom event
                };

                image_onclick = function (event) {
                    var $selected_image;

                    // remove existing "selected image"
                    $this.children('img').remove();

                    // put on a new "selected image"
                    $selected_image = $(this).clone(true, true);
                    $selected_image.click(openDropdown);
                    $this.append($selected_image);

                    settings.select($selected_image.attr('src'));  // call custom event
                    return closeDropdown();
                };

                // add images to the dropdown
                $images.click(image_onclick);

                // set up the dropdown container
                $this.click(box_onclick)
                     .append(dropdown_button)
                     .css(settings)
                     .blur(closeDropdown);
                if ($.browser.msie) {
                    $this.css({
                        '*display': 'inline',
                        'zoom': '1'
                    });
                }
                $expansion.css(settings)
                          .css({
                              'height': 'auto',
                              'max-height': '333px',
                              'overflow-y': 'auto',
                              'display': 'none'
                          })
                          .append($images)
                          .insertAfter($this)
                          .blur(closeDropdown);
                $expansion.find('img').eq(0).click();
            });
        };
    }
})($ || jQuery);