/**
 * Boat.js
 * Rocks the boat
 */
(function(window, document, $){
    var boat = null 
    , active = null
    , increment = 5
    , window_width = 0
    , borderRumble = null
    , moveLeft = function() {
        if (boat.offset().left <= 0) {
            clearTimeout(borderRumble);
            boat.trigger('startRubmle');
            borderRumble = setTimeout(function(){boat.trigger('stopRumble');}, 1500);
            boat.css('left', 0);
        } else {
            var left = boat.offset().left - increment;
            boat.css('left', left + 'px');
            if (active === moveLeft) {
                setTimeout(moveLeft, 10);
            }
        }
    }
    , moveRight = function() {
        var right = boat.offset().left + boat.width();
        if (right >= window_width) {
            clearTimeout(borderRumble);
            boat.trigger('startRubmle');
            borderRumble = setTimeout(function(){boat.trigger('stopRumble');}, 1500);
            boat.css('left', (window_width - boat.width()) + 'px');
        } else {
            var left = boat.offset().left + increment;
            boat.css('left', left + 'px');
            if (active === moveRight) {
                setTimeout(moveRight, 10);
            }
        }
    };
    $(document).ready(function() {
        // setup the boat
        window_width = $(window).width();
        boat = $('#sailboat')
            .css('width', '109px')
            .animate({right: "101px"}, 0)
            .jrumble({
                rumbleEvent: 'click',
                rangeX: 5,
                rangeY: 5,
                rangeRot: 15
            }
        );

        var arrow = {left: 37, up: 38, right: 39, down: 40 };
        $(document).keydown(function (e) {
            var keyCode = e.keyCode || e.which;
            if (keyCode == arrow.left && active !== moveLeft) {
                active = moveLeft;
                moveLeft();
            } else if (keyCode == arrow.right && active !== moveRight) {
                active = moveRight;
                moveRight();
            }
        }).keyup(function (e) {
            var keyCode = e.keyCode || e.which;
            if (keyCode == arrow.left || keyCode == arrow.right)
                active = null;
        });
    });
})(window, document, jQuery);

