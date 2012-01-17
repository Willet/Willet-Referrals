&lt;!-- Begin Willet integration code --&gt;

&lt;script type="text/javascript"&gt;
  (function()&#123;
    var jsUrl   = '{{URL}}/o/shopify/create.js?client_uuid={{client_uuid}}';
    var i       = 0;
    var items   = '';
    &#123;% for line in line_items %&#125;
      items += 'item' + i + '=' + encodeURIComponent('&#123;&#123; line.product.id &#125;&#125;') + '&';
      i++;
    &#123;% endfor %&#125;

    var jsSrc = jsUrl +
                '&order_id=' + encodeURIComponent('&#123;&#123; order_id &#125;&#125;') +
                '&order_num='+ encodeURIComponent('&#123;&#123; order_number &#125;&#125;') +
                '&subtotal=' + encodeURIComponent('&#123;&#123; subtotal_price | money_without_currency &#125;&#125;') +
                '&ref_site=' + encodeURIComponent('&#123;&#123; referring_site &#125;&#125;') +
                '&email='    + encodeURIComponent('&#123;&#123; customer.email &#125;&#125;') +
                '&name='     + encodeURIComponent('&#123;&#123; customer.name &#125;&#125;') +
                '&marketing='+ encodeURIComponent('&#123;&#123; customer.accepts_marketing &#125;&#125;') +
                '&num_items='+ i +
                '&'          + items;

    var script  = document.createElement('script');
    script.type = 'text/javascript';
    script.src  = jsSrc;
    document.getElementsByTagName("head")[0].appendChild(script);
  &#125;)();

&lt;/script&gt;

&lt;!-- End Willet integration code --&gt;
