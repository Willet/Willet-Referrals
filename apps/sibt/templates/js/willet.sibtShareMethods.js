var _willet = _willet || {};  // ensure namespace is there

// SIBT Methods to Post [vote] On Wall and Share With Selected Friends.
// requires server-side template vars:
// - FACEBOOK_APP_ID
// - URL
_willet.sibtShareMethods = (function (me) {
    var wm = _willet.mediator || {};

    me.init = me.init || function () {
        // load the "FB" object into DOM.
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
    };

    me.postOnWall = me.postOnWall || function (params) {
        try { // detect adblock
            FB.ui({ method: 'feed',
                   display: 'popup',
                   link: params.link,
                   picture: params.image,
                   name: params.title,
                   caption: params.caption,
                   description: params.description,
                   redirect_uri: params.redirect});
        } catch (e) {
            wm.fire('log', 'FB not loaded (adblock? remember to run init() first.)');
        }
        wm.fire('storeAnalytics', 'SIBTNoConnectFBDialog');
    };

    // set up your module hooks
    if (_willet.mediator) {
        _willet.mediator.on('customEvent', me.customEvent, defaultParams);
    }

    return me;
} (_willet.sibtShareMethods || {}));