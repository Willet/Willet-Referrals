{% extends '../../../plugin/templates/js/jquery.colorbox.js' %}

{% block js_includes %}{% endblock %}

{%block js_analytics %}
    publicMethod.topRightClose = function( ) {
        publicMethod.close();
    };

    publicMethod.overlayClose = function () {
        publicMethod.close();
    };

    publicMethod.storeAnalytics = function (message) { };

    publicMethod.closeState = "";
{% endblock %}