// Curebit's Order code as of Jan 16, 2012
<!-- Begin Curebit integration code -->

<script type="text/javascript">
  (function(){
    var curebitSiteId = 'monahan-braun';
    var curebitJsUrl = 'https://www.curebit.com/public/' + curebitSiteId + '/purchases/create_shopify.js';
    var curebitVersion = '0.2';
    var curebitOrderNumber = "{{ order_number }}";


    var curebitI = 0;
    var curebitItems = '';
    {% for line in line_items %}
      curebitItems += 'purchase[items_attributes][' + curebitI + '][product_id]=' + encodeURIComponent('{{ line.sku }}') + '&';
      curebitItems += 'purchase[items_attributes][' + curebitI + '][price]=' + encodeURIComponent('{{ line.price | money_without_currency }}') + '&';
      curebitItems += 'purchase[items_attributes][' + curebitI + '][quantity]=' + encodeURIComponent('{{ line.quantity }}') + '&';
      curebitI++;
    {% endfor %}

    var curebitJsSrc = curebitJsUrl +
                '?v=' + encodeURIComponent(curebitVersion) +
                '&purchase[order_number]=' + encodeURIComponent(curebitOrderNumber) +
                '&purchase[subtotal]=' + encodeURIComponent('{{subtotal_price | money_without_currency }}') +
                '&purchase[order_date]=' + encodeURIComponent('{{created_at}}') +
                '&purchase[customer_email]=' + encodeURIComponent('{{ customer.email }}') +
                '&' + curebitItems;

    var curebitHeadID = document.getElementsByTagName("head")[0];
    var curebitNewScript = document.createElement('script');
    curebitNewScript.type = 'text/javascript';
    curebitNewScript.src = curebitJsSrc;
    curebitHeadID.appendChild(curebitNewScript);
  })();

</script>
<script type="text/javascript" src="https://www.curebit.com/javascripts/api/all-0.2.js"></script>
<script>
  (function(){
    var curebitSiteId = 'monahan-braun';
    curebit.init({site_id: curebitSiteId});
    var base_url = '{{ shop.url }}';

    var products = [];
    {% for line in line_items %}
      var product_id = '{% if line.sku != "" %}{{ line.sku }}{% else %}{{ line.product.id }}{% endif %}';
      if (product_id != '') {
        products.push({
          url:	base_url + '{{ line.product.url }}', /*REQUIRED VARIABLE */
            image_url: '{{ line.product.featured_image |  product_img_url}}', /* REQUIRED VARIABLE */
            title:	'{{ line.title }}', /* REQUIRED VARIABLE */
            product_id: product_id,//'{{ line.sku }}', /* REQUIRED VARIABLE */
            price:	'{{ line.price | money_without_currency }}' /* OPTIONAL VARIABLE */
        });
      }
    {% endfor %}
    curebit.register_products(products);
  })();
</script>
<!-- End Curebit integration code -->

