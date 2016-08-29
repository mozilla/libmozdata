import os
from .connection import Query
from .socorro import SuperSearch


class CrashInfo(SuperSearch):

    def __init__(self, paths):
        self.info = {}

        paths = [paths] if type(paths) == str else paths
        queries = []
        for path in paths:
            queries.append(Query(SuperSearch.URL,
                                 params={'product': 'Firefox',
                                         'topmost_filenames': '~' + os.path.basename(path).lower(),
                                         '_results_number': 0,
                                         '_facets': 'product',
                                         '_facets_size': 1},
                                 handler=self.__handler,
                                 handlerdata=path))

        super(CrashInfo, self).__init__(queries=queries)

    def get(self):
        self.wait()
        return self.info

    def __handler(self, res, path):
        self.info[path] = res['total']
