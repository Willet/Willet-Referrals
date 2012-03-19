/*
    shaker jQuery Plugin MODDED
    (C)2010 ajaxBlender.com
    For any questions please visit www.ajaxblender.com 
    or email us at support@ajaxblender.com
    Some modifications by ronier@gmail.com
*/
;(function($){
    var element = {};
    var steps = 3;
    $.fn.shaker = function(){
        element = $(this);
        element.css('position', 'relative');
        element.run = true;
        element.find('*').each(function(i, el){
            $(el).css('position', 'relative');
        });
        var iFunc = function(){ $.fn.shaker.animate($(element)); };
        setTimeout(iFunc, 25);
    };
    $.fn.shaker.animate = function(el){
        if( element.run == true ) {
            $.fn.shaker.shake(el);
            el.find('*').each(function(i, el){
                $.fn.shaker.shake(el);
            });        
            var iFunc = function(){ $.fn.shaker.animate(el); };
            setTimeout(iFunc, 25);
        }
    }
    $.fn.shaker.stop = function(el) {
        element.run = false;
        element.css("top","0px");
        element.css("left","0px");
    }
	
    $.fn.shaker.shake = function(el){
        var pos = $(el).position();
        // if(Math.random() > 0.5){
            // $(el).css('top', pos['top'] + Math.random() < 0.5 ? (Math.random() * steps * (-1)) : Math.random() * steps);
        // } else {
            $(el).css('left', pos['left'] + Math.random() < 0.5 ? (Math.random() * steps * (-1)) : Math.random() * steps);
        // }
    }
})(jQuery);