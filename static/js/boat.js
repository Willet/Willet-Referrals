/**
 * Boat.js
 * Rocks the boat
 */
window.boat_finished = true;
window.boat = null; 
var move = function (next) {
    window.boat_finished = false;
    window.boat.animate({
        "left": next
    }, 300, function() {
        window.boat_finished = true;
    });
};
var moveLeft = function() {
    var current = window.boat.offset().left;
    if (current < 0 ) {
        move(0);
    } 
    var next = "-=100";
    move(next);
};
var moveRight = function() {
    var current = window.boat.offset().left;
    if (current > $(window).width()) {
        move($(window).width());
    }
    var next = "+=100";
    move(next);
};
$(document).ready(function() {
    // setup the boat
    window.boat = $('#sailboat');
    window.boat.animate({"right": "101px"}, 0);

    $(document).keydown(function (e) {
        /**
         * KEY CONTROLS FOR THE BOAT!
         */
        var keyCode = e.keyCode || e.which;
        arrow = {left: 37, up: 38, right: 39, down: 40 };

        switch (keyCode) {
            case arrow.left:
                moveLeft();
            break;
            case arrow.up:
                // func
            break;
            case arrow.right:
                moveRight();
            break;
            case arrow.down:
                // func
            break;
        }
    });
});
