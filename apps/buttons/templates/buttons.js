/**
 * Buttons JS
 */

/**
 * body of code to run when all scripts have been injected
 */
var _willet_run_scripts = function() {
    // get the button where we are going to insert
    var here = window.location + '.json';

    $.getJSON (
        here,
        function(data) {
            // callback function
            
            /*
            // Used to add meta tags to head
            var addEl = function(head, el, property, content) {
                var dom_el = document.createElement(el);
                dom_el.setAttribute('property', property);
                dom_el.content = content;
                head.appendChild(dom_el);
            };

            // META tags we are going to inject
            var meta_tags = [
                {
                    'property': "fb:app_id",
                    'content': "{{ FACEBOOK_APP_ID }}",
                }, {
                    'property': "og:type",
                    'content': "shopify_buttons:product"
                }, {
                    'property': "og:title",
                    'content': data.product.title, 
                },  {
                    'property': "og:description",
                    'content': data.product.body_html, 
                }, 
                {
                    'property': "og:url",
                    'content': "{{URL}}/{{ willt_code }}"
                }
            ];
            
            if  (data.product.images[0] != null ) {
                meta_tags.push({'property': "og:image", 'content': data.product.images[0].src});
            } else {
                meta_tags.push({'property': "og:image", 'content': '{{URL}}/static/imgs/ShopConnectionLogo.png'});
            }

            // add all those meta tags
            for (i = 0; i < meta_tags.length; i++) {
                addEl(head, 'meta', meta_tags[i].property, meta_tags[i].content);
            }
            head.setAttribute('prefix', "og: http://ogp.me/ns# fb: http://ogp.me/ns/fb# shopify_buttons: http://ogp.me/ns/fb/shopify_buttons#" );
            console.log('got meta tags', meta_tags); 
            
            */

            var head = document.getElementsByTagName('head')[0];
            var tmp = document.createElement( 'script' );
            $(tmp).attr( 'type', 'text/javascript' );
            $(tmp).attr( 'src', 'http://assets.pinterest.com/js/pinit.js' );
            head.appendChild( tmp );
            
            tmp = document.createElement( 'script' );
            $(tmp).attr( 'type', 'text/javascript' );
            $(tmp).attr( 'src', 'http://platform.tumblr.com/v1/share.js' );
            head.appendChild( tmp );

            /**
             * INSERT IFRAME WITH DATA
             */
            var button_div = document.getElementById('{{ app.button_selector }}');

            if (button_div &&  window.iframe_loaded == undefined) {
                button_div.style = "float: left; height:30px; width: 205px;";

                window.iframe_loaded = "teh fb_iframe haz been loaded";
                /*
                console.log('loading fb_iframe');
                var fb_iframe      = document.createElement('iframe');
                fb_iframe.setAttribute('allowtransparency', 'true');
                fb_iframe.setAttribute('frameborder', '0');
                fb_iframe.setAttribute('scrolling', 'no');
                fb_iframe.setAttribute('style', 'margin-top: 3px; margin-right: 5px; width:80px; height:18px; float: left; border: 1px solid #cad4e7; border-radius: 2px;');
                fb_iframe.setAttribute('src', '{{ URL }}/b/shopify/load/iframe.html?app_uuid={{app.uuid}}&willt_code={{willt_code}}');

                button_div.appendChild( fb_iframe );
                console.log('fb_iframe inserted');
                */
        
                // Tumblr
                var a = document.createElement( 'a' );
                var style = "display:inline-block; text-indent:-9999px; " +
                            "overflow:hidden; width:63px; height:20px; " + 
                            "background:url('http://platform.tumblr.com/v1/" + 
                            "share_2.png') top left no-repeat transparent; float: left; margin-right: 5px; margin-top: 3px;" 
                $(a).attr( 'href', 'http://www.tumblr.com/share' );
                $(a).attr( 'title', "Share on Tumblr" );
                $(a).attr( 'style', style);
                $(a).html = "Share on Tumblr";
                button_div.appendChild( a );

                // Pinterest
                var photo = '';
                if ( data.product.images[0] != null ) {
                    photo = data.product.images[0].src;
                }

                var d = document.createElement( 'div' );
                $(d).attr('style', 'float: left; width: 50px !important;' );

                a = document.createElement( 'a' );
                var u = "http://pinterest.com/pin/create/button/?" +
                        "url=" + window.location.href + 
                        "&media=" + photo + 
                        "&description=" + data.product.body_html;
                $(a).attr( 'href', u );
                $(a).attr( 'class', 'pin-it-button' );
                $(a).attr( 'count-layout', "horizontal" );
                $(a).html = "Pin It";
                d.appendChild( a );
                button_div.appendChild( d );
            }
        }
    );
};

// let's get this party started 
_willet_run_scripts();
