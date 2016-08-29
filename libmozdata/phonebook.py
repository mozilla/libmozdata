# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import re
from connection import (Connection, Query)
from pprint import pprint
from . import config


class Phonebook(Connection):
    """Mozilla phonebook class
    """

    URL = config.get('Phonebook', 'URL', 'https://phonebook.mozilla.org')
    SEARCH_URL = URL + '/search.php'

    def __init__(self, query='*'):
        """Constructor

        Args:
            query (Optional[str]): the query to pass to phonebook
        """
        # TODO: fix credential problem
        super(Phonebook, self).__init__(Phonebook.URL)
        self.entries = {}
        self.exec_queries(Query(Phonebook.SEARCH_URL, params={'query': query, 'format': 'fligtar'}, handler=self.default_handler, handlerdata=self.entries))

    def get(self):
        """Get the phonebook entries (waits for all data)

        Returns:
            dict: the entries
        """
        self.wait()
        return self.entries

    def get_auth(self):
        if self.credentials:
            ldap = self.credentials['ldap']
            return (ldap['username'], ldap['password'])
        return None

    def default_handler(self, json, data):
        """Handler to use with the data retrieved from phonebook

        Args:
            json (dict): json data retrieved from phonebook
            data (dict): the container which will receive the data
        """
        mail_pattern = re.compile('mail=([^,]*)')
        for k, v in json.items():
            _manager = None
            if 'manager' in v:
                manager = v['manager']
                if manager and 'dn' in manager:
                    dn = manager['dn']
                    m = mail_pattern.match(dn)
                    if m:
                        _manager = m.group(1)
                        if not _manager:
                            _manager = None
                    else:
                        _manager = None

            bz_email = v['bugzillaEmail']
            if not bz_email:
                bz_email = k

            data[k] = {'name': v['name'],
                       'bz_email': bz_email,
                       'manager': _manager}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mozilla\'s phonebook')
    parser.add_argument('-q', '--query', action='store', default='*', help='query to pass to phonebook, by default \'*\'')

    args = parser.parse_args()
    pprint(Phonebook(args.query).get())
