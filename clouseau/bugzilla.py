# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from connection import (Connection, Query)


class Bugzilla(Connection):
    """Connection to bugzilla.mozilla.org
    """

    URL = 'https://bugzilla.mozilla.org'
    # URL = 'https://bugzilla-dev.allizom.org'
    API_URL = URL + '/rest/bug'

    def __init__(self, bugids=None, credentials=None, bughandler=None, bugdata=None, historyhandler=None, historydata=None, commenthandler=None, commentdata=None, attachmenthandler=None, attachmentdata=None, queries=None):
        """Constructor

        Args:
            bugids (List[str]): list of bug ids or search query
            credentials (Optional[dict]): credentials to use with bugzilla
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
            super(Bugzilla, self).__init__(Bugzilla.URL, queries=queries, credentials=credentials)
        else:
            super(Bugzilla, self).__init__(Bugzilla.URL, credentials=credentials)
            if isinstance(bugids, basestring):
                self.bugids = [bugids]
            elif isinstance(bugids, int):
                self.bugids = [str(bugids)]
            else:
                self.bugids = map(str, bugids)
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

            if 'api_key' not in data:
                data['api_key'] = self.get_apikey(Bugzilla.URL)

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
        api_key = self.get_apikey(Bugzilla.URL)
        for bugids in Connection.chunks(self.bugids):
            self.bugs_results.append(self.session.get(Bugzilla.API_URL,
                                                      params={'api_key': api_key,
                                                              'id': ','.join(bugids)},
                                                      verify=True,
                                                      timeout=self.TIMEOUT,
                                                      background_callback=self.__bugs_cb))

    def __get_bugs_by_search(self):
        """Get the bugs in making a search query
        """
        api_key = self.get_apikey(Bugzilla.URL)
        url = Bugzilla.API_URL + '?'
        for query in self.bugids:
            self.bugs_results.append(self.session.get(url + query,
                                                      params={'api_key': api_key},
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

        api_key = self.get_apikey(Bugzilla.URL)
        results = []
        url = Bugzilla.API_URL + '?'
        for query in self.bugids:
            results.append(self.session.get(url + query,
                                            params={'api_key': api_key},
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
        req_params = {'api_key': self.get_apikey(Bugzilla.URL)}
        for bugid in self.bugids:
            self.history_results.append(self.session.get(url % bugid,
                                                         params=req_params,
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
                        if isinstance(key, basestring) and key.isdigit():
                            comments = bugs[key]
                            self.commenthandler(comments, key, self.commentdata)
                            break

    def __get_comment(self):
        """Get the bug comment
        """
        url = Bugzilla.API_URL + '/%s/comment'
        req_params = {'api_key': self.get_apikey(Bugzilla.URL)}
        for bugid in self.bugids:
            self.comment_results.append(self.session.get(url % bugid,
                                                         params=req_params,
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
                        if isinstance(key, basestring) and key.isdigit():
                            attachments = bugs[key]
                            self.attachmenthandler(attachments, key, self.attachmentdata)
                            break

    def __get_attachment(self):
        """Get the bug attachment
        """
        url = Bugzilla.API_URL + '/%s/attachment'
        req_params = {'api_key': self.get_apikey(Bugzilla.URL)}
        for bugid in self.bugids:
            self.attachment_results.append(self.session.get(url % bugid,
                                                            params=req_params,
                                                            timeout=self.TIMEOUT,
                                                            background_callback=self.__attachment_cb))
