{% extends '../../../plugin/templates/js/jquery.colorbox.js' %}

{% block js_includes %}

{% endblock %}

{%block js_analytics %}
    publicMethod.topRightClose = function( ) {
        publicMethod.storeAnalytics( publicMethod.closeState );
        publicMethod.close();
    };

    publicMethod.overlayClose = function( ) {
        publicMethod.storeAnalytics( "WOSIBOverlayCancelled" );
        publicMethod.close();
    };

    publicMethod.storeAnalytics = function( message ) {
        var message = message;
        var iframe = document.createElement( 'iframe' );

        iframe.style.display = 'none';
        iframe.src = "{{ URL }}{% url TrackSIBTShowAction %}?evnt=" + message +
                    "&app_uuid={{app_uuid}}" +
                    "&user_uuid={{user_uuid}}" +
                    "&instance_uuid={{instance_uuid}}" +
                    "&refer_url={{refer_url}}";

        document.body.appendChild( iframe );
    };

    publicMethod.closeState = "WOSIBAskIframeCancelled";
{% endblock %}
