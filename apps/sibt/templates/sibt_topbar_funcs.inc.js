// topbar SIBT code - included by sibt.js

var topbar_onclick = function(e) {
    // Onclick event handler for the 'sibt' button
    button_onclick(e, 'SIBTUserClickedTopBarAsk');
};

var unhide_topbar = function() {
    // When a user hides the top bar, it shows the little
    // "Show" button in the top right. This handles the clicks to that
    $.cookie('_willet_topbar_closed', false);
    topbar_hide_button.slideUp('fast');
    if (topbar === null) {
        if (instance.show_votes || hash_index !== -1) {
            show_topbar();
            store_analytics('SIBTUserReOpenedTopBar');
        } else {
            show_topbar_ask();
            store_analytics('SIBTShowingTopBarAsk');
        }
    } else {
        topbar.slideDown('fast');
        store_analytics('SIBTUserReOpenedTopBar');
    }
};

var close_top_bar = function() {
    // Hides the top bar and padding
    $.cookie('_willet_topbar_closed', true);
    topbar.slideUp('fast');
    topbar_hide_button.slideDown('fast');
    store_analytics('SIBTUserClosedTopBar');
};

// Expand the top bar and load the results iframe
var do_vote = function(vote) {
    // detecting if we just voted or not
    var doing_vote = (vote !== -1);
    var vote_result = (vote === 1);

    // getting the neccesary dom elements
    var iframe_div = topbar.find('div.iframe');
    var iframe = topbar.find('div.iframe iframe');

    // constructing the iframe src
    var hash        = w.location.hash;
    var hash_search = '#code=';
    var hash_index  = hash.indexOf(hash_search);
    var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
    var results_src = "{{URL}}/s/results.html?" +
        "willt_code=" + encodeURIComponent(willt_code) +
        "&user_uuid={{user.uuid}}" +
        "&doing_vote=" + encodeURIComponent(doing_vote) +
        "&vote_result=" + encodeURIComponent(vote_result) +
        "&is_asker=" + user.is_asker +
        "&store_id={{store_id}}" +
        "&store_url={{store_url}}" +
        "&instance_uuid={{instance.uuid}}" +
        "&url=" + encodeURIComponent(w.location.href);

    // show/hide stuff
    topbar.find('div.vote').hide();
    if (doing_vote || user.has_voted) {
        topbar.find('div.message').html('Thanks for voting!').fadeIn();
    } else if (user.is_asker) {
        topbar.find('div.message').html('Your friends say:   ').fadeIn();
    }

    // start loading the iframe
    iframe_div.show();
    iframe.attr('src', '');
    iframe.attr('src', results_src);

    iframe.fadeIn('medium');
};
var do_vote_yes = function() { do_vote(1);};
var do_vote_no = function() { do_vote(0);};

var build_top_bar_html = function (is_ask_bar) {
    // Builds the top bar html
    // is_ask_bar option boolean
    // if true, loads ask_in_the_bar iframe

    if (is_ask_bar || false) {
        var AB_CTA_text = AB_CTA_text || 'Ask your friends for advice!'; // AB lag
        var bar_html = "<div class='_willet_wrapper'><p style='font-size: 15px'>Decisions are hard to make. " + AB_CTA_text + "</p>" +
            "<div id='_willet_close_button' style='position: absolute;right: 13px;top: 1px; cursor: pointer;'>" +
            "   <img src='{{URL}}/static/imgs/fancy_close.png' width='30' height='30' />" +
            "</div>" +
        "</div>";
    } else {
        var asker_text = '';
        var message = 'Should <em>{{ asker_name }}</em> Buy This?';
        var image_src = '{{ asker_pic }}';

        var bar_html = "<div class='_willet_wrapper'> " +
            "<div class='asker'>" +
                "<div class='pic'><img src='" + image_src + "' /></div>" +
            "</div>" +
            "<div class='message'>" + message + "</div>" +
            "<div class='vote last' style='display: none'>" +
            "    <button id='yesBtn' class='yes'>Yes</button> "+
            "    <button id='noBtn' class='no'>No</button> "+
            "</div> "+
            "<div class='iframe last' style='display: none; margin-top: 1px;' width='600px'> "+
            "    <iframe id='_willet_results' height='40px' frameBorder='0' width='600px' style='background-color: #3b5998'></iframe>"+
            "</div>" +
            "<div id='_willet_close_button' style='position: absolute;right: 13px;top: 13px;cursor: pointer;'>" +
            "   <img src='{{URL}}/static/imgs/fancy_close.png' width='30' height='30' />" +
            "</div>" +
        "</div>";
    }
    return bar_html;
};

var show_topbar = function() {
    // Shows the vote top bar
    var body = $('body');

    // create the padding for the top bar
    padding_elem = d.createElement('div');
    padding_elem = $(padding_elem)
        .attr('id', '_willet_padding')
        .css('display', 'none');

    topbar = d.createElement('div');
    topbar = $(topbar)
        .attr('id', '_willet_sibt_bar')
        .css('display', "none")
        .html(build_top_bar_html());
    body.prepend(padding_elem);
    body.prepend(topbar);

    // bind event handlers
    $('#_willet_close_button').unbind().bind('click', close_top_bar);
    $('#yesBtn').click(do_vote_yes);
    $('#noBtn').click(do_vote_no);

    padding_elem.show();
    topbar.slideDown('slow');

    if (!instance.is_live) {
        // voting is over folks!
        topbar.find('div.message').html('Voting is over!');
        toggle_results();
    } else if (instance.show_votes && !user.has_voted && !user.is_asker) {
        // show voting!
        topbar.find('div.vote').show();
    } else if (user.has_voted && !user.is_asker) {
        // someone has voted && not the asker!
        topbar.find('div.message').html('Thanks for voting!').fadeIn();
        toggle_results();
    } else if (user.is_asker) {
        // showing top bar to asker!
        topbar.find('div.message').html('Your friends say:   ').fadeIn();
        toggle_results();
    }
};

var show_topbar_ask = function() {
    //Shows the ask top bar

    // create the padding for the top bar
    padding_elem = d.createElement('div');

    padding_elem = $(padding_elem)
        .attr('id', '_willet_padding')
        .css('display', 'none');

    topbar = $('<div />', {
        'id': '_willet_sibt_ask_bar',
        'class': 'willet_reset',
        'css': {
            'display', 'none'
        }
    });
    topbar.html(build_top_bar_html(true));

    $("body").prepend(padding_elem).prepend(topbar);

    var iframe = topbar.find('div.iframe iframe');
    var iframe_div = topbar.find('div.iframe');

    $('#_willet_close_button').unbind().bind('click', close_top_bar);

    topbar.find( '._willet_wrapper p')
        .css('cursor', 'pointer')
        .click(topbar_onclick);
    padding_elem.show();
    topbar.slideDown('slow');
};

var topbar_ask_success = function () {
    // if we get a postMessage from the iframe
    // that the share was successful
    store_analytics('SIBTTopBarShareSuccess');
    var iframe = topbar.find('div.iframe iframe');
    var iframe_div = topbar.find('div.iframe');

    user.is_asker = true;

    iframe_div.fadeOut('fast', function() {
        topbar.animate({height: '40'}, 500);
        iframe.attr('src', '');
        toggle_results();
    });
};

var toggle_results = function() {
    // Used to toggle the results view
    // iframe has no source, hasnt been loaded yet
    // and we are FOR SURE showing it
    do_vote(-1);
};
