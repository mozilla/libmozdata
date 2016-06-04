# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
from .connection import (Connection)
from . import config


class Bugzilla(Connection):
    """Connection to bugzilla.mozilla.org
    """

    URL = config.get('Bugzilla', 'URL', 'https://bugzilla.mozilla.org')
    API_URL = URL + '/rest/bug'
    TOKEN = config.get('Bugzilla', 'token', '')

    def __init__(self, bugids=None, include_fields='_default', bughandler=None, bugdata=None, historyhandler=None, historydata=None, commenthandler=None, commentdata=None, attachmenthandler=None, attachmentdata=None, queries=None):
        """Constructor

        Args:
            bugids (List[str]): list of bug ids or search query
            include_fields (List[str]): list of include fields
            bughandler (Optional[function]): the handler to use with each retrieved bug
            bugdata (Optional): the data to use with the bug handler
            historyhandler (Optional[function]): the handler to use with each retrieved bug history
            historydata (Optional): the data to use with the history handler
            commenthandler (Optional[function]): the handler to use with each retrieved bug comment
            commentdata (Optional): the data to use with the comment handler
            attachmenthandler (Optional[function]): the handler to use with each retrieved bug attachment
            attachmentdata (Optional): the data to use with the attachment handler
            queries (List[Query]): queries rather than single query
        """
        if queries:
            super(Bugzilla, self).__init__(Bugzilla.URL, queries=queries)
        else:
            super(Bugzilla, self).__init__(Bugzilla.URL)
            if isinstance(bugids, six.string_types):
                self.bugids = [bugids]
            elif isinstance(bugids, int):
                self.bugids = [str(bugids)]
            else:
                self.bugids = list(map(str, bugids))
            self.include_fields = include_fields
            self.bughandler = bughandler
            self.bugdata = bugdata
            self.historyhandler = historyhandler
            self.historydata = historydata
            self.commenthandler = commenthandler
            self.commentdata = commentdata
            self.attachmenthandler = attachmenthandler
            self.attachmentdata = attachmentdata
            self.bugs_results = []
            self.history_results = []
            self.comment_results = []
            self.attachment_results = []
            self.got_data = False

    def get_header(self):
        header = super(Bugzilla, self).get_header()
        header['X-Bugzilla-API-Key'] = self.get_apikey()
        return header

    def put(self, data):
        """Put some data in bugs

        Args:
            data (dict): a dictionnary
        """
        if self.bugids:
            if self.__is_bugid():
                ids = self.bugids
            else:
                ids = self.__get_bugs_list()

            url = Bugzilla.API_URL + '/'
            for _ids in Connection.chunks(ids):
                first_id = _ids[0]
                if len(_ids) >= 2:
                    data['ids'] = _ids[1:]
                elif 'ids' in data:
                    del data['ids']
                self.session.put(url + first_id, json=data)

    def get_data(self):
        """Collect the data
        """
        if not self.got_data:
            self.got_data = True
            if self.__is_bugid():
                if self.bughandler:
                    self.__get_bugs()
                if self.historyhandler:
                    self.__get_history()
                if self.commenthandler:
                    self.__get_comment()
                if self.attachmenthandler:
                    self.__get_attachment()
            elif self.bughandler:
                self.__get_bugs_for_history_comment()

        return self

    def wait(self):
        if self.queries:
            super(Bugzilla, self).wait()
        else:
            self.get_data()
            self.wait_bugs()
            for r in self.comment_results:
                r.result()
            for r in self.history_results:
                r.result()
            for r in self.attachment_results:
                r.result()

    def wait_bugs(self):
        """Just wait for bugs
        """
        for r in self.bugs_results:
            r.result()

    @staticmethod
    def follow_dup(bugids):
        """Follow the duplicated bugs

        Args:
            bugids (List[str]): list of bug ids

        Returns:
            dict: each bug in entry is mapped to the last bug in the duplicate chain (None if there's no dup and 'cycle' if a cycle is detected)
        """
        include_fields = ['id', 'resolution', 'dupe_of']
        dup = {}
        _set = set()
        for bugid in bugids:
            dup[str(bugid)] = None

        def bughandler(bug, data):
            if bug['resolution'] == 'DUPLICATE':
                dupeofid = str(bug['dupe_of'])
                dup[str(bug['id'])] = [dupeofid]
                _set.add(dupeofid)

        bz = Bugzilla(bugids=bugids, include_fields=include_fields, bughandler=bughandler).get_data()
        bz.wait_bugs()

        def bughandler2(bug, data):
            if bug['resolution'] == 'DUPLICATE':
                bugid = str(bug['id'])
                for _id in dup.keys():
                    dupid = dup[_id]
                    if dupid and dupid[-1] == bugid:
                        dupeofid = str(bug['dupe_of'])
                        if dupeofid == _id or dupeofid in dupid:
                            # avoid infinite loop if any
                            dup[_id].append('cycle')
                        else:
                            dup[_id].append(dupeofid)
                            _set.add(dupeofid)

        bz.bughandler = bughandler2

        while _set:
            bz.bugids = list(_set)
            _set.clear()
            bz.got_data = False
            bz.get_data().wait_bugs()

        for k in dup.keys():
            v = dup[k]
            dup[k] = v[-1] if v else None

        return dup

    def __is_bugid(self):
        """Check if the first bugid is a bug id or a search query

        Returns:
            (bool): True if the first bugid is a bug id
        """
        if self.bugids:
            bugid = self.bugids[0]
            if bugid.isdigit():
                return True
        return False

    def __get_bugs_for_history_comment(self):
        """Get history and comment (if there are some handlers) after a search query
        """
        if self.historyhandler or self.commenthandler:
            bugids = []
            bughandler = self.bughandler
            bugdata = self.bugdata

            def __handler(bug, bd):
                bughandler(bug, bugdata)
                bd.append(bug['id'])

            self.bughandler = __handler
            self.bugdata = bugids

            self.__get_bugs_by_search()
            self.wait_bugs()

            self.bughandler = bughandler
            self.bugdata = bugdata

            self.bugids = bugids

            if self.historyhandler:
                self.history_results = []
                self.__get_history()
            if self.commenthandler:
                self.comment_results = []
                self.__get_comment()
            if self.attachmenthandler:
                self.attachment_results = []
                self.__get_attachment()
        else:
            self.__get_bugs_by_search()

    def __bugs_cb(self, sess, res):
        """Callback for bug query

        Args:
            sess: session
            res: result
        """
        if res.status_code == 200:
            for bug in res.json()['bugs']:
                self.bughandler(bug, self.bugdata)

    def __get_bugs(self):
        """Get the bugs
        """
        for bugids in Connection.chunks(self.bugids):
            self.bugs_results.append(self.session.get(Bugzilla.API_URL,
                                                      params={'id': ','.join(bugids),
                                                              'include_fields': self.include_fields},
                                                      verify=True,
                                                      timeout=self.TIMEOUT,
                                                      background_callback=self.__bugs_cb))

    def __get_bugs_by_search(self):
        """Get the bugs in making a search query
        """
        url = Bugzilla.API_URL + '?'
        for query in self.bugids:
            self.bugs_results.append(self.session.get(url + query,
                                                      verify=True,
                                                      timeout=self.TIMEOUT,
                                                      background_callback=self.__bugs_cb))

    def __get_bugs_list(self):
        """Get the bugs list corresponding to the search query
        """
        _list = set()

        def cb(sess, res):
            if res.status_code == 200:
                for bug in res.json()['bugs']:
                    _list.add(bug['id'])

        results = []
        url = Bugzilla.API_URL + '?'
        for query in self.bugids:
            results.append(self.session.get(url + query,
                                            verify=True,
                                            timeout=self.TIMEOUT,
                                            background_callback=cb))

        for r in results():
            r.result()

        return list(_list)

    def __history_cb(self, sess, res):
        """Callback for bug history

        Args:
            sess: session
            res: result
        """
        if res.status_code == 200:
            json = res.json()
            if 'bugs' in json and json['bugs']:
                history = json['bugs'][0]
                self.historyhandler(history, self.historydata)

    def __get_history(self):
        """Get the bug history
        """
        url = Bugzilla.API_URL + '/%s/history'
        for bugid in self.bugids:
            self.history_results.append(self.session.get(url % bugid,
                                                         verify=True,
                                                         timeout=self.TIMEOUT,
                                                         background_callback=self.__history_cb))

    def __comment_cb(self, sess, res):
        """Callback for bug comment

        Args:
            sess: session
            res: result
        """
        if res.status_code == 200:
            json = res.json()
            if 'bugs' in json:
                bugs = json['bugs']
                if bugs:
                    for key in bugs.keys():
                        if isinstance(key, six.string_types) and key.isdigit():
                            comments = bugs[key]
                            self.commenthandler(comments, key, self.commentdata)
                            break

    def __get_comment(self):
        """Get the bug comment
        """
        url = Bugzilla.API_URL + '/%s/comment'
        for bugid in self.bugids:
            self.comment_results.append(self.session.get(url % bugid,
                                                         verify=True,
                                                         timeout=self.TIMEOUT,
                                                         background_callback=self.__comment_cb))

    def __attachment_cb(self, sess, res):
        """Callback for bug attachment

        Args:
            sess: session
            res: result
        """
        if res.status_code == 200:
            json = res.json()
            if 'bugs' in json:
                bugs = json['bugs']
                if bugs:
                    for key in bugs.keys():
                        if isinstance(key, six.string_types) and key.isdigit():
                            attachments = bugs[key]
                            self.attachmenthandler(attachments, key, self.attachmentdata)
                            break

    def __get_attachment(self):
        """Get the bug attachment
        """
        url = Bugzilla.API_URL + '/%s/attachment'
        req_params = {'api_key': self.get_apikey()}
        for bugid in self.bugids:
            self.attachment_results.append(self.session.get(url % bugid,
                                                            verify=True,
                                                            params=req_params,
                                                            timeout=self.TIMEOUT,
                                                            background_callback=self.__attachment_cb))
