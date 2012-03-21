<div class="_willet_sibt" 
     data-sibtversion="11"
     data-storeurl="http://ohai.ca" data-store="Brian's Site" 
     data-productname="Brian's Famous Toxic Cooking"
     data-productpic="http://ohai.ca/death.jpg" data-price="19.00">
</div>
<script type="text/javascript">/*<![CDATA[*//*---->*/;!function (d, st) {
    /* super Willet JS tag mod; gist:1925519 */ "use strict";
    try {
        var jse = d.getElementsByTagName(st)[0], jsa = d.createElement(st);
        jsa.src = '{{ URL }}{% url SIBTServeScript %}' + 
            '?url=' + encodeURIComponent(window.location.href); // required
        jse.parentNode.insertBefore(jsa, jse);
    } catch (e) {}
}(document, 'script');/*--*//*]]>*/</script>
