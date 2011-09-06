/**
 * dashboard.js
 *
 * controls the campaign dashboard
 * @author Matt Harris <matt@getwillet.com>
 */

// setup some globals
window.dbar = null;
window.dbar_top = null;
window.hover_el = null;
window.ub = null;
window.users = [];
var goProfile = function(user_id) {
    // redirects to a user profile
    window.location = '/profile/'+user_id+'/';
}
var showUserToast = function(obj) {
    /**
        * Controls showing the user toast
        *
        * obj format
        *  user_id     users id
        *  from_json   if data is from json
        *  had_error   if json request had error
        */ 
    var user_id = (obj.user_id == undefined ? -1 : obj.user_id);
    var from_json = (obj.from_json == undefined ? false : obj.from_json);
    var had_error = (obj.had_error == undefined ? false : obj.had_error);
    var toast_div = $('#user_box');
    var loading = '<img src="/static/imgs/loading.gif" />';
    if (!from_json) {
        // we are not coming from json
        // show the loading box
        var eleft = window.hover_el.offset().left;
        var etop = window.hover_el.offset().top;
        //eleft -= window.hover_el.width();
        //etop += window.hover_el.height() + 5;
        etop -= 5;
        eleft = 150;
        //console.log('moving toast to', eleft, etop);
        toast_div.hide()
            .css({position: 'absolute', top: etop, left: eleft})
            .html(loading) 
            .fadeIn('fast')
            .css({position: 'absolute', top: etop, left: eleft});
    }
    if (had_error) {
        // we had an error, display that
        toast_div.html('There was an error loading the user.');
    } else if (user_id != -1) {
        user = users[user_id];
        html = '<div align="right" style="float:right;"><img class="pic" src="'+ user.pic +'" />';
        html += '<br /><span class="services">Accounts:&nbsp;'; 
        if (user.has_twitter)
            html += '<img src="/static/imgs/db_twitter_small.png" />&nbsp;';
        if (user.has_facebook)
            html += '<img src="/static/imgs/fb-logo-small.png" />&nbsp;';
        if (user.has_linkedin)
            html += '<img src="/static/imgs/linkedin-logo-small.png" />&nbsp;';
        if (user.has_email)
            html += '<img src="/static/imgs/email_logo_small.png" />&nbsp;';
        
        html += '</span></div><div align="left">';
        html += '<h3>'+user.name+'</h3>';
        html += '<strong><em>'+user.handle+'</em></strong><br />';
        html += '<strong>Created: </strong>' + user.created + '<br />';
        html += '<strong>KScore: </strong>' + user.kscore + '<br />';
        html += '<strong>Reach: </strong>' + user.reach + '</div>';
        html += '<a href="/profile/'+campaign_id+'/'+user_id+'/" class="button">Profile</button>';
        
        toast_div.html(html);
    } else {
        // we are probably waiting on the data from json
    }
    return;
};

$(document).ready(function() {
    /**
     * jQuery onready
     */
    window.dbar = $('#results_header');
    window.ub = $('#user_box');
    if (window.dbar.offset() != null) {
        window.dbar_top = window.dbar.offset().top;
    }

    // Show/hide results
    /*$('#results div.row').click(function() {
        $(this)
            .toggleClass('expanded')
            .toggleClass('expandable')
            .next('div.details_toggle')
                .animate({
                    height: 'toggle'
                    }, 100, function() {
                        var row = $(this);
                        if (row.height() < 1) {
                            row.css('display', 'inline-block');
                        }
                });
    });*/

    // Show/Hide Defaults
    $('#results div.row_details').click(function() {
        $(this)
            .toggleClass('expanded')
            .toggleClass('expandable')
            .children('div.referrers_toggle')
            .animate({height: 'toggle'}, 200);
    });
    
    // prevent default on links
    $('#results span a').click(function(e) {
        /**
            * just prevent the div to close 
            */
        e.preventDefault();
        e.stopPropagation();
        //$.colorbox({inline:true, href:'#user_box'});
        //console.log($(this));     
    });

    // All the junk for the hovercards (users toasts)
    $('#results a.user').hover(function() {
        try {
            clearTimeout(window.ub.data('timeoutID'));
            window.hover_el = $(this);
            var user_id = window.hover_el.attr('id');
            if (window.users[user_id] == undefined) {
                // the users data has not been cached yet
                showUserToast({'from_json': false});
                $.getJSON(
                    '/campaign/get_user/' + user_id + '/',
                    function(data) {
                        // callback for when we get the user details
                        if (data.success) {
                            // request was good
                            window.users[data.user.uuid] = data.user;
                            console.log('got data for user, showing box', data);
                            showUserToast({'user_id': data.user.uuid, 'from_json': true});
                        } else {
                            // error!
                            console.log('error getting data for user, got response', data);
                            showUserToast({'from_json': true, 'had_error': true});
                        }
                    }
                );
            } else {
                // we already have the users data
                showUserToast({'user_id': user_id});
            }
        } catch (e) {
            console.log(e);
        }
    }, function () {
        // hover off
        var timeoutId = setTimeout(function(){ window.ub.fadeOut("fast");}, 100);
        window.ub.data('timeoutID', timeoutId); 
    });
    window.ub.hover(
        function() {console.log('hovering on ub'); clearTimeout(window.ub.data('timeoutID')); },
        function() {
            var timeoutID = setTimeout(function(){ window.ub.fadeOut("fast");}, 100);
            window.ub.data('timeoutID', timeoutID);
    });
    $(document).scroll(function() {
        /**
            * CONTROLS CARRYING THE HEADER WITH THE PAGE WHEN USER
            * SCROLLS
            */
        // scrolling
        var scroll_top = $(document).scrollTop();
        if (window.dbar.offset() != null) {
            var current_top = window.dbar.offset().top;
        } else {
            return;
        }
        if (current_top < window.dbar_top) {
            // move bar back to default position
            window.dbar.css('position', 'initial').css('top', window.dbar_top).removeClass('scrolling');
        } else if (current_top < scroll_top || (current_top > window.dbar_top && current_top > scroll_top)) {
            // let's get retarded!
            //window.dbar.css('position', 'absolute').css('top', scroll_top).css('left', '30%');
            window.dbar.animate({top: 0}, 10, function() {
                window.dbar.addClass('scrolling');
            });
        }
    });
});
