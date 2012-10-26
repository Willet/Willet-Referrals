{% extends '../../plugin/js/jquery.colorbox.js' %}

{% block js_includes %}

{% endblock %}

{%block js_analytics %}
    publicMethod.topRightClose = function( ) {
        publicMethod.storeAnalytics( publicMethod.closeState );
        publicMethod.close();
    };

    publicMethod.overlayClose = function( ) {
        publicMethod.storeAnalytics( "Overlay Cancelled" );
        publicMethod.close();
    };

    publicMethod.storeAnalytics = function(message) {
        if (_willet && _willet.mediator) {
            _willet.mediator.fire('storeAnalytics', message);
        }
    };

    publicMethod.closeState = "Overlay Closed";
{% endblock %}
