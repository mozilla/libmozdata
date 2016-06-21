import base64
import re
from datetime import (datetime, timedelta)
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen
import weakref
import numbers
from collections import Counter
import warnings
import whatthepatch
from .HGFileInfo import HGFileInfo
from .bugzilla import Bugzilla, BugzillaUser
from .CrashInfo import CrashInfo
from . import hgmozilla
from . import modules
from . import utils


reviewer_cache = {}


def short_name_match(short_name, real_name, email):
    names = real_name.split(' ')
    possible_short_name = (names[0][0] + names[1]).lower() if names and len(names) >= 2 else ''

    return '[:' + short_name + ']' in real_name or\
           '(:' + short_name + ')' in real_name or\
           ':' + short_name + ',' in real_name or\
           short_name + '@mozilla.com' in real_name or\
           (possible_short_name and short_name == possible_short_name) or\
           short_name == email[email.index('@') + 1:email.rindex('.')]


def reviewer_match(short_name, bugzilla_names, cc_list):
    if short_name in reviewer_cache:
        assert reviewer_cache[short_name] in bugzilla_names
        return reviewer_cache[short_name]

    found = set()

    # Check if we can find the reviewer in the list of reviewers from the bug.
    for bugzilla_name in bugzilla_names:
        if bugzilla_name.startswith(short_name):
            found.add(bugzilla_name)

    if len(found) == 0:
        # Otherwise, check if we can find him/her in the CC list.
        found |= set([entry['email'] for entry in cc_list if entry['email'] in bugzilla_names and short_name_match(short_name, entry['real_name'], entry['email'])])

    if len(found) == 0:
        # Otherwise, find matching users on Bugzilla.
        bugzilla_users = []

        def user_handler(u):
            bugzilla_users.append(u)

        BugzillaUser(search_strings='match=' + short_name, user_handler=user_handler).wait()
        for bugzilla_name in bugzilla_names:
            BugzillaUser(bugzilla_name, user_handler=user_handler).wait()

        found |= set([user['email'] for user in bugzilla_users if user['email'] in bugzilla_names and short_name_match(short_name, user['real_name'], user['email'])])

    # We should always find a matching reviewer name.
    # If we're unable to find it, add a static entry in the
    # reviewer_cache dict or find a new clever way to retrieve it.
    assert len(found) == 1, 'Reviewer ' + short_name + ' not found.'

    assert short_name not in reviewer_cache
    reviewer_cache[short_name] = found.pop()
    return reviewer_cache[short_name]


def author_match(author_mercurial, author_real_name, bugzilla_names, cc_list):
    if author_mercurial in bugzilla_names:
        return set([author_mercurial])

    found = set()

    if len(bugzilla_names) == 1:
        found.add(list(bugzilla_names)[0])

    # Check in the cc_list, so we don't have to hit Bugzilla.
    for entry in cc_list:
        if author_real_name in entry['real_name']:
            found.add(entry['email'])

    if len(found) == 0:
        # Otherwise, search on Bugzilla.
        bugzilla_users = []

        def user_handler(u):
            bugzilla_users.append(u)

        BugzillaUser(search_strings='match=' + author_real_name, user_handler=user_handler).wait()
        for user in bugzilla_users:
            if author_real_name in user['real_name']:
                found.add(user['email'])

    assert len(found) == 1, 'Author ' + author_mercurial + ' not found.'

    return set([author_mercurial, found.pop()])


def _is_test(path):
    return 'test' in path and not path.endswith(('ini', 'list', 'in', 'py', 'json', 'manifest'))


hginfos = weakref.WeakValueDictionary()


