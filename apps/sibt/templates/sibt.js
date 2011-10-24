/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

(function(document, window){
    var _willet_css = {% include stylesheet %}
    var _willet_ask_success = false;
    var _willet_is_asker = ('{{ is_asker }}' == 'True'); // did they ask?
    var _willet_show_votes = ('{{ show_votes }}' == 'True');
    var _willet_has_voted = ('{{ has_voted }}' == 'True');
    var is_live = ('{{ is_live }}' == 'True');
    var show_top_bar_ask = ('{{ show_top_bar_ask }}' == 'True');
    var _willet_topbar = null;

    /**
    * quick helper function to add scripts to dom
    */
    var _willet_load_remote_script = function(script) {
        var dom_el = document.createElement('script'); 
        dom_el.src = script;
        dom_el.type = 'text/javascript'; 
        document.getElementsByTagName('head')[0].appendChild(dom_el); 
        return dom_el;
    };

    var _willet_vote_callback = function () {
        /**
        * Called when the vote iframe is closed
        */
        var button = $('#_willet_button');
        var original_shadow = button.css('box-shadow');
        var glow_timeout = 400;

        var resetGlow = function() {
            button.css('box-shadow', original_shadow);
        };
        if (_willet_show_votes && !_willet_is_asker) {
            // closing box but not the asker!
            var button = $('#_willet_button');
            button.css('box-shadow', '0px 0px 15px red');
            setTimeout(resetGlow, glow_timeout)
        }
        return;
    };

    var _willet_store_analytics = function (message) {
        var message = message || '{{ evnt }}';
        var iframe = document.createElement( 'iframe' );

        iframe.style.display = 'none';
        iframe.src = "{{URL}}/s/storeAnalytics?evnt=" + message + 
                    "&target_url=" + window.location.href +
                    "&app_uuid={{app.uuid}}" +
                    "&user_uuid={{user.uuid}}";

        document.body.appendChild( iframe );
    };

    /**
    * Called when ask iframe is closed
    */
    var _willet_ask_callback = function() {
        if (_willet_ask_success) {
            _willet_is_asker = true;
            $('#_willet_button').html('Refresh the page to see your results!');
        }
    };

    /**
    * Onclick event handler for the 'sibt' button
    */
    var _willet_button_onclick = function() {
        if (_willet_is_asker || _willet_show_votes) {
            //_willet_show_vote();
            window.location.reload(true);
        } else {
            _willet_show_ask();        
        }
    };

    /**
    * shows the ask your friends iframe
    */
    var _willet_show_ask = function () {
        var url =  "{{URL}}/s/ask.html?store_url={{ store_url }}&url=" + window.location.href;

        $.colorbox({
            transition: 'fade',
            scrolling: false,
            iframe: true, 
            initialWidth: 0, 
            initialHeight: 0, 
            innerWidth: '450px',
            innerHeight: '240px', 
            fixed: true,
            href: url,
            onClosed: _willet_ask_callback
        });
    };

    /**
    * Shows the voting screen
    */
    var _willet_show_vote = function() {
        var photo_src = $('#image img').attr('src'); 
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);
        var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
            
        var url = "{{URL}}/s/vote.html?willt_code=" + willt_code + 
                "&is_asker={{is_asker}}&store_id={{store_id}}" + 
                "&photo=" + photo_src + 
                "&instance_uuid={{instance.uuid}}" +
                "&url=" + window.location.href;  

        $.colorbox({
            transition: 'fade',
            scrolling: true, 
            iframe: true,
            fixed: true,
            initialWidth: 0, 
            initialHeight: 0,
            innerWidth: '660px',
            innerHeight: '90%',
            href: url,
            onClosed: _willet_vote_callback
        });
    };
    
    /**
     * called when the results iframe is refreshed
     */
    var _willet_iframe_loaded = function() {
        //$('#_willet_sibt_bar div.loading').hide();
        _willet_topbar.children('div.iframe').children('div.loading').hide();
        //$('#_willet_sibt_bar').children('div.iframe').children('div.loading').hide();
        //$('#_willet_sibt_bar').children('div.iframe').children('div.loading').hide();
        $(this).css('width', $(this).parent().css('width'));
        $(this).fadeIn('fast');
    };
    
    /**
    * Used to toggle the results view
    */
    var _willet_toggle_results = function() {
        // check if results iframe is showing
        var iframe = _willet_topbar.find('div.iframe iframe'); 
        var iframe_div = _willet_topbar.find('div.iframe'); 
        var iframe_display = iframe_div.css('display');

        if (iframe.attr('src') == undefined || iframe.attr('src') == '') {
            // iframe has no source, hasnt been loaded yet
            // and we are FOR SURE showing it
            _willet_do_vote(-1);
            $('#_willet_toggle_results span.down').hide();
            $('#_willet_toggle_results span.up').show();
        } else {
            // iframe has been loaded before
            if (iframe_display == 'none') {
                // show the iframe
                _willet_topbar.animate({height: '337px'}, 500);
                $('#_willet_toggle_results span.down').hide();
                $('#_willet_toggle_results span.up').show();
                iframe_div.fadeIn('fast');
            } else {
                // hide iframe
                $('#_willet_toggle_results span.up').hide();
                $('#_willet_toggle_results span.down').show();
                iframe_div.fadeOut('fast');
                _willet_topbar.animate({height: '40'}, 500);
            }
        }
    };

    /**
    * Expand the top bar and load the results iframe
    */
    var _willet_do_vote_yes = function() { _willet_do_vote(1);};
    var _willet_do_vote_no = function() { _willet_do_vote(0);};
    var _willet_do_vote = function(vote) {
        // detecting if we just voted or not
        var doing_vote = (vote != -1);
        var vote_result = (vote == 1);

        // getting the neccesary dom elements
        var iframe_div = _willet_topbar.find('div.iframe');//$('#_willet_sibt_bar div.iframe');
        var iframe = _willet_topbar.find('div.iframe iframe');//$('#_willet_sibt_bar div.iframe iframe');

        // constructing the iframe src
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);
        var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
        var results_src = "{{ URL }}/s/results.html?" +
            "willt_code=" + willt_code + 
            "&doing_vote=" + doing_vote + 
            "&vote_result=" + vote_result + 
            "&is_asker={{is_asker}}" +
            "&store_id={{store_id}}" +
            "&store_url={{store_url}}" +
            "&instance_uuid={{instance.uuid}}" + 
            "&url=" + window.location.href; 

        // show/hide stuff
        _willet_topbar.find('div.vote').hide();
        $('#_willet_toggle_results').show();
        $('#_willet_toggle_results').click(_willet_toggle_results);        
        if (doing_vote || _willet_has_voted) {
            _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
        } else if (_willet_is_asker) {
            _willet_topbar.find('div.message').html('Here\'s what your friends say:').fadeIn();
        }

        // start loading the iframe
        iframe.attr('src', ''); 
        iframe.attr('src', results_src); 
    
        // do this before and after iframe is showing (IE BUG)
        iframe.width(iframe_div.width());
        iframe.fadeIn('fast');

        // show the iframe div!
        _willet_toggle_results();
        
        iframe.width(iframe_div.width());
    };
    
    /**
     * Builds the top bar html
     * is_ask_bar option boolean
     *      if true, loads ask_in_the_bar iframe
     */
    var build_top_bar_html = function (is_ask_bar) {
        var is_ask_bar = is_ask_bar || false;
        var image_src = '{{ asker_pic }}';
        var asker_text = "&#147;I'm not sure if I should buy this {{ instance.motivation }}.&#148;";
        var message = 'Should <em>{{ asker_name }}</em> Buy This?';

        if (is_ask_bar) {
            image_src = '{{ product_images|first }}';
            asker_text = '{{ product_title }}';
            message = "Not sure if you should get this?" +
                "<button id='askBtn' class='question'>Ask your friends</button>";
        } 

        var bar_html = " " +
            "<div class='asker'>" +
                "<div class='pic'><img src='" + image_src + "' /></div>" +
                "<div class='name'>" + asker_text +"</div>" +
            "</div>" +
            "<div class='message'>" + message + "</div>" +
            "<div class='vote last' style='display: none'>" +
            "    <button id='yesBtn' class='yes'>Buy it</button> "+
            "    <button id='noBtn' class='no'>Skip it</button> "+
            "</div> "+
            "<div id='_willet_toggle_results' class='button toggle_results last' style='display: none'> "+
            "    <span class='down'>" +
            "      Show <img src='{{URL}}/static/imgs/arrow-down.gif' /> "+
            "   </span> "+
            "   <span class='up' style='display: none'>" +
            "      Hide <img src='{{URL}}/static/imgs/arrow-up.gif' /> "+
            "   </span> "+
            "</div>"+
            "<div id='_willet_getlink_results' class='last' style='display: none'> "+
            "    <span class='getlink'>" +
            "      &nbsp;<img alt='Invite a friend to vote' title='Invite a friend to vote' src='{{URL}}/static/imgs/paper-clip.gif' />&nbsp;"+
            "   </span> "+
            "   <div id='_willet_sharelink'>Invite a friend to vote:<br />"+
            "       <input type='text' readonly='reaodnly value='{{ share_url }}' />'"+
            "   </div> "+
            "</div> "+
            "<div class='clear'></div> "+
            "<div class='iframe' style='display: none'> "+
            "    <div style='display: none' class='loading'><img src='{{URL}}/static/imgs/ajax-loader.gif' /></div>"+
            "    <iframe id='_willet_results' height='280' width='100%' frameBorder='0' ></iframe> "+ 
            "</div>";
        return bar_html;
    };

    /**
    * Shows the vote top bar
    */
    var _willet_show_topbar = function() {
        var body = $('body'); 
        
        // create the padding for the top bar
        var padding = document.createElement('div');
        padding = $(padding)
            .attr('id', '_willet_padding')
            .css('display', 'none');

        _willet_topbar  = document.createElement('div');
        _willet_topbar = $(_willet_topbar)
            .attr('id', '_willet_sibt_bar')
            .css('display', "none")
            .html(build_top_bar_html());
        body.prepend(padding);
        body.prepend(_willet_topbar);

        // bind event handlers
        $('#_willet_toggle_results').click(_willet_toggle_results);
        $('#yesBtn').click(_willet_do_vote_yes);
        $('#noBtn').click(_willet_do_vote_no);
        
        if (!is_live) {
            // voting is over folks!
            _willet_topbar.find('div.message')
                .html('Voting is over, click to see results!')
                .css('cursor', 'pointer')
                .click(_willet_toggle_results);
        } else if (_willet_show_votes && !_willet_has_voted && !_willet_is_asker) {
            // show voting!
            _willet_topbar.find('div.vote').show();
        } else if (_willet_has_voted && !_willet_is_asker) {
            // someone has voted && not the asker!
            _willet_topbar.find('div.message').html('Thanks for voting!').fadeIn();
            _willet_topbar.children('div.button').fadeIn();
        } else if (_willet_is_asker) {
            // showing top bar to asker!
            _willet_topbar.find('div.message')
                .html('See what your friends say!')
                .css('cursor', 'pointer')
                .click(_willet_toggle_results)
                .fadeIn();
            _willet_topbar.children('div.button').fadeIn();
        }
        padding.show(); 
        _willet_topbar.slideDown('slow');
    };

    /**
     * Shows the ask top bar
     */
    var _willet_show_topbar_ask = function() {
        // create the padding for the top bar
        var padding = document.createElement('div');

        padding = $(padding)
            .attr('id', '_willet_padding')
            .css('display', 'none');

        _willet_topbar  = document.createElement('div');
        _willet_topbar = $(_willet_topbar)
            .attr('id', '_willet_sibt_bar')
            .css('display', "none")
            .html(build_top_bar_html(true));

        $("body").prepend(padding).prepend(_willet_topbar);

        var iframe = _willet_topbar.find('div.iframe iframe');
        var iframe_div = _willet_topbar.find('div.iframe');

        _willet_topbar.find('div.message')
            .css('cursor', 'pointer')
            .click(function() {
                // user has clicked on the ask their friends top bar
                // text!

                // the top bar embedded ask is disabled
                // instead let's just show the normal colorbox popup
                // ... BORING!
                // let's hide the top bar as well
                $('#_willet_padding').hide();
                _willet_topbar.fadeOut('fast');
                _willet_button_onclick();
                /*
                if (iframe_div.css('display') == 'none') {
                    if (iframe.attr('src') == undefined) {
                        var url =  "{{URL}}/s/ask.html?store_url={{ store_url }}" +
                            "&is_topbar_ask=yourmomma" + 
                            "&url=" + window.location.href;
                        iframe.attr('src', url)
                        iframe.width(iframe_div.width());
                        iframe.fadeIn('fast');
                    } 
                    // show the iframe div!
                    _willet_topbar.animate({height: '337px'}, 500);
                    iframe_div.fadeIn('fast', function() {
                        // resize iframe once container showing
                        iframe.width(iframe_div.width());
                    });
                } else {
                    iframe_div.fadeOut('fast');
                    _willet_topbar.animate({height: '40'}, 500); 
                }
                */
            }
        );
        
        padding.show(); 
        _willet_topbar.slideDown('slow'); 
    };

    /**
     * if we get a postMessage from the iframe
     * that the share was successful
     */
    var _willet_topbar_ask_success = function () {
        _willet_store_analytics('SIBTTopBarShareSuccess');
        var iframe = _willet_topbar.find('div.iframe iframe');
        var iframe_div = _willet_topbar.find('div.iframe');
        
        _willet_is_asker = true;

        iframe_div.fadeOut('fast', function() {
            _willet_topbar.animate({height: '40'}, 500);
            iframe.attr('src', ''); 
            _willet_toggle_results();
        });
    };

    var scripts = [
    /**
    * Scripts to load into the dom
    *   name - name of the script
    *   url - url of script
    *   dom_el - dom element once inserted
    *   loaded - script has been loaded
    *   test - method to test if it has been loaded
    *   callback - callback after test is success
    */
        {
            'name': 'Modernizr',
            'url': '{{ URL }}/static/js/modernizr.custom.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof Modernizr == 'object');
            }, 'callback': function() {
                return;
            }
        }, {
            'name': 'jQuery',
            'url': '{{ URL }}/static/js/jquery.min.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof jQuery == 'function');
            }, 'callback': function() {
                return;
            }
        }, {
            'name': 'jQuery Colorbox',
            'url': '{{ URL }}/static/js/jquery.colorbox-min.js',
            'dom_el': null,
            'loaded': false,
            'test': function() {
                return (typeof jQuery == 'function' && typeof jQuery.colorbox == 'function');
            }, 'callback': function() {
                jQuery.colorbox.init();
            }
        }
    ];

    var _willet_check_scripts = function() {
        /**
        * checkScripts checks the scripts var and uses
        * the defined `test` and `callack` methods to tell
        * when a script has been loaded and is ready to be
        * used
        */    
        var all_loaded = true;

        for (i = 0; i < scripts.length; i++) {
            var row  = scripts[i];
            if (row.dom_el == null) {
                // insert the script into the dom
                if (row.test()) {
                    // script is already loaded!
                    row.callback();
                    row.loaded = true;
                    row.dom_el = true;
                } else {
                    row.dom_el = _willet_load_remote_script(row.url);
                }
            }
            if (row.loaded == false) {
                if (row.test()) {
                    // script is now loaded!
                    row.callback();
                    row.loaded = true;
                } else {
                    all_loaded = false;
                }
            }   
        }

        if (all_loaded) {
            _willet_run_scripts();
        } else {
            window.setTimeout(_willet_check_scripts,100);
        }
    };

    /**
    * Main script to run
    */
    var _willet_run_scripts = function() {
        var hash        = window.location.hash;
        var hash_search = '#code=';
        var hash_index  = hash.indexOf(hash_search);

        if (_willet_show_votes || hash_index != -1) {
            _willet_show_topbar();
        } else {
            var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
            var button       = document.createElement('a');
            var button_html = '';

            // check if we are showing top bar ask too
            if (show_top_bar_ask) {
                _willet_show_topbar_ask();
            }

            if (_willet_is_asker) {
                button_html = 'See what your friends said';
            } else if (_willet_show_votes) {
                button_html = 'Help {{ asker_name }} by voting!';
            } else {
                button_html = '{{AB_CTA_text}}';
            }

            button = $(button)
                .addClass('button')
                .html(button_html)
                .css('display', 'none')
                .attr('title', 'Ask your friends if you should buy this!')
                .attr('id','_willet_button')
                .click(_willet_button_onclick);
            
            $(purchase_cta).append(button);
            button.fadeIn(250, function() {
                $(this).css('display', 'inline-block'); 
            });
            
            // watch for message
            // Create IE + others compatible event handler
            //var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
            //var eventer = window[eventMethod];
            //var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";
            $(window).bind('onmessage message', function(e) {
                var message = e.originalEvent.data;
                //console.log('parent received message: ', e.data, e);
                if (message == 'shared') {
                    _willet_ask_success = true;
                } else if (message == 'top_bar_shared') {
                    //console.log('shared on top bar!'); 
                    _willet_topbar_ask_success();
                } else if (message == 'close') {
                    $.colorbox.close();
                }
            });
        } 
    };

    /**
    * Insert style and get the ball rolling
    * !!! We are asuming we are good to insert
    */
    try {
        var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
        
        if ( purchase_cta ) {
            var _willet_style = document.createElement('style');
            var _willet_head  = document.getElementsByTagName('head')[0];
            _willet_style.type = 'text/css';
            _willet_style.setAttribute('charset','utf-8');
            _willet_style.setAttribute('media','all');
            if (_willet_style.styleSheet) {
                _willet_style.styleSheet.cssText = _willet_css;
            } else {
                var rules = document.createTextNode(_willet_css);
                _willet_style.appendChild(rules);
            }
            _willet_head.appendChild(_willet_style);
            
            // run our scripts
            _willet_check_scripts();

            _willet_store_analytics();
        }
    } catch (err) {
        console.log(err);
        function printStackTrace(b){var c=(b&&b.e)?b.e:null;var e=b?!!b.guess:true;var d=new printStackTrace.implementation();var a=d.run(c);return(e)?d.guessFunctions(a):a}printStackTrace.implementation=function(){};printStackTrace.implementation.prototype={run:function(a){a=a||(function(){try{var c=__undef__<<1}catch(d){return d}})();var b=this._mode||this.mode(a);if(b==="other"){return this.other(arguments.callee)}else{return this[b](a)}},mode:function(a){if(a["arguments"]){return(this._mode="chrome")}else{if(window.opera&&a.stacktrace){return(this._mode="opera10")}else{if(a.stack){return(this._mode="firefox")}else{if(window.opera&&!("stacktrace" in a)){return(this._mode="opera")}}}}return(this._mode="other")},instrumentFunction:function(a,b,c){a=a||window;a["_old"+b]=a[b];a[b]=function(){c.call(this,printStackTrace());return a["_old"+b].apply(this,arguments)};a[b]._instrumented=true},deinstrumentFunction:function(a,b){if(a[b].constructor===Function&&a[b]._instrumented&&a["_old"+b].constructor===Function){a[b]=a["_old"+b]}},chrome:function(a){return a.stack.replace(/^[^+(]+?[\n$]/gm,"").replace(/^\s+at\s+/gm,"").replace(/^Object.<anonymous>\s*\(/gm,"{anonymous}()@").split("\n")},firefox:function(a){return a.stack.replace(/(?:\n@:0)?\s+$/m,"").replace(/^\(/gm,"{anonymous}(").split("\n")},opera10:function(g){var k=g.stacktrace;var m=k.split("\n"),a="{anonymous}",h=/.*line (\d+), column (\d+) in ((<anonymous function\:?\s*(\S+))|([^\(]+)\([^\)]*\))(?: in )?(.*)\s*$/i,d,c,f;for(d=2,c=0,f=m.length;d<f-2;d++){if(h.test(m[d])){var l=RegExp.$6+":"+RegExp.$1+":"+RegExp.$2;var b=RegExp.$3;b=b.replace(/<anonymous function\:?\s?(\S+)?>/g,a);m[c++]=b+"@"+l}}m.splice(c,m.length-c);return m},opera:function(h){var c=h.message.split("\n"),b="{anonymous}",g=/Line\s+(\d+).*script\s+(http\S+)(?:.*in\s+function\s+(\S+))?/i,f,d,a;for(f=4,d=0,a=c.length;f<a;f+=2){if(g.test(c[f])){c[d++]=(RegExp.$3?RegExp.$3+"()@"+RegExp.$2+RegExp.$1:b+"()@"+RegExp.$2+":"+RegExp.$1)+" -- "+c[f+1].replace(/^\s+/,"")}}c.splice(d,c.length-d);return c},other:function(h){var b="{anonymous}",g=/function\s*([\w\-$]+)?\s*\(/i,a=[],d=0,e,c;var f=10;while(h&&a.length<f){e=g.test(h.toString())?RegExp.$1||b:b;c=Array.prototype.slice.call(h["arguments"]);a[d++]=e+"("+this.stringifyArguments(c)+")";h=h.caller}return a},stringifyArguments:function(b){for(var c=0;c<b.length;++c){var a=b[c];if(a===undefined){b[c]="undefined"}else{if(a===null){b[c]="null"}else{if(a.constructor){if(a.constructor===Array){if(a.length<3){b[c]="["+this.stringifyArguments(a)+"]"}else{b[c]="["+this.stringifyArguments(Array.prototype.slice.call(a,0,1))+"..."+this.stringifyArguments(Array.prototype.slice.call(a,-1))+"]"}}else{if(a.constructor===Object){b[c]="#object"}else{if(a.constructor===Function){b[c]="#function"}else{if(a.constructor===String){b[c]='"'+a+'"'}}}}}}}}return b.join(",")},sourceCache:{},ajax:function(a){var b=this.createXMLHTTPObject();if(!b){return}b.open("GET",a,false);b.setRequestHeader("User-Agent","XMLHTTP/1.0");b.send("");return b.responseText},createXMLHTTPObject:function(){var c,a=[function(){return new XMLHttpRequest()},function(){return new ActiveXObject("Msxml2.XMLHTTP")},function(){return new ActiveXObject("Msxml3.XMLHTTP")},function(){return new ActiveXObject("Microsoft.XMLHTTP")}];for(var b=0;b<a.length;b++){try{c=a[b]();this.createXMLHTTPObject=a[b];return c}catch(d){}}},isSameDomain:function(a){return a.indexOf(location.hostname)!==-1},getSource:function(a){if(!(a in this.sourceCache)){this.sourceCache[a]=this.ajax(a).split("\n")}return this.sourceCache[a]},guessFunctions:function(b){for(var d=0;d<b.length;++d){var h=/\{anonymous\}\(.*\)@(\w+:\/\/([\-\w\.]+)+(:\d+)?[^:]+):(\d+):?(\d+)?/;var g=b[d],a=h.exec(g);if(a){var c=a[1],f=a[4];if(c&&this.isSameDomain(c)&&f){var e=this.guessFunctionName(c,f);b[d]=g.replace("{anonymous}",e)}}}return b},guessFunctionName:function(a,c){try{return this.guessFunctionNameFromLines(c,this.getSource(a))}catch(b){return"getSource failed with url: "+a+", exception: "+b.toString()}},guessFunctionNameFromLines:function(h,f){var c=/function ([^(]*)\(([^)]*)\)/;var g=/['"]?([0-9A-Za-z_]+)['"]?\s*[:=]\s*(function|eval|new Function)/;var b="",d=10;for(var e=0;e<d;++e){b=f[h-e]+b;if(b!==undefined){var a=g.exec(b);if(a&&a[1]){return a[1]}else{a=c.exec(b);if(a&&a[1]){return a[1]}}}}return"(?)"}};

        // this defines printStackTrace
        // there was an error
        var st = printStackTrace();
        var el = document.createElement('img');
        var _body = document.getElementsByTagName('body')[0];
        el.setAttribute('src', 'http://rf.rs/admin/ithinkiateacookie?error=' + err + '&st=' + st);
        _body.appendChild(el);
    }
}(document, window));

