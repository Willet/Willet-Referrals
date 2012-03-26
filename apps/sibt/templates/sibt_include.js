<div class="_willet_sibt" data-sibtversion="{{ sibt_version }}"></div>
<script type="text/javascript">/*<![CDATA[*//*---->*/;!function (d, st) {
    "use strict";
    try {
        var jse = d.getElementsByTagName(st)[0], jsa = d.createElement(st);
        jsa.src = '{{ URL }}{% url SIBTServeScript %}' + 
            '?url=' + encodeURIComponent(window.location.href); // required
        jse.parentNode.insertBefore(jsa, jse);
    } catch (e) {}
}(document, 'script');/*--*//*]]>*/</script>
