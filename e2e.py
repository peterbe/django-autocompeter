import time

import requests


DEFAULT_URL = 'http://localhost:8000/v1'


class Test:
    def __init__(self, auth_key, domain, base_url=DEFAULT_URL):
        self.auth_key = auth_key
        self.domain = domain
        self.base_url = base_url

    def _post(self, _url='', **data):
        _error = data.pop('_error', 201)
        _json = data.pop('_json', False)
        kwargs = {
            'headers': {
                'Auth-Key': self.auth_key,
            }
        }
        if _json:
            kwargs['json'] = data
        else:
            kwargs['data'] = data
        response = requests.post(
            self.base_url + _url,
            **kwargs
        )
        assert response.status_code == _error, response.status_code
        return response.json()

    def _get(self, _url='', **params):
        _secure = params.pop('_secure', False)
        response = requests.get(
            self.base_url + _url,
            params=params,
            headers=_secure and {
                'Auth-Key': self.auth_key,
            } or None
        )
        assert response.status_code == 200, response.status_code
        return response.json()

    def _stats(self):
        return self._get('/stats', _secure=True)

    def _bulk(self, documents):
        return self._post('/bulk', _json=True, documents=documents)

    def _delete(self, url, **data):
        _error = data.pop('_error', 200)
        kwargs = {
            'headers': {
                'Auth-Key': self.auth_key,
            }
        }
        response = requests.delete(
            self.base_url + '?url={}'.format(url),
            **kwargs
        )
        assert response.status_code == _error, response.status_code
        return response.json()

    def run(self):
        self._post('/flush', _error=200)
        # Create a bunch of docs
        self._post(
            title='Xylophone Meeting',
            url='http://example.com/meeting/document',
        )
        time.sleep(1)
        stats = self._stats()
        assert stats['documents'] >= 1, stats['documents']
        results = self._get(q='x', d=self.domain)
        exp = ['http://example.com/meeting/document', 'Xylophone Meeting']
        assert exp in results['results'], results['results']
        assert results['terms'] == ['x'], results['terms']

        # Change title
        self._post(
            title='Xylophone Concert',
            url='http://example.com/meeting/document',
        )
        time.sleep(1)
        results = self._get(q='x', d=self.domain)
        exp = ['http://example.com/meeting/document', 'Xylophone Concert']
        assert exp in results['results'], results['results']

        # Bulk create
        documents = []
        documents.append({
            'title': 'Monday Meeting One',
            'url': 'http://example.com/one',
            'popularity': 1,
        })
        documents.append({
            'title': 'Monday Meeting Two',
            'url': 'http://example.com/Two',
            'popularity': 2,
        })
        result = self._bulk(documents)
        assert result['count'] == 2, result['count']
        time.sleep(1)
        results = self._get(q='monday meet', d=self.domain)
        exp = [
            ['http://example.com/Two', 'Monday Meeting Two'],
            ['http://example.com/one', 'Monday Meeting One'],
        ]
        assert exp == results['results'], results['results']

        self._delete(
            url='http://example.com/meeting/document',
        )
        time.sleep(1)

        # Groups
        self._post(
            title='Zebra Public',
            url='http://example.com/zebra/public',
        )
        self._post(
            title='Zebra Contributor',
            url='http://example.com/zebra/contributor',
            group='contributor'
        )
        self._post(
            title='Zebra Private',
            url='http://example.com/zebra/private',
            group='private'
        )
        time.sleep(1)
        results = self._get(q='zeb', d=self.domain)

        public = ['http://example.com/zebra/public', 'Zebra Public']
        contrib = ['http://example.com/zebra/contributor', 'Zebra Contributor']
        private = ['http://example.com/zebra/private', 'Zebra Private']
        assert public in results['results'], results['results']
        assert contrib not in results['results'], results['results']
        assert private not in results['results'], results['results']

        results = self._get(q='zeb', d=self.domain, g='contributor')
        assert public in results['results'], results['results']
        assert contrib in results['results'], results['results']
        assert private not in results['results'], results['results']

        results = self._get(q='zeb', d=self.domain, g='contributor,private')
        assert public in results['results'], results['results']
        assert contrib in results['results'], results['results']
        assert private in results['results'], results['results']

        # Things that should not work
        self._post(
            title='Zebra Public',
            _error=400
        )
        self._post(
            url='http://example.com/zebra/public',
            _error=400
        )
        self._delete(
            url='',
            _error=400
        )
        self._post(
            '/bulk',
            _json=True,
            _error=400
        )


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'auth_key',
        help='Auth Key',
    )
    parser.add_argument(
        'domain',
        help='Domain',
    )
    parser.add_argument(
        'base_url',
        help='Base URL (default: {})'.format(DEFAULT_URL),
        default=DEFAULT_URL,
        nargs='?'
    )
    args = parser.parse_args()
    Test(
        args.auth_key,
        args.domain,
        args.base_url,
    ).run()


if __name__ == '__main__':
    import sys
    sys.exit(main())
