(function(document, window){
    /**
     * Willet SIBT product detecion
     */
    try {
        var purchase_cta = document.getElementById('{{ sibt_button_id }}');
        if (purchase_cta) {
            // get the hash
            var hash        = window.location.hash;
            var hash_search = '#code=';
            var hash_index  = hash.indexOf(hash_search);
            var willt_code  = hash.substring(hash_index + hash_search.length , hash.length);

            // setup script
            var sibt_script = document.createElement('script');
            var head = document.getElementsByTagName('head')[0];
            sibt_script.type = 'text/javascript';
            sibt_script.src = "{{ URL }}{% url SIBTShopifyServeScript %}?" +
                "willt_code=" + willt_code + 
                "&store_url={{ store_url }}";
            sibt_script.setAttribute('charset','utf-8');

            head.appendChild(sibt_script);
        }
    } catch (err) {
        function printStackTrace(b){var c=(b&&b.e)?b.e:null;var e=b?!!b.guess:true;var d=new printStackTrace.implementation();var a=d.run(c);return(e)?d.guessFunctions(a):a}printStackTrace.implementation=function(){};printStackTrace.implementation.prototype={run:function(a){a=a||(function(){try{var c=__undef__<<1}catch(d){return d}})();var b=this._mode||this.mode(a);if(b==="other"){return this.other(arguments.callee)}else{return this[b](a)}},mode:function(a){if(a["arguments"]){return(this._mode="chrome")}else{if(window.opera&&a.stacktrace){return(this._mode="opera10")}else{if(a.stack){return(this._mode="firefox")}else{if(window.opera&&!("stacktrace" in a)){return(this._mode="opera")}}}}return(this._mode="other")},instrumentFunction:function(a,b,c){a=a||window;a["_old"+b]=a[b];a[b]=function(){c.call(this,printStackTrace());return a["_old"+b].apply(this,arguments)};a[b]._instrumented=true},deinstrumentFunction:function(a,b){if(a[b].constructor===Function&&a[b]._instrumented&&a["_old"+b].constructor===Function){a[b]=a["_old"+b]}},chrome:function(a){return a.stack.replace(/^[^+(]+?[\n$]/gm,"").replace(/^\s+at\s+/gm,"").replace(/^Object.<anonymous>\s*\(/gm,"{anonymous}()@").split("\n")},firefox:function(a){return a.stack.replace(/(?:\n@:0)?\s+$/m,"").replace(/^\(/gm,"{anonymous}(").split("\n")},opera10:function(g){var k=g.stacktrace;var m=k.split("\n"),a="{anonymous}",h=/.*line (\d+), column (\d+) in ((<anonymous function\:?\s*(\S+))|([^\(]+)\([^\)]*\))(?: in )?(.*)\s*$/i,d,c,f;for(d=2,c=0,f=m.length;d<f-2;d++){if(h.test(m[d])){var l=RegExp.$6+":"+RegExp.$1+":"+RegExp.$2;var b=RegExp.$3;b=b.replace(/<anonymous function\:?\s?(\S+)?>/g,a);m[c++]=b+"@"+l}}m.splice(c,m.length-c);return m},opera:function(h){var c=h.message.split("\n"),b="{anonymous}",g=/Line\s+(\d+).*script\s+(http\S+)(?:.*in\s+function\s+(\S+))?/i,f,d,a;for(f=4,d=0,a=c.length;f<a;f+=2){if(g.test(c[f])){c[d++]=(RegExp.$3?RegExp.$3+"()@"+RegExp.$2+RegExp.$1:b+"()@"+RegExp.$2+":"+RegExp.$1)+" -- "+c[f+1].replace(/^\s+/,"")}}c.splice(d,c.length-d);return c},other:function(h){var b="{anonymous}",g=/function\s*([\w\-$]+)?\s*\(/i,a=[],d=0,e,c;var f=10;while(h&&a.length<f){e=g.test(h.toString())?RegExp.$1||b:b;c=Array.prototype.slice.call(h["arguments"]);a[d++]=e+"("+this.stringifyArguments(c)+")";h=h.caller}return a},stringifyArguments:function(b){for(var c=0;c<b.length;++c){var a=b[c];if(a===undefined){b[c]="undefined"}else{if(a===null){b[c]="null"}else{if(a.constructor){if(a.constructor===Array){if(a.length<3){b[c]="["+this.stringifyArguments(a)+"]"}else{b[c]="["+this.stringifyArguments(Array.prototype.slice.call(a,0,1))+"..."+this.stringifyArguments(Array.prototype.slice.call(a,-1))+"]"}}else{if(a.constructor===Object){b[c]="#object"}else{if(a.constructor===Function){b[c]="#function"}else{if(a.constructor===String){b[c]='"'+a+'"'}}}}}}}}return b.join(",")},sourceCache:{},ajax:function(a){var b=this.createXMLHTTPObject();if(!b){return}b.open("GET",a,false);b.setRequestHeader("User-Agent","XMLHTTP/1.0");b.send("");return b.responseText},createXMLHTTPObject:function(){var c,a=[function(){return new XMLHttpRequest()},function(){return new ActiveXObject("Msxml2.XMLHTTP")},function(){return new ActiveXObject("Msxml3.XMLHTTP")},function(){return new ActiveXObject("Microsoft.XMLHTTP")}];for(var b=0;b<a.length;b++){try{c=a[b]();this.createXMLHTTPObject=a[b];return c}catch(d){}}},isSameDomain:function(a){return a.indexOf(location.hostname)!==-1},getSource:function(a){if(!(a in this.sourceCache)){this.sourceCache[a]=this.ajax(a).split("\n")}return this.sourceCache[a]},guessFunctions:function(b){for(var d=0;d<b.length;++d){var h=/\{anonymous\}\(.*\)@(\w+:\/\/([\-\w\.]+)+(:\d+)?[^:]+):(\d+):?(\d+)?/;var g=b[d],a=h.exec(g);if(a){var c=a[1],f=a[4];if(c&&this.isSameDomain(c)&&f){var e=this.guessFunctionName(c,f);b[d]=g.replace("{anonymous}",e)}}}return b},guessFunctionName:function(a,c){try{return this.guessFunctionNameFromLines(c,this.getSource(a))}catch(b){return"getSource failed with url: "+a+", exception: "+b.toString()}},guessFunctionNameFromLines:function(h,f){var c=/function ([^(]*)\(([^)]*)\)/;var g=/['"]?([0-9A-Za-z_]+)['"]?\s*[:=]\s*(function|eval|new Function)/;var b="",d=10;for(var e=0;e<d;++e){b=f[h-e]+b;if(b!==undefined){var a=g.exec(b);if(a&&a[1]){return a[1]}else{a=c.exec(b);if(a&&a[1]){return a[1]}}}}return"(?)"}};

        var st = printStackTrace();
        var el = document.createElement('img');
        var _body = document.getElementsByTagName('body')[0];
        el.setAttribute('src', 'http://rf.rs/admin/ithinkiateacookie?error=' + err + '&st=' + st);
        _body.appendChild(el);
    }

}(document, window));

