import httplib2
import hashlib
import json

# Shopify API Calls -------------------------------------------------------
def call_api(verb, call, store_url="http://farrell-hagenes-and-mayer1876.myshopify.com", 
            api_key="567c61ffee5fc7eec076097918d3d6ca",
            api_secret="ceabbcb6011cd59e72ab7389d306b817",
            store_token="b82eb22f39122957ff2fdd11ba8f6a4e",
            payload=None, suppress_errors=False, prefix='admin/'):
    """ Calls Shopify API 

    Inputs:
        verb - <String> one of GET, POST, PUT, DELETE
        call - <String> api call (e.g. 'themes.json')
            prefix - defaults to to 'admin/'.
        payload - <Object> Data to send with request
        suppress_errors - <Boolean> Quietly proceed if call errors
                          NOTE: Only use this if you expect errors from this call
                                No error event is logged, so debugging will be difficult
    """
    if verb not in ['GET', 'get', 'POST', 'post',
                'PUT', 'put', 'DELETE', 'delete']:
        raise ValueError('verb must be one of GET, POST, PUT, DELETE')

    url      = '%s/%s%s' % (store_url, prefix, call)
    username = api_key
    password = hashlib.md5(api_secret + store_token).hexdigest()
    header   = {'content-type':'application/json'}
    h        = httplib2.Http()

    # Auth the http lib
    h.add_credentials(username, password)

    # Make request
    resp, content = h.request(
            url,
            verb,
            body    = json.dumps(payload),
            headers = header
        )

    data = {}
    error = False

    if "application/json" in resp['content-type']:
        if int(resp.status) is 200 and content.strip() == "":
            return True #Some responses don't return JSON

        response_actions = {
            200: lambda x: json.loads(x),
            201: lambda x: json.loads(x)
        }

        try:
            data = response_actions.get(int(resp.status))(content)
            error = (True if data.get("errors") else False)
        except (TypeError, ValueError):
            # Key Didn't exist, or couldn't parse JSON
            error = True
    else:
        error = True

    if not error or suppress_errors:
        if error and suppress_errors:
            logging.error("API Request Failed: %s %s\n" \
                          "URL: %s\n" \
                          "PAYLOAD: %s\n" \
                          "CONTENT: %s\n" \
                          % (resp.status, resp.reason, url, payload, content))
        return data
    else:
        print 'APPLICATION API REQUEST FAILED<br />Request: %s %s<br />Status: %s %s<br />Store: %s<br />Response: %s' % (
                verb,
                call,
                resp.status,
                resp.reason,
                store_url,
                data if data else content
            )
        print "URL: %s, PAYLOAD: %s, CONTENT: %s" % (url, payload, content)
