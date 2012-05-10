{% extends '../../../plugin/templates/js/jquery.colorbox.js' %}

{% block js_includes %}

{% endblock %}

{%block js_analytics %}
    publicMethod.topRightClose = function( ) {
        publicMethod.storeAnalytics( publicMethod.closeState );
        publicMethod.close();
    };

    publicMethod.overlayClose = function( ) {
        publicMethod.storeAnalytics( "SIBTOverlayCancelled" );
        publicMethod.close();
    };

    publicMethod.storeAnalytics = function(message) {
        if (_willet && _willet.Mediator) {
            _willet.Mediator.fire('storeAnalytics', message);
        }
    };

    publicMethod.closeState = "SIBTAskIframeCancelled";
{% endblock %}
