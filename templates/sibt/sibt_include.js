<div class="_willet_sibt"
     data-sibtversion="{{ sibt_version }}"
     data-app_uuid="{{ app.uuid }}"
     data-client_uuid="{{ client.uuid }}"
     data-title=" (name of the product) "
     data-description=" (product description) "
     data-images=" (optional: pictures of the product, separated by a comma) "
     data-image=" (optional: picture of the product) "
     data-tags=" (optional: tags for the product) "
     data-price="19.00">
</div>
<script type="text/javascript">/*<![CDATA[*//*---->*/;!function (d, st) {
    "use strict";
    try {
        var jse = d.getElementsByTagName(st)[0], jsa = d.createElement(st);
        jsa.src = '{{ URL }}{% url SIBTServeScript %}' +
            '?url=' + encodeURIComponent(window.location.href); // required
        jse.parentNode.insertBefore(jsa, jse);
    } catch (e) {}
}(document, 'script');/*--*//*]]>*/</script>
