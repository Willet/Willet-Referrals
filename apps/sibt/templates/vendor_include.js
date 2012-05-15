<div class="_vendor_sibt"
     data-sibtversion="{{ sibt_version }}"
     data-client_uuid="{{ client.uuid }}"></div>
<script type="text/javascript">/*<![CDATA[*//*---->*/
    !function (d, st) {
        "use strict";
        try {
            var jse = d.getElementsByTagName(st)[0],
                jsa = d.createElement(st);
            jsa.src = '{{ URL }}{% url SIBTServeScript %}' +
                      '?url=' + encodeURIComponent(window.location.href);
            jse.parentNode.insertBefore(jsa, jse);
        } catch (e) {}
    }(document, 'script');
/*--*//*]]>*/</script>