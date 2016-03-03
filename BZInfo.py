# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import multiprocessing
from requests.adapters import HTTPAdapter
from requests_futures.sessions import FuturesSession
from pprint import pprint
import re
import utils

class BZInfo(object):

    BZ_URL = 'https://bugzilla.mozilla.org'
    API_URL = BZ_URL + '/rest/bug'
    TIMEOUT = 60
    MAX_RETRIES = 5
    MAX_WORKERS = multiprocessing.cpu_count()
    CHUNK_SIZE = 8
    
    def __init__(self, bugids, credentials = None):
        self.results = [ ]
        self.credentials = credentials
        self.bugids = map(str, bugids)
        self.info = { }
        for bugid in self.bugids:
            self.info[bugid] = { 'ownership': [],
                                 'reviewers': set(),
                                 'commenters': { },
                                 'authorized': False }
        self.session = FuturesSession(max_workers = self.MAX_WORKERS)
        self.session.mount(self.BZ_URL, HTTPAdapter(max_retries = self.MAX_RETRIES))
        self.reply_pattern = re.compile('^\(In reply to .* comment #([0-9]+)\)')
        self.dupbug_pattern = re.compile('\*\*\* Bug [0-9]+ has been marked as a duplicate of this bug. \*\*\*')
        self.review_pattern= re.compile('review\?\(([^\)]+)\)')
        self.needinfo_pattern= re.compile('needinfo\?\(([^\)]+)\)')
        self.feedback_pattern= re.compile('feedback\?\(([^\)]+)\)')
        self.__get_info()
        self.__analyze_history()
        self.__analyze_comment()

    def get(self):
        for r in self.results:
            r.result()
        return self.info

    def get_best_collaborator(self):
        # a collaboration between A & B is when A reviews a patch of B (or reciprocally)
        # in term of graph:
        #   - each node represents a reviewer or a writter (owner)
        #   - each edge represents a collaboration
        # here we count the degree of each node and find out who's the best collaborator
        # TODO: use this graph to get other metrics (??)

        # it could be interesting to weight each contribution according to its date
        # someone who made 20 contribs recently is probably better than someone 50 contribs
        # two years ago...
        # TODO: We could weight a contrib with a gaussian which depends to the time
        
        collaborations = { }
        for info in self.get().itervalues():
            if info['authorized']:
                owner = info['owner']
                if owner not in collaborations:
                    collaborations[owner] = 0
                reviewers = info['reviewers']
                feedbacks = info['feedbacks']
                collabs = set()
                if reviewers and owner in reviewers:
                    collabs |= reviewers[owner]
                if feedbacks and owner in feedbacks:
                    collabs |= feedbacks[owner]
                if collabs:
                    collaborations[owner] += len(collabs)
                    for person in collabs:
                        collaborations[person] = collaborations[person] + 1 if person in collaborations else 1
 
        # maybe we should compute the percentage of collaborations just to give an idea
 
        return utils.get_best(collaborations)

    def get_best_component_product(self):
        # Just get stats on components and products
        comps_prods = { }
        for info in self.get().itervalues():
            if info['authorized']:
                comp_prod = (info['component'], info['product'])
                comps_prods[comp_prod] = comps_prods[comp_prod] + 1 if comp_prod in comps_prods else 1

        if comps_prods:
            return utils.get_best(comps_prods)
        else:        
            return None

    def __get_apikey(self):
        if self.credentials:
            return self.credentials['tokens'][self.BZ_URL]
        else:
            return ''

    def __info_cb(self, sess, res):
        bugs = res.json()['bugs']
        for bug in bugs:
            self.info[str(bug['id'])].update({ 'authorized': True,
                                               'severity': bug['severity'],
                                               'votes': bug['votes'],
                                               'component': bug['component'],
                                               'product': bug['product'],
                                               'nbcc': len(bug['cc']),
                                               'reporter': bug['creator'],
                                               'owner': bug['assigned_to_detail']['email']})

    def __get_info(self):
        def chunks():
            for i in range(0, len(self.bugids), self.CHUNK_SIZE):
                yield self.bugids[i:(i + self.CHUNK_SIZE)]
                
        for bugids in chunks():
            bugids = ','.join(map(str, bugids))
            self.results.append(self.session.get(self.API_URL,
                                                 params = {'api_key': self.__get_apikey(),
                                                           'id': bugids},
                                                 verify = True,
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__info_cb))

    def __history_cb(self, sess, res):
        if res.status_code == 200:
            json = res.json()
            ownership = []
            reviewers = { }
            feedbacks = { }
            if 'bugs' in json and json['bugs']: 
                bug = json['bugs'][0]
                bugid = str(bug['id'])
                history = bug['history']
                for h in history:
                    who = h['who']
                    owner = None
                    changes = h['changes']
                    for change in changes:
                        nam = change['field_name']
                        rem = change['removed']
                        add = change['added']

                        if nam == 'status':
                            if rem == 'NEW' and add == 'ASSIGNED':
                                owner = who
                        elif nam == 'assigned_to':
                            owner = add
                        elif nam == 'flagtypes.name':
                            # Get the reviewers
                            for m in self.review_pattern.finditer(add):
                                if who in reviewers:
                                    reviewers[who].add(m.group(1))
                                else:
                                    reviewers[who] = set([m.group(1)])
 
                            # Get people pinged for feedback
                            for m in self.feedback_pattern.finditer(add):
                                if who in feedbacks:
                                    feedbacks[who].add(m.group(1))
                                else:
                                    feedbacks[who] = set([m.group(1)])

                    if owner and (not ownership or ownership[-1]['owner'] != owner):
                        ownership.append({ 'owner': owner,
                                           'touch_by': who,
                                           'touch_when': h['when']} )

                self.info[bugid].update({ 'ownership': ownership,
                                          'reviewers': reviewers,
                                          'feedbacks': feedbacks})
                
    def __analyze_history(self):
        for bugid in self.bugids:
            self.results.append(self.session.get(self.API_URL + '/' + bugid + '/history',
                                                 params = { 'api_key': self.__get_apikey() },
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__history_cb))

    def __comment_cb(self, sess, res):
        if res.status_code == 200:
            json = res.json()
            if 'bugs' in json:
                bugs = json['bugs']
                keys = bugs.keys()
                bugid = ''
                for key in keys:
                    if isinstance(key, basestring) and key.isdigit():
                        bugid = key
                        break
                if bugid:
                    commenters = { }
                    bug = bugs[bugid]
                    if 'comments' in bug:
                        comments = bug['comments']
                        authors = []
                        for comment in comments:
                            text = comment['text']
                            if not self.dupbug_pattern.match(text):
                                author = comment['author']
                                authors.append(author)
                                if author not in commenters:
                                    commenters[author] = []

                                for m in self.reply_pattern.finditer(comment['raw_text']):
                                    n = int(m.group(1))
                                    if n >= 1 and n <= len(authors):
                                        commenters[authors[n - 1]].append(author)

                        self.info[bugid].update({'commenters': commenters})

    def __analyze_comment(self):
        for bugid in self.bugids:
            self.results.append(self.session.get(self.API_URL + '/' + bugid + '/comment',
                                                 params = {'api_key': self.__get_apikey()},
                                                 timeout = self.TIMEOUT,
                                                 background_callback = self.__comment_cb))


#bi=BZInfo([1127618, 1127619, 1127620, 1127621, 1127622, 1127623])
#pprint(bi.get())
#pprint(bi.get_best_collaborator())

