var _willet = _willet || {};  // ensure namespace is there

// SIBT Methods to Post [vote] On Wall and Share With Selected Friends.
// requires server-side template vars:
// - FACEBOOK_APP_ID
// - URL
_willet.sibtShareMethods = (function (me) {
    var wm = _willet.mediator || {};

    me.init = me.init || function () {
        // load the "FB" object into DOM.
        if (!window.FB) {
            window.fbAsyncInit = function() {
                FB.init({
                    appId : '{{ FACEBOOK_APP_ID }}', // App ID
                    channelUrl : '{{ URL }}/static/plugin/html/FBChannel.html', // Channel File
                    status: true, // check login status
                    cookie: true, // enable cookies to allow the server to access the session
                    oauth : true, // enable OAuth 2.0
                    xfbml : true  // parse XFBML
                });
            };

            (function(d, s, id) {
                var js, fjs = d.getElementsByTagName(s)[0];
                if (d.getElementById(id)) {return;}
                js = d.createElement(s);
                js.id = id;
                js.async = true;
                js.src = "https://connect.facebook.net/en_US/all.js#xfbml=1";
                fjs.parentNode.insertBefore(js, fjs);
            }(document, 'script', 'facebook-jssdk'));
        }
    };

    me.postOnWall = me.postOnWall || function (params) {
        // post something to a fbloggedin user's wall.
        // see simple code below to check what the params object requires.
        try { // detect adblock
            FB.ui({method: 'feed',
                   name: params.title || '(no title)',
                   link: params.link || window.location.href,
                   picture: params.image || '{{ URL }}/static/imgs/noimage-willet.png',

                   display: params.display || 'popup',  // 'iframe'
                   caption: params.caption || '(no caption)',
                   description: params.description || '(no description)',
                   redirect_uri: params.redirect || window.location.href});
        } catch (e) {
            wm.fire('log', 'FB not loaded (adblock? remember to run init() first.)');
        }
        wm.fire('storeAnalytics', 'SIBTNoConnectFBDialog');
    };

    me.sendToFriends = me.sendToFriends || function (params) {
        // post something to several fbFriends' walls.
        // see simple code below to check what the params object requires.
        try { // detect adblock
            FB.ui({method: 'send',
                   name: params.title || '(no title)',
                   link: params.link || window.location.href,
                   picture: params.image || '{{ URL }}/static/imgs/noimage-willet.png',

                   display: params.display || 'popup',  // 'iframe'
                   caption: params.caption || '(no caption)',
                   description: params.description || '(no description)',
                   redirect_uri: params.redirect || window.location.href});
        } catch (e) {
            wm.fire('log', 'FB not loaded (adblock? remember to run init() first.)');
        }
        wm.fire('storeAnalytics', 'SIBTNoConnectFBDialog');
    };

    // set up your module hooks
    if (_willet.mediator) {
        _willet.mediator.on('scriptComplete', me.init);
        _willet.mediator.on('fbInit', me.init);
        _willet.mediator.on('postOnWall', me.postOnWall);
        _willet.mediator.on('sendToFriends', me.sendToFriends);
    }

    return me;
} (_willet.sibtShareMethods || {}));