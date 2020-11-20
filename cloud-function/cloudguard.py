import json
import sys
import os
import requests
from urllib.parse import urlparse, urljoin
from requests import ConnectionError, auth

class CloudGuardAPI:
    def __init__(self, api_key_id=None, api_secret=None, api_address='https://api.dome9.com', api_version='v2'):
        if api_key_id is None:
            self.api_key_id = os.getenv('CHKP_CLOUDGUARD_ID', None)
        else:
            self.api_key_id = api_key_id

        if api_secret is None:
            self.api_secret = os.getenv('CHKP_CLOUDGUARD_SECRET', None)
        else:
            self.api_secret = api_secret
        
        if self.api_secret is None or self.api_key_id is None:
            raise Exception(f"CHKP_CLOUDGUARD_ID and CHKP_CLOUDGUARD_SECRET environment variables are required")

        self.api_address = api_address
        self.api_version = f"/{api_version}/"
        self.base_address = self.api_address + self.api_version
        self.client_auth = auth.HTTPBasicAuth(
            self.api_key_id, self.api_secret)
        self.rest_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json'}
        if not self.api_key_id or not self.api_secret:
            raise Exception(
                'Cannot create api client instance without keyID and secret!')

    def get(self, route, payload=None):
        return self.request('get', route, payload)

    def post(self, route, payload=None):
        return self.request('post', route, payload)

    def patch(self, route, payload=None):
        return self.request('patch', route, payload)

    def put(self, route, payload=None):
        return self.request('put', route, payload)

    def delete(self, route, payload=None):
        return self.request('delete', route, payload)

    def request(self, method, route, payload=None, isV2=True):
        res = None
        url = None
        try:
            url = urljoin(self.base_address, route)
            if method == 'get':
                res = requests.get(
                    url=url, params=payload, headers=self.rest_headers, auth=self.client_auth)

            elif method == 'post':
                res = requests.post(
                    url=url, data=payload, headers=self.rest_headers, auth=self.client_auth)

            elif method == 'patch':
                res = requests.patch(
                    url=url, json=payload, headers=self.rest_headers, auth=self.client_auth)

            elif method == 'put':
                res = requests.put(
                    url=url, data=payload, headers=self.rest_headers, auth=self.client_auth)

            elif method == 'delete':
                res = requests.delete(
                    url=url, params=payload, headers=self.rest_headers, auth=self.client_auth)

        except requests.ConnectionError as ex:
            raise ConnectionError(url, ex)

        json_object = None
        err = None

        if res.status_code in range(200, 299):
            try:
                if res.content:
                    json_object = res.json()

            except Exception as ex:
                err = {
                    'code': res.status_code,
                    'message': str(ex),
                    'content': res.content
                }
        else:
            err = {
                'code': res.status_code,
                'message': res.reason,
                'content': res.content
            }

        if err:
            raise Exception(err)
        return json_object