def patch_analysis(patch, authors, reviewers, creation_date=utils.get_date_ymd('today')):
    info = Counter({
        'changes_size': 0,
        'test_changes_size': 0,
        'modules_num': 0,
        'code_churn_overall': 0,
        'code_churn_last_3_releases': 0,
        'developer_familiarity_overall': 0,
        'developer_familiarity_last_3_releases': 0,
        'reviewer_familiarity_overall': 0,
        'reviewer_familiarity_last_3_releases': 0,
        'crashes': 0,
    })

    paths = []
    for diff in whatthepatch.parse_patch(patch):
        old_path = diff.header.old_path[2:] if diff.header.old_path.startswith('a/') else diff.header.old_path
        new_path = diff.header.new_path[2:] if diff.header.new_path.startswith('b/') else diff.header.new_path

        if _is_test(new_path):
            info['test_changes_size'] += len(diff.changes)
        else:
            info['changes_size'] += len(diff.changes)

        if old_path != '/dev/null' and old_path != new_path:
            paths.append(old_path)

        if new_path != '/dev/null':
            paths.append(new_path)

    used_modules = {}
    ci = CrashInfo(paths).get()  # TODO: Only check files that can actually be here (.c or .cpp).
    for path in paths:
        info['crashes'] += ci[path]

        module = modules.module_from_path(path)
        if module and module['name'] not in used_modules:
            used_modules[module['name']] = 1

        if path in hginfos:
            hi = hginfos[path]
        else:
            hi = hginfos[path] = HGFileInfo(path, date_type='creation')

        utc_ts_to = utils.get_timestamp(creation_date) - 1  # -1 so it doesn't include the current patch

        info['code_churn_overall'] += len(hi.get(path, utc_ts_to=utc_ts_to)['patches'])
        info['code_churn_last_3_releases'] += len(hi.get(path, utc_ts_from=utils.get_timestamp(creation_date + timedelta(-3 * 6 * 7)), utc_ts_to=utc_ts_to)['patches'])
        info['developer_familiarity_overall'] += len(hi.get(path, authors=authors, utc_ts_to=utc_ts_to)['patches'])
        info['developer_familiarity_last_3_releases'] += len(hi.get(path, authors=authors, utc_ts_from=utils.get_timestamp(creation_date + timedelta(-3 * 6 * 7)), utc_ts_to=utc_ts_to)['patches'])
        info['reviewer_familiarity_overall'] += len(hi.get(path, authors=reviewers, utc_ts_to=utc_ts_to)['patches'])
        info['reviewer_familiarity_last_3_releases'] += len(hi.get(path, authors=reviewers, utc_ts_from=utils.get_timestamp(creation_date + timedelta(-3 * 6 * 7)), utc_ts_to=utc_ts_to)['patches'])

    info['modules_num'] = sum(used_modules.values())

    # TODO: Add coverage info before and after the patch.

    return info


