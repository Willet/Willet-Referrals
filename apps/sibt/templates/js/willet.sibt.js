var _willet = _willet || {};  // ensure namespace is there

// module description comment
_willet.SIBT = (function (me) {
    me.$ = jQuery || {};

    // scrape the page for SIBT signature.
    me.getElements = me.getElements || function () {
        var $ = me.$;
        var elements = [],
            selectors = [
                '#mini_sibt_button', // SIBT for ShopConnection (SIBT Connection)
                '#_willet_shouldIBuyThisButton', // SIBT standalone (v2, v3, v10)
                '._willet_sibt', // SIBT-JS
                '#_willet_WOSIB_Button' // WOSIB mode
            ];
        for (var i = 0; i < selectors.length; i++) {
            var matches = $(selectors[i]);
            if (matches.length >= 1) {  // found
                elements.push(matches.eq(0));
            }
        }
        return elements;
    };

    me.init = me.init || function ($) {
        me.$ = $;

        var elements = me.getElements();
        if (elements) {
            // TODO
        }
    };

    // set up your module hooks
    if (_willet.Mediator) {
        _willet.Mediator.on('hasjQuery', me.init);
    }

    return me;
} (_willet.SIBT || {}));