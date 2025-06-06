#!/usr/bin/python3
#
# cherry-pick complete translations from weblate
#
# This is too hard to get working right, so really, this should be
# punted to the translators.  Weblate can automatically file a merge
# request when a language hits 100% translated and 0% failed.
#
# This will probably fail to cherry-pick if a commit contains more
# than one language.  In that case, reset everything, then manually
# cherry-pick that one commit and push it.  Then run this again.

import git
import os
import re
import requests
import sys


def get_paths_tuple(locale):
    return (
        'metadata/%s/*.txt' % locale.replace('_', '-'),
        'metadata/%s/changelogs/*.txt' % locale.replace('_', '-'),
        'app/src/main/res/values-%s/strings.xml'
        % (
            locale.replace('Hant_HK', 'HK')
            .replace('Hans', 'CN')
            .replace('Hant', 'TW')
            .replace('_', '-r')
        ),
    )


projectbasedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

repo = git.Repo(projectbasedir)
weblate = repo.remotes.weblate
weblate.fetch()
upstream = repo.remotes.upstream
upstream.fetch()

url = 'https://hosted.weblate.org/api/components/f-droid/f-droid/statistics/?format=json'
r = requests.get(url)
r.raise_for_status()
app = r.json()['results']

url = 'https://hosted.weblate.org/api/components/f-droid/f-droid-metadata/statistics/?format=json'
r = requests.get(url)
r.raise_for_status()
metadata = r.json()['results']


# with open('f-droid-metadata.json') as fp:
#    metadata = json.load(fp)

app_locales = dict()
metadata_locales = dict()

merge_locales = []
for locale in app:
    app_locales[locale['code']] = locale
for locale in metadata:
    metadata_locales[locale['code']] = locale

print('%10s' % 'locale', 'app %', 'failing', 'meta %', 'failing', sep='\t')
for locale in sorted(app_locales.keys(), reverse=True):
    a = app_locales.get(locale)
    m = metadata_locales.get(locale)
    if m:
        print(
            '%10s' % locale,
            a['translated_percent'],
            a['failing'],
            m['translated_percent'],
            m['failing'],
            sep='\t',
            end='',
        )
    else:
        print('%10s' % locale, a['translated_percent'], a['failing'], sep='\t')
    if (a is not None and a['translated_percent'] == 100 and a['failing'] == 0) or (
        m is not None and m['translated_percent'] == 100 and m['failing'] == 0
    ):
        print('\t<--- selected')
        merge_locales.append(locale)
    else:
        print()

if not merge_locales:
    sys.exit()

print('\nIf all else fails, try:')
print('\tgit checkout -B merge_weblate weblate/master')
print('\tgit rebase -i upstream/master')
print('\t# select all in editor and cut')
print('\twl-paste | grep -Eo ".* \((%s)\) .*" | wl-copy' % '|'.join(merge_locales))
print('\t# paste into editor, and make rebase\n')

if 'merge_weblate' in repo.heads:
    merge_weblate = repo.heads['merge_weblate']
    repo.create_tag(
        'previous_merge_weblate',
        ref=merge_weblate,
        message=('Automatically created by %s' % __file__),
    )
else:
    merge_weblate = repo.create_head('merge_weblate')
merge_weblate.set_commit(upstream.refs.master)
merge_weblate.checkout()

email_pattern = re.compile(r'by (.*?) <(.*)>$')

cherry_picked = set()
for locale in sorted(merge_locales):
    a = app_locales.get(locale)
    m = metadata_locales.get(locale)
    paths = get_paths_tuple(locale)
    skipped_cherry_pick = False
    for commit in repo.iter_commits(
        str(weblate.refs.master) + '...' + str(upstream.refs.master),
        paths=paths,
        max_count=10,
        reverse=True,
    ):
        has_a = False
        has_m = False
        for i in commit.iter_items(repo, commit.hexsha, paths=[paths[2]]):
            if (
                i.hexsha == commit.hexsha
                and a['translated_percent'] == 100
                and a['failing'] == 0
            ):
                has_a = True
            break
        for i in commit.iter_items(repo, commit.hexsha, paths=paths[0:2]):
            if (
                i.hexsha == commit.hexsha
                and m['translated_percent'] == 100
                and m['failing'] == 0
            ):
                has_m = True
            break
        if has_a or has_m:
            commit_id = str(commit)
            if not skipped_cherry_pick and commit_id not in cherry_picked:
                repo.git.cherry_pick(commit_id)
                cherry_picked.add(commit_id)
        else:
            skipped_cherry_pick = True
        match = email_pattern.search(commit.summary)
        if match:
            email = match.group(1) + ' <' + match.group(2) + '>'