MOZREVIEW_URL_PATTERN = 'https://reviewboard.mozilla.org/r/([0-9]+)/'


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
            'platform', 'op_sys', 'cc',
        ]

        ATTACHMENT_INCLUDE_FIELDS = [
            'flags', 'is_patch', 'creator', 'content_type',
        ]

        Bugzilla(bug_id, INCLUDE_FIELDS, bughandler=bughandler, commenthandler=commenthandler, attachmenthandler=attachmenthandler, attachment_include_fields=ATTACHMENT_INCLUDE_FIELDS).get_data().wait()

    info = Counter({
        'backout_num': 0,
        'blocks': len(bug['blocks']),
        'depends_on': len(bug['depends_on']),
        'comments': len(bug['comments']),
        'r-ed_patches': sum((a['is_patch'] == 1 or a['content_type'] == 'text/x-review-board-request') and sum(flag['name'] == 'review' and flag['status'] == '-' for flag in a['flags']) > 0 for a in bug['attachments']),
    })

    # Get all reviewers and authors, we will match them with the changeset description (r=XXX).
    bugzilla_reviewers = set()
    bugzilla_authors = set()
    for attachment in bug['attachments']:
        if sum(flag['name'] == 'review' and (flag['status'] == '+' or flag['status'] == '-') for flag in attachment['flags']) == 0:
            continue

        bugzilla_authors.add(attachment['creator'])

        for flag in attachment['flags']:
            # If the creator of the patch is the setter of the review flag, it's probably
            # because he/she was carrying a r+, so we don't add him/her to the reviewers list.
            if flag['setter'] == attachment['creator']:
                continue

            bugzilla_reviewers.add(flag['setter'])

    reviewer_pattern = re.compile('r=([a-zA-Z0-9]+)')
    author_pattern = re.compile('<([^>]+)>')
    author_name_pattern = re.compile('([^<]+)')
    backout_pattern = re.compile('(?:Backout|Back out|Backed out|Backedout) changeset ([0-9a-z]+)')
    bug_pattern = re.compile('[\t ]*[Bb][Uu][Gg][\t ]*([0-9]+)')
    landings = Bugzilla.get_landing_comments(bug['comments'], ['inbound', 'central', 'fx-team'])
    revs = {}
    backed_out_revs = set()
    backout_comments = set()
    for landing in landings:
        rev = landing['revision'][:12]
        channel = landing['channel']

        diff = hgmozilla.RawRevision.get_revision(channel, rev)
        # TODO: No need to get the revision, we have everything in the raw format.
        #       We can use pylib/mozautomation/mozautomation/commitparser.py from version-control-tools
        meta = hgmozilla.Revision.get_revision(channel, rev)

        # Check if it was a backout
        backout_revisions = set()
        for match in backout_pattern.finditer(meta['desc']):
            backout_revisions.add(match.group(1)[:12])
        if not backout_revisions:
            # TODO: Search in lowercase.
            match = re.search('Backout|Back out|Backed out|Backedout', meta['desc'])
            if match:
                for parent in meta['parents']:
                    for match in backout_pattern.finditer(hgmozilla.Revision.get_revision(channel, parent)['desc']):
                        backout_revisions.add(match.group(1)[:12])

                # It's definitely a backout, but we couldn't find which revision was backed out.
                if not backout_revisions:
                    warnings.warn('Looks like a backout, but we couldn\'t find which revision was backed out.', stacklevel=2)
                # I wish we could assert instead of warn.
                # assert backout_revisions

        if backout_revisions and not backout_revisions.issubset(backed_out_revs):
            backout_comments.add(landing['comment']['id'])
            backed_out_revs.update(backout_revisions)

        if backout_revisions:
            continue

        bug_id_match = re.search(bug_pattern, meta['desc'])
        if bug_id_match:
            if int(bug_id_match.group(1)) != bug['id']:
                warnings.warn('Revision ' + rev + ' is related to another bug (' + bug_id_match.group(1) + ').', stacklevel=2)
                continue

        reviewers = set()
        for match in reviewer_pattern.finditer(meta['desc']):
            reviewers.add(match.group(1))

        author_mercurial = author_pattern.search(meta['user']).group(1)
        author_real_name = author_name_pattern.search(meta['user']).group(1)
        # Multiple names because sometimes authors use different emails on Bugzilla and Mercurial and sometimes
        # they change it.
        author_names = author_match(author_mercurial, author_real_name, bugzilla_authors, bug['cc_detail'])

        # Overwrite revisions from integration channels (inbound, fx-team).
        if rev not in revs or channel == 'central':
            revs[rev] = {
                'diff': diff,
                'author_names': author_names,
                'creation_date': meta['date'][0],
                'reviewers': reviewers,
            }

    # Remove backed out changesets
    for rev in backed_out_revs:
        if rev not in revs:
            warnings.warn('Revision ' + rev + ' was not found.', stacklevel=2)
        else:
            del revs[rev]

    if len(revs) > 0:
        for rev in revs.values():
            reviewers = set()

            short_reviewers = rev['reviewers']

            for short_reviewer in short_reviewers:
                if short_reviewer == 'me' or short_reviewer == 'bustage':
                    reviewers |= rev['author_names']
                else:
                    reviewers.add(reviewer_match(short_reviewer, bugzilla_reviewers, bug['cc_detail']))

            rev['reviewers'] = reviewers

            info += patch_analysis(rev['diff'], rev['author_names'], reviewers, datetime.utcfromtimestamp(rev['creation_date']))
    else:
        def attachmenthandler(attachments, bugid, data):
            for i in range(0, len(bug['attachments'])):
                bug['attachments'][i].update(attachments[i])

        Bugzilla(bug['id'], attachmenthandler=attachmenthandler, attachment_include_fields=['data', 'is_obsolete', 'creation_time']).get_data().wait()

        for attachment in bug['attachments']:
            if sum(flag['name'] == 'review' and flag['status'] == '+' for flag in attachment['flags']) == 0:
                continue

            data = None

            if attachment['is_patch'] == 1 and attachment['is_obsolete'] == 0:
                data = base64.b64decode(attachment['data']).decode('ascii', 'ignore')
            elif attachment['content_type'] == 'text/x-review-board-request' and attachment['is_obsolete'] == 0:
                mozreview_url = base64.b64decode(attachment['data']).decode('utf-8')
                review_num = re.search(MOZREVIEW_URL_PATTERN, mozreview_url).group(1)
                mozreview_raw_diff_url = 'https://reviewboard.mozilla.org/r/' + review_num + '/diff/raw/'

                response = urlopen(mozreview_raw_diff_url)
                data = response.read().decode('ascii', 'ignore')

            reviewers = [flag['setter'] for flag in attachment['flags'] if flag['name'] == 'review' and flag['status'] == '+']

            if data is not None:
                info += patch_analysis(data, [attachment['creator']], reviewers, utils.get_date_ymd(attachment['creation_time']))

    # TODO: Add number of crashes with signatures from the bug (also before/after the patch?).

    # TODO: Add perfherder results?

    # TODO: Add number of days since the landing (to check if the patch baked a little on nightly or not).

    info['backout_num'] = len(backout_comments)

    return info
