/** Willet's "Should I Buy This?" Shopify App
  * Copyright 2011, Willet, Inc.
 **/

/**
 * TODO
 * add comments for wtf this is
 */

var _willet_ask_success = false;
var _willet_is_asker = (parseInt('{{ is_asker }}') == 1); // did they ask?
var _willet_show_votes = (parseInt('{{ show_votes }}') == 1);
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

var _willet_add_other_instance = function(instance) {
    /**
     * this method will be used if a user has multiple
     * "sibt" instances for a given product page.
     * Currently this functionality is not implemented in the backend
     */
    var el = document.createElement('img');
    el = $(el);
    el.attr('src', instance.src);
    el.attr('title', 'Should ' + instance.user_name + ' buy this?');
    el.attr('data-item', instance.code);
    el.click(function() {
        var code = $(this).attr('data-item');
        var photo_src = $('#image img').attr('src'); 
        _willet_show_vote();
    });
    
    return el;
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

/**
 * Called when ask iframe is closed
 */
var _willet_ask_callback = function() {
    if (_willet_ask_success) {
        _willet_is_asker = true;
        $('#_willet_button').html('See if your friends have voted');
    }
};

/**
 * Onclick event handler for the 'sibt' button
 */
var _willet_button_onclick = function() {
    if (_willet_is_asker || _willet_show_votes) {
        // instead of showing vote again, let's show the results
        _willet_show_vote();
    } else {
        var url =  "{{URL}}/s/ask.html?store_id={{ store_id }}&url=" + window.location.href;

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
    }
};

var _willet_show_vote = function() {
    var photo_src = $('#image img').attr('src'); 
    var hash        = window.location.hash;
    var hash_search = '#code=';
    var hash_index  = hash.indexOf(hash_search);
    var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);
        
    var url = "{{URL}}/s/vote.html?willt_code=" + willt_code + 
            "&is_asker={{is_asker}}&store_id={{store_id}}&photo=" + 
            photo_src + "&url=" + window.location.href + "&instance_uuid={{instance.uuid}}";

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
        'name': 'jQuery',
        'url': 'https://social-referral.appspot.com/static/js/jquery.min.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            return (typeof jQuery == 'function');
        }, 'callback': function() {
            return;
        }
    }, {
        'name': 'jQuery Colorbox',
        'url': 'https://social-referral.appspot.com/static/js/jquery.colorbox-min.js',
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
                //console.log('script already loaded', row.name);
                row.callback();
                row.loaded = true;
                row.dom_el = true;
            } else {
                //console.log('loading remote script', row.name);
                row.dom_el = _willet_load_remote_script(row.url);
            }
        }
        if (row.loaded == false) {
            if (row.test()) {
                // script is now loaded!
                //console.log('script has been loaded', row.name);
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
    //console.log('running');
    var hash        = window.location.hash;
    var hash_search = '#code=';
    var hash_index  = hash.indexOf(hash_search);

    // Show the vote fast
    if (_willet_show_votes || hash_index != -1) {
        _willet_show_vote();
    }

    var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
    var button       = document.createElement('a');
    
    button.setAttribute('class', 'button');
    button.setAttribute('style', 'display: none'); 
    button.setAttribute( 'title', 'Ask your friends if you should buy this!' );
    button.setAttribute( 'value', '' );
    button.setAttribute( 'onClick', '_willet_button_onclick(); return false;');
    button.setAttribute( 'id', '_willet_button' );
    // Construct button.
    if (_willet_is_asker) {
        $(button).html('See what your friends said!');
    } else if (_willet_show_votes) {
        // not the asker but we are showing votes
        $(button).html('Help {{ asker_name }} by voting!');
    } else {
        $(button).html( "{{AB_CTA_text}}" );
    }
    $(purchase_cta).append(button);
    $("#_willet_button").fadeIn(250).css('display', 'inline-block');
    
    // watch for message
    // Create IE + others compatible event handler
    var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
    var eventer = window[eventMethod];
    var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";

    // Listen to message from child window
    eventer(messageEvent,function(e) {
        //console.log('parent received message!:  ',e.data);
        if (e.data == 'shared') {
            _willet_ask_success = true;
        } else if (e.data == 'close') {
            // the iframe wants to be closed
            // ... maybe it's emo
            $.colorbox.close();
        }
    }, false);
};

/**
 * Insert style and get the ball rolling
 */
try {
    var purchase_cta = document.getElementById('_willet_shouldIBuyThisButton');
    
    if ( purchase_cta ) {
        var _willet_style = document.createElement('link');
        var _willet_head  = document.getElementsByTagName('head')[0];
        _willet_style.setAttribute('rel', 'stylesheet');
        _willet_style.setAttribute('href', '{{URL}}/static/sibt/css/{{ stylesheet }}.css');
        _willet_style.setAttribute('type', 'text/css');
        _willet_style.setAttribute('media', 'all');
        _willet_head.appendChild(_willet_style);
        
        // run our scripts
        _willet_check_scripts();
    }

} catch (err) {
    // this defines printStackTrace
    function printStackTrace(b){var c=(b&&b.e)?b.e:null;var e=b?!!b.guess:true;var d=new printStackTrace.implementation();var a=d.run(c);return(e)?d.guessFunctions(a):a}printStackTrace.implementation=function(){};printStackTrace.implementation.prototype={run:function(a){a=a||(function(){try{var c=__undef__<<1}catch(d){return d}})();var b=this._mode||this.mode(a);if(b==="other"){return this.other(arguments.callee)}else{return this[b](a)}},mode:function(a){if(a["arguments"]){return(this._mode="chrome")}else{if(window.opera&&a.stacktrace){return(this._mode="opera10")}else{if(a.stack){return(this._mode="firefox")}else{if(window.opera&&!("stacktrace" in a)){return(this._mode="opera")}}}}return(this._mode="other")},instrumentFunction:function(a,b,c){a=a||window;a["_old"+b]=a[b];a[b]=function(){c.call(this,printStackTrace());return a["_old"+b].apply(this,arguments)};a[b]._instrumented=true},deinstrumentFunction:function(a,b){if(a[b].constructor===Function&&a[b]._instrumented&&a["_old"+b].constructor===Function){a[b]=a["_old"+b]}},chrome:function(a){return a.stack.replace(/^[^\(]+?[\n$]/gm,"").replace(/^\s+at\s+/gm,"").replace(/^Object.<anonymous>\s*\(/gm,"{anonymous}()@").split("\n")},firefox:function(a){return a.stack.replace(/(?:\n@:0)?\s+$/m,"").replace(/^\(/gm,"{anonymous}(").split("\n")},opera10:function(g){var k=g.stacktrace;var m=k.split("\n"),a="{anonymous}",h=/.*line (\d+), column (\d+) in ((<anonymous function\:?\s*(\S+))|([^\(]+)\([^\)]*\))(?: in )?(.*)\s*$/i,d,c,f;for(d=2,c=0,f=m.length;d<f-2;d++){if(h.test(m[d])){var l=RegExp.$6+":"+RegExp.$1+":"+RegExp.$2;var b=RegExp.$3;b=b.replace(/<anonymous function\:?\s?(\S+)?>/g,a);m[c++]=b+"@"+l}}m.splice(c,m.length-c);return m},opera:function(h){var c=h.message.split("\n"),b="{anonymous}",g=/Line\s+(\d+).*script\s+(http\S+)(?:.*in\s+function\s+(\S+))?/i,f,d,a;for(f=4,d=0,a=c.length;f<a;f+=2){if(g.test(c[f])){c[d++]=(RegExp.$3?RegExp.$3+"()@"+RegExp.$2+RegExp.$1:b+"()@"+RegExp.$2+":"+RegExp.$1)+" -- "+c[f+1].replace(/^\s+/,"")}}c.splice(d,c.length-d);return c},other:function(h){var b="{anonymous}",g=/function\s*([\w\-$]+)?\s*\(/i,a=[],d=0,e,c;var f=10;while(h&&a.length<f){e=g.test(h.toString())?RegExp.$1||b:b;c=Array.prototype.slice.call(h["arguments"]);a[d++]=e+"("+this.stringifyArguments(c)+")";h=h.caller}return a},stringifyArguments:function(b){for(var c=0;c<b.length;++c){var a=b[c];if(a===undefined){b[c]="undefined"}else{if(a===null){b[c]="null"}else{if(a.constructor){if(a.constructor===Array){if(a.length<3){b[c]="["+this.stringifyArguments(a)+"]"}else{b[c]="["+this.stringifyArguments(Array.prototype.slice.call(a,0,1))+"..."+this.stringifyArguments(Array.prototype.slice.call(a,-1))+"]"}}else{if(a.constructor===Object){b[c]="#object"}else{if(a.constructor===Function){b[c]="#function"}else{if(a.constructor===String){b[c]='"'+a+'"'}}}}}}}}return b.join(",")},sourceCache:{},ajax:function(a){var b=this.createXMLHTTPObject();if(!b){return}b.open("GET",a,false);b.setRequestHeader("User-Agent","XMLHTTP/1.0");b.send("");return b.responseText},createXMLHTTPObject:function(){var c,a=[function(){return new XMLHttpRequest()},function(){return new ActiveXObject("Msxml2.XMLHTTP")},function(){return new ActiveXObject("Msxml3.XMLHTTP")},function(){return new ActiveXObject("Microsoft.XMLHTTP")}];for(var b=0;b<a.length;b++){try{c=a[b]();this.createXMLHTTPObject=a[b];return c}catch(d){}}},isSameDomain:function(a){return a.indexOf(location.hostname)!==-1},getSource:function(a){if(!(a in this.sourceCache)){this.sourceCache[a]=this.ajax(a).split("\n")}return this.sourceCache[a]},guessFunctions:function(b){for(var d=0;d<b.length;++d){var h=/\{anonymous\}\(.*\)@(\w+:\/\/([\-\w\.]+)+(:\d+)?[^:]+):(\d+):?(\d+)?/;var g=b[d],a=h.exec(g);if(a){var c=a[1],f=a[4];if(c&&this.isSameDomain(c)&&f){var e=this.guessFunctionName(c,f);b[d]=g.replace("{anonymous}",e)}}}return b},guessFunctionName:function(a,c){try{return this.guessFunctionNameFromLines(c,this.getSource(a))}catch(b){return"getSource failed with url: "+a+", exception: "+b.toString()}},guessFunctionNameFromLines:function(h,f){var c=/function ([^(]*)\(([^)]*)\)/;var g=/['"]?([0-9A-Za-z_]+)['"]?\s*[:=]\s*(function|eval|new Function)/;var b="",d=10;for(var e=0;e<d;++e){b=f[h-e]+b;if(b!==undefined){var a=g.exec(b);if(a&&a[1]){return a[1]}else{a=c.exec(b);if(a&&a[1]){return a[1]}}}}return"(?)"}};

    // there was an error
    var st = printStackTrace();
    var el = document.createElement('img');
    var _body = document.getElementsByTagName('body')[0];
    src.setAttribute('src', 'http://rf.rs/admin/ithinkiateacookie?error=' + err + '&st=' + st);
    _body.appendChild(el);
}
