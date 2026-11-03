#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Write the list of WonderSwan translation patches at the top of README.md.

The list comes from the catalog of https://github.com/mariovirgili/WonderSwan_bps_repo (index.json),
which a crawler there updates every day. One row per release, newest first, with a link to the
release; patches published as files in a repository get one row per repository, with its latest
files. Only the part of the
README between the two markers below is rewritten.

    python .github/scripts/update_patch_list.py [README.md] [index.json]

Without index.json the catalog is downloaded.
"""
import json
import pathlib
import sys
import urllib.request

CATALOG_URL = 'https://raw.githubusercontent.com/mariovirgili/WonderSwan_bps_repo/main/index.json'
CATALOG_REPO = 'https://github.com/mariovirgili/WonderSwan_bps_repo'
START, END = '<!-- patch-list:start -->', '<!-- patch-list:end -->'
LANGUAGES = {'en': 'English', 'es': 'Spanish', 'it': 'Italian', 'fr': 'French', 'de': 'German', 'pt': 'Portuguese', 'ja': 'Japanese'}


def cell(text):
    """Text for a Markdown table cell."""
    return str(text or '').replace('|', '\\|').replace('\n', ' ').strip()


def load(path=None):
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    with urllib.request.urlopen(CATALOG_URL, timeout=60) as r:
        return json.load(r)


def releases(catalog):
    """Catalog entries grouped by release (or by file, for files in a repository), newest first."""
    groups = {}
    for e in catalog.get('entries', []):
        if e.get('duplicate_of'):
            continue
        o = e.get('origin') or {}
        if o.get('kind') == 'release_asset':
            key = o.get('release_url') or f"{o.get('source')}@{o.get('release_tag')}"
            link, title = o.get('release_url'), o.get('release_name') or o.get('release_tag')
            date = (o.get('published_at') or e.get('first_seen') or '')[:10]
        else:
            # Files kept in a repository (no release): one row per repository, with its latest files,
            # dated by when the catalog first found the newest of them.
            if not e.get('latest'):
                continue
            key = o.get('source_url') or o.get('source')
            link, title = o.get('source_url'), f"{(o.get('source') or '').split('/')[-1]} (repository)"
            date = (e.get('first_seen') or '')[:10]
        g = groups.setdefault(key, {'date': date, 'link': link, 'title': title, 'author': (o.get('source') or '').split('/')[0],
                                    'source_url': o.get('source_url'), 'games': [], 'files': [], 'languages': []})
        g['date'] = max(g['date'], date)
        for k, v in (('games', e.get('game')), ('files', e.get('variant') or e.get('file_name')),
                     ('languages', LANGUAGES.get(e.get('language'), (e.get('language') or '').upper()))):
            if v and v not in g[k]:
                g[k].append(v)
    return sorted(groups.values(), key=lambda g: (g['date'], g['title'] or ''), reverse=True)


def table(catalog):
    rows = releases(catalog)
    when = (catalog.get('generated_at') or '')[:10]
    out = [START,
           '## WonderSwan translation patches — newest first',
           '',
           f'Every `.bps` / `.ips` WonderSwan translation patch found by [WonderSwan_bps_repo]({CATALOG_REPO}) '
           f'(mariovirgili, PokemonGoDB, Gand46), catalog of {when}: {len(rows)} releases (Gand46 publishes his patches as files in '
           'his repositories: one row per repository, with its latest files). '
           'This list is updated automatically after each catalog update.',
           '',
           '| Date | Game | Release | Patch files | Language | Author |',
           '| --- | --- | --- | --- | --- | --- |']
    for g in rows:
        title = cell(g['title'])
        release = f"[{title}]({g['link']})" if g['link'] else title
        author = f"[{cell(g['author'])}]({g['source_url']})" if g['source_url'] else cell(g['author'])
        out.append(f"| {g['date']} | {cell(' / '.join(g['games']))} | {release} | {cell(', '.join(g['files']))} | "
                   f"{cell(', '.join(g['languages']))} | {author} |")
    out.append(END)
    return '\n'.join(out)


def update(readme_text, catalog):
    block = table(catalog)
    if START in readme_text and END in readme_text:
        head, rest = readme_text.split(START, 1)
        return head + block + rest.split(END, 1)[1]
    # First run: the list goes right after the title and its subtitle line (the first section).
    lines = readme_text.split('\n')
    at = 2 if len(lines) > 1 and lines[0].startswith('# ') else 0
    return '\n'.join(lines[:at] + ['', block, ''] + lines[at:])


def main():
    readme = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'README.md')
    catalog = load(sys.argv[2] if len(sys.argv) > 2 else None)
    if not catalog.get('entries'):
        sys.exit('catalog has no entries; README left as it is')
    old = readme.read_text(encoding='utf-8')
    new = update(old, catalog)
    if new != old:
        readme.write_text(new, encoding='utf-8')
        print('README.md updated')
    else:
        print('README.md already up to date')


if __name__ == '__main__':
    main()
