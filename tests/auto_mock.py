import unittest
import os
import requests
import responses
import gzip
import pickle
import re
import hashlib
import logging
import sys
try:
    from urllib.parse import urlparse, parse_qsl
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse, parse_qsl
    from urllib2 import Request, HTTPError, urlopen

logger = logging.getLogger(__name__)


MOCKS_DIR = os.path.join(os.path.dirname(__file__), 'mocks')


class MockTestCase(unittest.TestCase):
    """
    Mock responses from any webserver (through requests)
    Register local responses when none are found
    """
    mock_urls = []

    def setUp(self):
        # Real requests session
        self.real_session = requests.Session()

        # Setup mock callbacks
        for mock_url in self.mock_urls:
            url_re = re.compile(r'^{}'.format(mock_url))
            responses.add_callback(
                responses.GET,
                url_re,
                callback=self.request_callback,
                content_type='application/json',
            )

    def request_callback(self, request):
        logger.debug('Mock request {} {}'.format(request.method, request.url))
        path = self.build_path(request.method, request.url)

        if os.path.exists(path):
            # Load local file
            logger.info('Using mock file {}'.format(path))
            with gzip.open(path, 'rb') as f:
                response = pickle.load(f)
        else:
            # Build from actual request
            logger.info('Building mock file {}'.format(path))
            response = self.real_request(request)

            # Save in local file for future use
            with gzip.open(path, 'wb') as f:
                # Use old pickle ascii protocol (default)
                # to be compatible with Python 2
                f.write(pickle.dumps(response, protocol=2))

        return (
            response['status'],
            response['headers'],
            response['body'],
        )

    def build_path(self, method, url):
        """
        Build a unique filename from method & url
        """
        # Build directory to request
        out = urlparse(url)
        parts = [
            '{}_{}'.format(out.scheme, out.hostname),
        ]
        parts += filter(None, out.path.split('/'))
        directory = os.path.join(MOCKS_DIR, *parts)

        # Build sorted query filename
        query = sorted(parse_qsl(out.query))
        query = ['{}={}'.format(k, v.replace('/', '_')) for k, v in query]
        query_str = '_'.join(query)

        # Use hashes to avoid too long names
        if len(query_str) > 150:
            query_str = '{}_{}'.format(query_str[0:100], hashlib.md5(query_str.encode('utf-8')).hexdigest())
        filename = '{}_{}.gz'.format(method, query_str)

        # Build directory
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except Exception as e:
                logger.error('Concurrency error when building directories: {}'.format(e))

        return os.path.join(directory, filename)

    def real_request(self, request):
        """
        Do a real request towards the target
        to build a mockup, using low level urllib
        Can't use requests: it's wrapped by unittest.mock
        """

        # No gzip !
        headers = dict([(k.lower(), v) for k, v in request.headers.items()])
        if 'accept-encoding' in headers:
            del headers['accept-encoding']

        # Method arg is not supported by Python 2
        if sys.version_info >= (3, 0):
            real_req = Request(request.url, request.body, headers=headers, method=request.method)
        else:
            real_req = Request(request.url, request.body, headers=headers)
        try:
            resp = urlopen(real_req)
        except HTTPError as e:
            logger.error('HTTP Error saved for {}: {}'.format(request.url, e))
            return {
                'status': e.code,
                'headers': {},
                'body': '',
            }

        return {
            'status': resp.code,
            # TODO: fix cookie usage bug
            # 'headers': dict(resp.getheaders()),
            'headers': {},
            'body': resp.read().decode('utf-8'),
        }
