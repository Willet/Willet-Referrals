/**
 * Buttons JS
 */



/**
 * quick helper function to add scripts to dom
 */
var loadRemoteScript = function(scipt) {
    var dom_el = document.createElement('script'); 
    dom_el.src = script;
    dom_el.type = 'text/javascript'; 
    document.getElementsByTagName('head')[0].appendChild(dom_el); 
    return dom_el;
}

/**
 * Used to add meta tags to head
 */
var addEl = function(head, el, property, content) {
    var dom_el = document.createElement(el);
    dom_el.property = property;
    dom_el.content = content;
    head.appendChild(dom_el);
}

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
            if(typeof unsafeWindow.jQuery == 'undefined') {   
                return false;
            } else {
                return true;
            }
        }, 'callback': function() {
            $ = unsafeWindow.jQuery;
        }
    }, {
        'name': 'Facebook',
        'url': 'http://connect.facebook.net/en_US/all.js',
        'dom_el': null,
        'loaded': false,
        'test': function() {
            if (typeof unsafeWindow.FB == 'undefined') {
                console.log('FB not loaded yet');
                return false;
            } else {
                return true;
            }
        }, 'callback': function() {
            FB = unsafeWindow.FB;
        }
    }
];



/**
 * checkScripts checks the scripts var and uses
 * the defined `test` and `callack` methods to tell
 * when a script has been loaded and is ready to be
 * used
 */
var checkScripts = function() {
    var all_loaded = true;

    for (i = 0; i < scripts.length; i++) {
        var row  = scripts[i];
        if (row.dom_el == null) {
            // insert the script into the dom
            row.dom_el = loadremoteScript(row.url);
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
        run();
    } else {
        window.setTimeout(checkScripts,100);
    }
}

/**
 * body of code to run when all scripts have been injected
 */
var run = function() {
    // HERE IS OUR REAL CODE
    

    // get the button where we are going to insert
    var button_selector = '{{ app.button_selector }}';
    var button_insert = $(button_selector);
    
    // try to get the json for this location
    var here = window.location;
    here = here + '.json';

    $.getJSON (
        here,
        function(data) {
            // callback function
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
            * Insert Facebook DOM El
            */
            var fb_dom_el = document.createElement('fb:add-to-timeline');
            button_insert.append(fb_dom_el); 

            /**
             *  Add META tags to HEAD
             */
            var head = document.getElementsByTagName('head')[0];
            head.setAttribute('prefix', 'og: http://ogp.me/ns# shopify_buttons:http://ogp.me/ns/apps/shopify_buttons#')

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
}

// let's get this party started 
checkScripts();

