/**
 * Buttons JS
 */

/**
 * Scripts to load into the dom
 *   name - name of the script
 *   url - url of script
 *   dom_el - dom element once inserted
 *   loaded - script has been loaded
 *   test - method to test if it has been loaded
 *   callback - callback after test is success
 */
var scripts = [
    {
        'name': 'jQuery',
        'url': 'http://rf.rs/static/js/jquery.min.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            return (typeof jQuery == 'function');
        }, 'callback': function() {
            $ = jQuery;
        }
    }, {
        'name': 'Facebook',
        'url': 'http://connect.facebook.net/en_US/all.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            if (typeof FB == 'undefined') {
                console.log('FB not loaded yet');
                return false;
            } else {
                return true;
            }
        }, 'callback': function() {
            //FB = unsafeWindow.FB;
        }
    }
];

/**
 * checkScripts checks the scripts var and uses
 * the defined `test` and `callack` methods to tell
 * when a script has been loaded and is ready to be
 * used
 */
var _willet_check_scripts = function() {
    /**
     * quick helper function to add scripts to dom
     */
    var loadRemoteScript = function(script) {
        var dom_el = document.createElement('script'); 
        dom_el.src = script;
        dom_el.type = 'text/javascript'; 
        document.getElementsByTagName('head')[0].appendChild(dom_el); 
        return dom_el;
    };
    var all_loaded = true;

    for (i = 0; i < scripts.length; i++) {
        var row  = scripts[i];
        
        if (row.loaded == false) {
            if (row.test()) {
                // script is now loaded!
                row.callback();
                row.loaded = true;
            } else {
                if (row.dom_el == null) {
                    row.dom_el = loadRemoteScript(row.url);
                }    
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
 * body of code to run when all scripts have been injected
 */
var _willet_run_scripts = function() {
    // HERE IS OUR REAL CODE
    

    // get the button where we are going to insert
    var button_selector = '{{ app.button_selector }}';
    var button_insert = $(button_selector);
    var userFound = {% if user_found %}{{ user_found }}{% else %}false{% endif %}; 
    var here = window.location + '.json';

    $.getJSON (
        here,
        function(data) {
            // callback function
            /**
             * Used to add meta tags to head
             */
            var addEl = function(head, el, property, content) {
                var dom_el = document.createElement(el);
                dom_el.setAttribute('property', property);
                dom_el.content = content;
                head.appendChild(dom_el);
            };

            /**
             * post to facebook
             */
            var fb_share_handler = function(payload) {
                console.log(payload)
                $.ajax({
                    url: '/fbShare',
                    type: 'post',
                    data: payload,
                    success: function(data) {
                        if (data) {
                            shareComplete();
                        } else {
                            console.log("Facebook post failure");
                        }
                    }
                });
            };

            /**
             * META tags we are going to inject
            */
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
                }, {
                    'property': "og:image",
                    'content': data.product.images[0].src, 
                }, {
                    'property': "og:description",
                    'content': data.product.body_html, 
                }, {
                    'property': "og:url",
                    'content': "{{ willt_url }}"
                }
            ];

            /**
            * Insert Faceb)ok DOM El
            */
            var fb_dom_el = document.createElement('div');
            var fb_root_el = document.createElement('div');
            var html_el = document.getElementsByTagName('html')[0];
            html_el.setAttribute('xmlns:fb', "https://www.facebook.com/2008/fbml");
            //$(fb_dom_el).attr('data-mode', 'button');
            //$(fb_dom_el).addClass('fb-add-to-timeline');
            $(fb_root_el).attr('id', 'fb-root');
            button_insert.append(fb_root_el); 
            //button_insert.append(fb_dom_el); 
            
            var want = document.createElement('input');
            $(want).attr('type', 'button');
            $(want).val('I want this!');
            $(want).click(function(e) {
                e.preventDefault();
                var fbData = {msg: message, wcode: '{{willt_code}}'}; 
                if (userFound) {
                    fb_share_handler(fbData)
                    return; 
                } else {
                    FB.login(
                        function(login_response) {
                            console.log(login_response);
                            if (!login_response.authResponse) {
                                // we weren't given permission
                                window.close();
                            } else { 
                                fbData.fb_token = login_response.authResponse.accessToken;
                                fbData.fb_id = login_response.authResponse.userID;
                                fb_share_handler(fbData);
                            }
                        }, {
                            scope: 'publish_stream,offline_access,user_about_me,email'
                        }
                    );
                }



                FB.api('/me/shopify_buttons:want?product={{willt_url}}',
                    'post',
                    function(response) {
                        if (!response || response.error) {
                            console.log('Error occured', response);
                        } else {
                            console.log('Post was successful! Action ID: ', response.id);
                        }
                    }
                );
            });
            
            button_insert.append(want);
            
            /**
             *  Add META tags to HEAD
             */
            var head = document.getElementsByTagName('head')[0];
            head.setAttribute('prefix', 'og: http://ogp.me/ns# shopify_buttons: http://ogp.me/ns/apps/shopify_buttons#');

            console.log('got meta tags', meta_tags); 
            
            // add all those meta tags
            for (i = 0; i < meta_tags.length; i++) {
                addEl(head, 'meta', meta_tags[i].property, meta_tags[i].content);
            }

            /**
             * call fb.init after everything has been added to page
             */
            FB.init({ 
                appId: '{{ FACEBOOK_APP_ID }}',
                cookie: true, 
                status: true,
                xfbml: true,
                oauth: true
            });
        }
    );
};

// let's get this party started 
//_willet_check_scripts();
var button_selector = '{{ app.button_selector }}';
var button_insert = $(button_selector);
var url         = location.href.split('/');
var l           = url.length;

if (button_insert &&  window.iframe_loaded == undefined) {
    window.iframe_loaded = "teh iframe haz been loaded";
    console.log('loading iframe');
    var surround    = document.createElement('div');
    var iframe      = document.createElement('iframe');
    surround.setAttribute('style', 'width: 200px;')
    iframe.setAttribute('allowtransparency', 'true');
    iframe.setAttribute('frameborder', '0');
    iframe.setAttribute('scrolling', 'no');
    iframe.setAttribute('style', 'width:100%; min-height:340px; display: block;');
    iframe.setAttribute('src', '{{ URL }}/b/shopify/load/iframe.html?store_url=http://' + Shopify.shop);

    button_insert.append(surround);
    $(surround).append(iframe);
    console.log('iframe inserted');
}

