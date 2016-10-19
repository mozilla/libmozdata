# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from elasticsearch import Elasticsearch


class ESBugzilla(Elasticsearch):

    def __init__(self):
        super(ESBugzilla, self).__init__(['https://esfrontline.bugzilla.mozilla.org:443'], verify_certs=False)

    def get_bug_history(self, bug_id):
        return self.search(
            index="public_bugs",
            body={
                "query": {
                    "filtered": {
                        "query": {
                            "match_all": {}
                        },
                        "filter": {
                            "term": {
                                "bug_id": bug_id
                            }
                        }
                    }
                },
                "from": 0,
                "size": 2000,
                "sort": ["bug_version_num"]
            }
        )

    def get_bug_comments(self, bug_id):
        return self.search(
            index="public_comments",
            body={
                "query": {
                    "filtered": {
                        "query": {
                            "match_all": {}
                        },
                        "filter": {
                            "term": {
                                "bug_id": bug_id
                            }
                        }
                    }
                },
                "from": 0,
                "size": 2000,
                "sort": ["comment_id"]
            }
        )
