import time
import hashlib
import hmac
import uuid
import sys
import ssl
import certifi
import json
import urllib.request
from urllib.parse import urlencode


class PostOpen:

    BTCUSD_ENDPOINT = 'https://www.bitstamp.net/api/v2/open_orders/all/'

    def __init__(self, apikeyfile):

        with open(apikeyfile, 'r') as apikeyfile:
            self.apikey = json.load(apikeyfile)

    def post_get_open(self):

        api_key = self.apikey['key']

        timestamp = str(int(round(time.time() * 1000)))
        nonce = str(uuid.uuid4())
        content_type = 'application/x-www-form-urlencoded'
        payload = {
            'key': api_key,
            'nonce': nonce,
        }

        payload_str = urlencode(payload)

        message = 'BITSTAMP'+ ' ' + api_key + \
                  'POST' + \
                  self.BTCUSD_ENDPOINT.replace('https://', '') + \
                  '' + \
                  content_type + \
                  nonce + \
                  timestamp + \
                  'v2' + \
                  payload_str
        message = message.encode('utf-8')

        api_secret = self.apikey['secret'].encode('utf-8')

        signature = hmac.new(api_secret, msg=message, digestmod=hashlib.sha256).hexdigest().upper()
        
        headers = {
            'X-Auth': 'BITSTAMP' + ' ' + api_key,
            'X-Auth-Signature': signature,
            'X-Auth-Nonce': nonce,
            'X-Auth-Timestamp': timestamp,
            'X-Auth-Version': 'v2',
            'Content-Type': content_type
        }

        #print('payload = %s' % payload_str)

        api_request = urllib.request.Request(
            self.BTCUSD_ENDPOINT,
            headers=headers,
            data=payload_str.encode('utf-8')
        );

        with urllib.request.urlopen(api_request, context=ssl.create_default_context(cafile=certifi.where())) as api_call:
            status_code = api_call.getcode()
            api_result = api_call.read()
            headers = api_call.info()            
            
            if not status_code == 200:
                print(r)
                print(api_result)
                raise Exception('Status code not 200')

        
            string_to_sign = (nonce + timestamp + headers.get('Content-Type')).encode('utf-8') + api_result
            signature_check = hmac.new(api_secret, msg=string_to_sign, digestmod=hashlib.sha256).hexdigest()

            if not headers.get('X-Server-Auth-Signature') == signature_check:
                raise Exception('Signatures do not match')

            print(api_result.decode())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            apikeyfile = sys.argv[1]
            po = PostOpen(apikeyfile)
            po.post_get_open()
            sys.exit(0)
        except Exception as e:
            print('Failed. '+repr(e))
    else:
        print('apikey file is required')
        sys.exit(1)
