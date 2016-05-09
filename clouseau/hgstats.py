from mercurial import ui, hg
import mercurial
from pprint import pprint
from datetime import datetime
import os
import argparse


class HGExploration(object):

    def __init__(self, path, rev='tip'):
        self.root = path
        self.ui = ui.ui()
        self.rev = rev
        self.repo = hg.repository(self.ui, path)
        self.ctx = self.repo[self.rev]
        self.haspushlog = hasattr(self.repo, 'pushlog')

    def __explore_file(self, path, file_hook, userdata):
        # pprint(path)
        if path in self.ctx:
            fctx = self.ctx[path]
            file_hook(self.repo, self.haspushlog, fctx, userdata)

    def __explore_dir(self, path, file_hook, userdata):
        for root, subdirs, files in os.walk(path):
            if files:
                if self.root.endswith(os.sep):
                    _root = root[len(self.root):]
                else:
                    _root = root[len(self.root) + 1:]
                for f in files:
                    self.__explore_file(os.path.join(_root, f), file_hook, userdata)
            for d in subdirs:
                self.__explore_dir(os.path.join(root, d), file_hook, userdata)

    def explore(self, file_hook, userdata):
        self.__explore_dir(self.repo.root, file_hook, userdata)

    @staticmethod
    def stat_file(repo, haspushlog, fctx, userdata):
        fl = fctx.filelog()
        path = fctx.path()
        for rev in fl.revs():
            _fctx = fctx.filectx(rev)
            author = _fctx.user()
            date = None
            if haspushlog:
                pushinfo = repo.pushlog.pushfromchangeset(_fctx)
                if pushinfo:
                    pushdate = mercurial.util.makedate(pushinfo[2])[0]
                    date = datetime.utcfromtimestamp(pushdate)
            else:
                date = _fctx.date()

            pprint([path, author, date])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='hgstats')
    parser.add_argument('-p', '--path', action='store', required=True, help='the path to the mercurial repository')
    parser.add_argument('-r', '--revision', action='store', default='tip', help='the revision')

    args = parser.parse_args()

    ud = {}
    hge = HGExploration(path=args.path, rev=args.revision).explore(file_hook=HGExploration.stat_file, userdata=ud)
