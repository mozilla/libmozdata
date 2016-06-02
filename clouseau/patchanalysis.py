import base64
import re
from datetime import (date, timedelta)
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen
import weakref
import os
import pickle
import numbers
import whatthepatch
from .HGFileInfo import HGFileInfo
from .bugzilla import Bugzilla
from .CrashInfo import CrashInfo
from . import modules
from . import utils

hginfos = weakref.WeakValueDictionary()


def patch_analysis(patch, author):
    info = {
        'changes_size': 0,
        'modules_num': 0,
        'code_churn_overall': 0,
        'code_churn_last_3_releases': 0,
        'developer_familiarity_overall': 0,
        'developer_familiarity_last_3_releases': 0,
        # 'reviewer_familiarity_overall': 0,
        # 'reviewer_familiarity_last_3_releases': 0,
        'crashes': 0,
    }

    paths = []
    for diff in whatthepatch.parse_patch(patch):
        info['changes_size'] += len(diff.changes)

        old_path = diff.header.old_path[2:] if diff.header.old_path.startswith('a/') else diff.header.old_path
        new_path = diff.header.new_path[2:] if diff.header.new_path.startswith('b/') else diff.header.new_path

        if old_path != '/dev/null' and old_path != new_path:
            paths.append(old_path)

        if new_path != '/dev/null':
            paths.append(new_path)

    used_modules = {}
    ci = CrashInfo(paths).get()
    for path in paths:
        info['crashes'] += ci[path]

        module = modules.module_from_path(path)
        if module and module['name'] not in used_modules:
            used_modules[module['name']] = 1

        if path in hginfos:
            hi = hginfos[path]
        else:
            hi = hginfos[path] = HGFileInfo(path)

        info['code_churn_overall'] += len(hi.get(path)['patches'])
        info['code_churn_last_3_releases'] += len(hi.get(path, utc_ts_from=utils.get_timestamp(date.today() + timedelta(-3 * 6 * 7)))['patches'])
        info['developer_familiarity_overall'] += len(hi.get(path, author=author)['patches'])
        info['developer_familiarity_last_3_releases'] += len(hi.get(path, author=author, utc_ts_from=utils.get_timestamp(date.today() + timedelta(-3 * 6 * 7)))['patches'])

        # TODO: Add number of times the file was modified by the reviewer.

    info['modules_num'] = sum(used_modules.values())

    # TODO: Add coverage info before and after the patch.

    return info


MOZREVIEW_URL_PATTERN = 'https://reviewboard.mozilla.org/r/([0-9]+)/diff/#index_header'
MOZREVIEW_URL_PATTERN2 = 'https://reviewboard.mozilla.org/r/([0-9]+)/'


# TODO: Consider feedback+ and feedback- as review+ and review-
def bug_analysis(bug):
    if isinstance(bug, numbers.Number):
        bug_id = bug
        bug = {}

        def bughandler(found_bug, data):
            bug.update(found_bug)

        def commenthandler(found_bug, bugid, data):
            bug['comments'] = found_bug['comments']

        def attachmenthandler(attachments, bugid, data):
            bug['attachments'] = attachments

        INCLUDE_FIELDS = [
            'id', 'flags', 'depends_on', 'keywords', 'blocks', 'whiteboard', 'resolution', 'status',
            'url', 'version', 'summary', 'priority', 'product', 'component', 'severity',
            'platform', 'op_sys'
        ]

        INCLUDE_FIELDS_QUERY = 'include_fields=' + ','.join(INCLUDE_FIELDS)

        Bugzilla('id=' + str(bug_id) + '&' + INCLUDE_FIELDS_QUERY, bughandler=bughandler, commenthandler=commenthandler, attachmenthandler=attachmenthandler).get_data().wait()

    info = {
        'backout_num': 0,
        'blocks': len(bug['blocks']),
        'depends_on': len(bug['depends_on']),
        'comments': len(bug['comments']),
        'r-ed_patches': sum((a['is_patch'] == 1 or a['content_type'] == 'text/x-review-board-request') and sum(flag['name'] == 'review' and flag['status'] == '-' for flag in a['flags']) > 0 for a in bug['attachments']),
    }

    # Assume all non-obsolete and r+ed patches have landed.
    # TODO: Evaluate if reading comments to see what landed is better.
    for attachment in bug['attachments']:
        if sum(flag['name'] == 'review' and flag['status'] == '+' for flag in attachment['flags']) == 0:
            continue

        data = None

        if attachment['is_patch'] == 1 and attachment['is_obsolete'] == 0:
            data = base64.b64decode(attachment['data']).decode('ascii', 'ignore')
        elif attachment['content_type'] == 'text/x-review-board-request' and attachment['is_obsolete'] == 0:
            mozreview_url = base64.b64decode(attachment['data']).decode('utf-8')

            try:
                review_num = re.search(MOZREVIEW_URL_PATTERN, mozreview_url).group(1)
            except:
                review_num = re.search(MOZREVIEW_URL_PATTERN2, mozreview_url).group(1)

            try:
                with open('mozreviews_cache/' + review_num, 'rb') as f:
                    data = pickle.load(f)
            except:
                mozreview_raw_diff_url = 'https://reviewboard.mozilla.org/r/' + review_num + '/diff/raw/'

                response = urlopen(mozreview_raw_diff_url)
                data = response.read().decode('ascii', 'ignore')

                try:
                    os.mkdir('mozreviews_cache')
                except OSError:
                    pass

                with open('mozreviews_cache/' + review_num, 'wb') as f:
                    pickle.dump(data, f)

        if data is not None:
            info.update(patch_analysis(data, attachment['creator']))
            # XXX: The creator of the attachment isn't always the developer of the patch (and sometimes it is, but with a different email). For example, in bug 1271794.
            # Using the landing comment with the hg revision instead of reading the attachments would be better.

    # TODO: Add number of crashes with signatures from the bug (also before/after the patch?).

    # TODO: Add number of days since the landing (to check if the patch baked a little on nightly or not).

    # TODO: Use a more clever way to check if the patch was backed out.
    for comment in bug['comments']:
        if 'backed out' in comment['text'].lower():
            info['backout_num'] += 1

    return info
