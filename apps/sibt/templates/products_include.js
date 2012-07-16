/* generated products JS array */
var products = [{% for product in products %}
    {
        'uuid': '{{ product.uuid }}',
        'shopify_id': '{{ product.shopify_id|default:"0" }}',
        'title': '{{ product.title|striptags|escape|default:"(no name)" }}',
        'description': '{{ product.description|striptags|escape|default:"(no description)" }}',
        'image': '{{ product.images.0|default:"/static/imgs/noimage-willet.png" }}'
    }
    {% if not forloop.last %},{% endif %}
{% endfor %}];
/* end generated products JS array */