/*
 * jQuery LightSwitch plugin
 * @author admin@catchmyfame.com - http://www.catchmyfame.com
 * @author nick@nt3r.com - http://www.nt3r.com
 * @category jQuery plugin
 * @copyright (c) 2010 admin@catchmyfame.com (www.catchmyfame.com)
 * @license CC Attribution-Share Alike 3.0 - http://creativecommons.org/licenses/by-sa/3.0/
 */
(function($){
    $.fn.extend({
        lightSwitch: function(options) {
            var defaults = {
                "hover": {
                    "speed": 100,
                    "on":  {"x": "-31px", "y": "0px"},
                    "off": {"x": "-6px",  "y": "0px"}
                },
                "click": {
                    "speed": 120,
                    "on":  {"x": "0px",   "y": "0px"},
                    "off": {"x": "-37px", "y": "0px"}
                },
                "dir": "",
                "switch": "switch.png",
                "cover": "switchplate.png",
                "disabled": "disabled.png",
                "height": "18px",
                "width": "63px",
                "change": function(){}
            };

            options = $.extend(defaults, options);

            var createLightSwitch = function(disabled) {
                var o = options,
                    base = $("<span/>"),
                    baseImg = $("<img />", {
                        "src": "" + o.dir + o.disabled
                    });

                if (!disabled) {
                    base.addClass("switch");

                    baseImg.attr("width", o.width);
                    baseImg.attr("height", o.height);
                    baseImg.attr("src", "" + o.dir + o.cover);
                }

                base.append(baseImg);
                base.css({
                    'display':'inline-block',
                    'background-image':'url("' + o.dir + o["switch"] + '")',
                    'background-repeat':'no-repeat',
                    'overflow':'hidden',
                    'cursor':'pointer',
                    'margin-right':'2px'
                });

                return base;
            };

            return this.each(function() {
                var o=options,
                    lightSwitch,
                    input = $(this);

                // Create lightswitch
                lightSwitch = createLightSwitch(input.attr('disabled'), o);

                // Replace input with lightswitch
                input.hide().after(lightSwitch);

                // Setup switch handlers
                lightSwitch.click(function() {
                    var c = o.click,
                        radioGroupName;

                    // When we click any span image for a radio button, animate the previously selected radio button to 'off'.
                    if(input.is(':radio')) {
                        radioGroupName = $(this).prev().attr('name');
                        $('input[name="'+radioGroupName+'"]'+':checked + span').stop().animate({
                            'background-position-x': c.off.x,
                            'background-position-y': c.off.y
                        }, c.speed);
                    }

                    if(input.is(':checked')) {
                        $(this).stop().animate({
                            'background-position-x': c.off.x,
                            'background-position-y': c.off.y
                        }, c.speed); // off
                        input.removeAttr('checked');
                    } else {
                        $(this).stop().animate({
                            'background-position-x': c.on.x,
                            'background-position-y': c.on.y
                        }, c.speed); // on

                        if(input.is(':radio')){
                            $('input[name="'+radioGroupName+'"]'+':checked').removeAttr('checked');
                        }
                        input.attr('checked','checked');
                    }

                    //because change is not triggered unless user clicks a checkbox
                    input.change();

                }).hover(
                    function() {
                        var h = o.hover;
                        $(this).stop().animate({
                            'background-position-x': input.is(':checked') ? h.off.x : h.on.x,
                            'background-position-y': input.is(':checked') ? h.off.y : h.on.y
                        }, h.speed);
                    },
                    function(){
                        var c = o.click;
                        $(this).stop().animate({
                            'background-position-x': input.is(':checked') ? c.on.x : c.off.x,
                            'background-position-y': input.is(':checked') ? c.on.y : c.off.y
                        }, c.speed);
                    }
                );

                lightSwitch.css({
                    'background-position-x': $(this).is(':checked') ? o.click.on.x : o.click.off.x,
                    'background-position-y': $(this).is(':checked') ? o.click.on.y : o.click.off.y
                }); // setup default states

                // set the css in case the animation didn't work
                // e.g. Firefox and Opera
                if ($.browser.mozilla || $.browser.opera) {
                    var state = $(this).is(':checked') ? o.click.on : o.click.off;
                    lightSwitch.css({
                        "background-position": state.x+" "+state.y
                    })
                }

                $('input + span').live("click", function() { return false; });

                input.change(function(event){
                    var c = o.click,
                        radioGroupName = $(this).attr('name');

                    if($(this).is(':radio')) {
                        $(this).animate({
                            'background-position-x': c.on.x,
                            'background-position-y': c.on.y
                        }, c.speed);

                        $('input[name="'+radioGroupName+'"]'+' + span').stop().animate({
                            'background-position-x': c.off.x,
                            'background-position-y': c.off.x
                        }, c.speed);
                    }

                    lightSwitch.animate({
                        'background-position-x': $(this).is(':checked') ? c.on.x : c.off.x,
                        'background-position-y': $(this).is(':checked') ? c.on.y : c.off.y
                    }, c.speed);

                    // set the css in case the animation didn't work
                    // e.g. Firefox and Opera
                    if ($.browser.mozilla || $.browser.opera) {
                        var state = $(this).is(':checked') ? c.on : c.off;
                        lightSwitch.css({
                            "background-position": state.x+" "+state.y
                        })
                    }

                    o.change(event);
                });
            });
        }
    });
})(jQuery);