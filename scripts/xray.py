#!/usr/bin/env python3
"""Deterministic helpers for the codebase-xray skill.

Reachability, SQL call status and citation checks are computed here, not by a
model, so "dormant" and "safe to drop" rest on evidence a script can re-check.
Standard library only.

  xray.py reach <graph.json> --out <reachability.json>
  xray.py sql   <source-root> --out <sql-objects.json>
  xray.py cite  <xray-result.json> <source-root>          (annotates in place)
  xray.py brief <xray-dir> --date YYYY-MM-DD --out <reachability-brief.md>
  xray.py shards <graph.json> --out <modules.json> [--max-files 25] [--status active,unknown,dormant]
  xray.py security <security-result.json> --date YYYY-MM-DD --out <security-findings.md>
"""

import argparse
import json
import os
import re
import sys
from collections import deque

SKIP_DIRS = {'.git', '.hg', '.svn', 'node_modules', 'bin', 'obj', 'dist', 'build',
             'target', 'vendor', '.venv', 'venv', '__pycache__', 'context', '.idea', '.vs',
             'packages', 'aspnet_client', 'bower_components', 'jspm_packages'}
MAX_FILE_BYTES = 2_000_000
MAX_REFS = 5
WORD = re.compile(r'[a-z_][a-z0-9_]*')


def read_json(path):
    with open(path) as fh:
        return json.load(fh)


def write_json(path, data):
    with open(path, 'w') as fh:
        json.dump(data, fh, indent=2)


# --- reach -------------------------------------------------------------------

def leaves_of(node, out):
    children = node.get('children') or []
    if not children and node.get('kind') not in ('system', 'domain'):
        out[node['id']] = node
    for child in children:
        leaves_of(child, out)
    return out


def reach(graph):
    """Classify every leaf as active, dormant or unknown, and list orphaned refs.

    active   reachable from an entry point over any edge kind
    unknown  unreachable, but a possible target of an unresolved dynamic call
    dormant  unreachable and not a possible dynamic target
    orphaned a reference whose target has no implementation in the graph
    """
    leaves = leaves_of(graph['root'], {})
    entries = graph.get('entryPoints') or []
    if not entries:
        raise SystemExit('reach: graph has no entryPoints. Every node would look dormant; '
                         'find the entry points in deployment/route/scheduler config first.')
    missing = [e for e in entries if e not in leaves]
    if missing:
        raise SystemExit(f'reach: entryPoints not found among leaf nodes: {missing}')

    adjacency, orphaned = {}, list(graph.get('danglingRefs') or [])
    for edge in graph.get('edges') or []:
        src, dst = edge.get('source'), edge.get('target')
        if src not in leaves or dst not in leaves:
            orphaned.append({'source': src, 'ref': dst, 'site': edge.get('site', ''),
                             'reason': 'edge endpoint is not a leaf node in the graph'})
            continue
        adjacency.setdefault(src, []).append(dst)

    parent = {e: None for e in entries}
    queue = deque(entries)
    while queue:
        cur = queue.popleft()
        for nxt in adjacency.get(cur, []):
            if nxt not in parent:
                parent[nxt] = cur
                queue.append(nxt)

    unbounded = graph.get('unboundedDynamic') or []
    dynamic = {d['id']: d for d in graph.get('dynamicTargets') or []}
    nodes = {}
    for nid, leaf in leaves.items():
        info = {'name': leaf.get('name', nid), 'kind': leaf.get('kind'), 'file': leaf.get('file')}
        if nid in parent:
            path, cur = [], nid
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            info.update(status='active', via=list(reversed(path)))
        elif nid in dynamic:
            info.update(status='unknown', reason=f"possible dynamic target: {dynamic[nid].get('reason', '')}"
                        f" ({dynamic[nid].get('site', 'no site')})")
        elif unbounded:
            info.update(status='unknown', reason='unbounded dynamic call sites exist: '
                        + ', '.join(s.get('site', '?') for s in unbounded[:3]))
        else:
            info.update(status='dormant')
        nodes[nid] = info

    counts = {s: sum(1 for n in nodes.values() if n['status'] == s) for s in ('active', 'dormant', 'unknown')}
    counts['orphaned'] = len(orphaned)
    return {'method': graph.get('method', ''), 'entryPoints': entries, 'counts': counts,
            'nodes': nodes, 'orphaned': orphaned, 'dynamicSites': graph.get('dynamicSites') or [],
            'unboundedDynamic': unbounded}


# --- sql ---------------------------------------------------------------------

SQL_DEF = re.compile(r'\bCREATE\s+(?:OR\s+(?:ALTER|REPLACE)\s+)?(PROCEDURE|PROC|TRIGGER|VIEW|FUNCTION)\s+'
                     r'([\[\]"`\w.]+)', re.IGNORECASE)
DYNAMIC_SQL = re.compile(r'\bsp_executesql\b|\bEXEC(?:UTE)?\s*\(|EXEC(?:UTE)?\s+@', re.IGNORECASE)
# A command or procedure name built from a literal prefix plus a variable: "fetch" & LookupName.
BUILT_NAME = re.compile(r'(?:CommandText\s*=|SqlCommand\s*\(|prepareCall\s*\(|callproc\s*\()\s*"(\w+)"\s*(?:&|\+)', re.IGNORECASE)
# Client-side and non-server files can't run SQL; a regex .exec( in jQuery is not dynamic SQL.
NOT_SERVER_CODE = ('.js', '.css', '.html', '.htm', '.map', '.json', '.md', '.txt', '.xml', '.svg')


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, 'rb') as fh:
                    raw = fh.read()
            except OSError:
                continue
            if b'\0' in raw[:4096]:
                continue
            yield os.path.relpath(path, root), raw.decode('utf-8', errors='replace').splitlines()


def sql_objects(root):
    files = list(walk(root))
    defs = []
    for rel, lines in files:
        if not rel.lower().endswith('.sql'):
            continue
        for i, line in enumerate(lines, 1):
            for m in SQL_DEF.finditer(line):
                full = re.sub(r'[\[\]"`]', '', m.group(2))
                kind = m.group(1).lower()
                defs.append({'name': full.split('.')[-1], 'qualified': full,
                             'type': 'procedure' if kind == 'proc' else kind, 'file': rel, 'line': i})

    dynamic_sites, built = [], []
    for rel, lines in files:
        low = rel.lower()
        if low.endswith(NOT_SERVER_CODE):
            continue
        for i, line in enumerate(lines, 1):
            if DYNAMIC_SQL.search(line) and len(dynamic_sites) < 20:
                dynamic_sites.append(f'{rel}:{i}')
            if not low.endswith('.sql'):
                for m in BUILT_NAME.finditer(line):
                    built.append((m.group(1).lower(), f'{rel}:{i}'))

    # One pass builds a word index (only for defined names), instead of one scan per object.
    wanted = {d['name'].lower() for d in defs}
    index = {}
    for rel, lines in files:
        is_sql = rel.lower().endswith('.sql')
        for i, line in enumerate(lines, 1):
            for w in set(WORD.findall(line.lower())) & wanted:
                index.setdefault(w, []).append((rel, i, is_sql))
    for d in defs:
        code_refs, sql_refs = [], []
        for rel, i, is_sql in index.get(d['name'].lower(), []):
            if (rel, i) == (d['file'], d['line']):
                continue
            (sql_refs if is_sql else code_refs).append(f'{rel}:{i}')
        prefix_site = next((site for prefix, site in built
                            if d['name'].lower().startswith(prefix) and len(d['name']) > len(prefix)), None)
        if d['type'] == 'trigger':
            d['called_from_code'] = 'n/a (trigger fires on table events)'
        elif code_refs:
            d['called_from_code'] = 'true'
        elif prefix_site:
            d['called_from_code'] = f'unknown (name matches a string-built call at {prefix_site})'
        elif dynamic_sites:
            d['called_from_code'] = 'unknown (no static reference; dynamic SQL present)'
        else:
            d['called_from_code'] = 'false'
        d['code_refs'] = code_refs[:MAX_REFS]
        d['sql_refs'] = sql_refs[:MAX_REFS]
    return {'objects': defs, 'dynamicSqlSites': dynamic_sites,
            'builtNameSites': sorted({site for _, site in built})}


# --- cite --------------------------------------------------------------------

def check_citation(root, file, line, cache):
    root_real = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, file))
    if not (path == root_real or path.startswith(root_real + os.sep)):
        return 'outside-root'
    if path not in cache:
        try:
            with open(path, 'rb') as fh:
                cache[path] = fh.read().count(b'\n') + 1
        except OSError:
            cache[path] = None
    if cache[path] is None:
        return 'missing-file'
    try:
        line = int(str(line).split('-')[0])
    except ValueError:
        return 'bad-line'
    return 'ok' if 1 <= line <= cache[path] else 'bad-line'


def cite(result, root):
    cache, tally = {}, {}

    def visit(obj):
        if isinstance(obj, dict):
            if obj.get('file') and 'line' in obj:
                obj['citation'] = check_citation(root, obj['file'], obj['line'], cache)
                tally[obj['citation']] = tally.get(obj['citation'], 0) + 1
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    visit(result)
    return tally


# --- brief -------------------------------------------------------------------

def bullet(items, fmt, empty='- None found'):
    return '\n'.join('- ' + fmt(x) for x in items) if items else empty


def at(x):
    return f"`{x.get('file')}:{x.get('line')}`" if x.get('file') else ''


def brief(xdir, date):
    reach_data, sql, result = (read_json(os.path.join(xdir, n))
                               for n in ('reachability.json', 'sql-objects.json', 'xray-result.json'))
    c = reach_data['counts']
    syn = result.get('synthesis') or {}

    def tally(items):
        t = {'active': 0, 'dormant': 0, 'unknown': 0}
        for i in items:
            t[i.get('reachability', 'unknown')] = t.get(i.get('reachability', 'unknown'), 0) + 1
        return t

    classes, surfaces = tally(result.get('classes', [])), tally(result.get('ioSurfaces', []))
    failed = result.get('failedModules') or []
    incomplete = (f"\n> **Incomplete scan.** {len(failed)} module(s) could not be analyzed and are excluded "
                  f"from every count and conclusion below: {', '.join(failed)}. Re-run for these modules "
                  f"before treating Safe-to-Drop as complete.\n") if failed else ''
    bad_cites = [f"`{x['file']}:{x['line']}` ({x['citation']})" for x in iter_cited(result)
                 if x.get('citation') not in (None, 'ok')]
    modules = result.get('modules') or []

    return f"""---
Status: Draft
Approved By:
Approved Date:
Last Updated: {date}
Supersedes:
Derived From: codebase-xray — {len(modules)} module(s) scanned: {', '.join(modules)}; graph built with {reach_data.get('method') or 'unspecified method'}
---

# Reachability Brief

*Generated by `codebase-xray`. Reachability is computed from the dependency graph in
`context/brownfield/xray/graph.json`, walked from its entry points; it is not a model's opinion.*
{incomplete}
## Reachability Summary

| Category | Active | Dormant | Unknown | Orphaned |
|---|---|---|---|---|
| Graph nodes | {c['active']} | {c['dormant']} | {c['unknown']} | {c['orphaned']} |
| Classes | {classes['active']} | {classes['dormant']} | {classes['unknown']} | — |
| I/O surfaces | {surfaces['active']} | {surfaces['dormant']} | {surfaces['unknown']} | — |

- **Active:** reachable from an entry point. **Dormant:** unreachable and not a possible dynamic target.
- **Unknown:** unreachable, but could be the target of a dynamic call (reflection, string-built names,
  convention DI) or the file sits outside the graph. Never treated as dormant.
- **Orphaned:** referenced, but no implementation exists in the scanned code.

Entry points: {', '.join(f'`{e}`' for e in reach_data['entryPoints'])}

## Load-Bearing (must survive modernization)

{bullet(syn.get('load_bearing', []), lambda x: f"**{x['item']}** — {x['why']} {at(x)}")}

## Safe to Drop (verified dormant — not yet confirmed with client)

Each item is unreachable in the graph **and** survived two independent agents trying to prove it is
still used.

{bullet(result.get('safeToDrop', []), lambda x: f"**{x['item']}** {at(x)} — {x['evidence']} — Confirmed with client: no")}

## Contested (a verifier found a possible use — do not drop)

{bullet(result.get('contested', []), lambda x: f"**{x['item']}** {at(x)} — " + '; '.join(f"{e['explanation']} {at(e)}" for e in x['counterEvidence']), '- None')}

## Questions for Retiring/Departing Developers

{bullet(syn.get('knowledge_capture_points', []), lambda x: f"{x['question']} — {x['category']} — Owner: {x['owner']}")}

## Possible Dynamic Targets (Unknown)

{bullet([dict(id=k, **v) for k, v in reach_data['nodes'].items() if v['status'] == 'unknown'], lambda x: f"`{x['id']}` — {x.get('reason', '')}", '- None')}

## SQL Objects Not Called From Application Code

{bullet([o for o in sql['objects'] if o['called_from_code'] == 'false'], lambda o: f"{o['qualified']} ({o['type']}) `{o['file']}:{o['line']}`" + (f" — referenced from SQL: {', '.join(o['sql_refs'])}" if o['sql_refs'] else ''))}

## SQL Objects With Unknown Call Status (Needs Verification)

{bullet([o for o in sql['objects'] if o['called_from_code'].startswith('unknown')], lambda o: f"{o['qualified']} ({o['type']}) `{o['file']}:{o['line']}`")}

## Orphaned References

{bullet(reach_data['orphaned'], lambda o: f"`{o.get('source')}` → `{o.get('ref')}` {o.get('site', '')} — {o.get('reason', '')}", '- None')}

## Citations That Failed Checking

{bullet(bad_cites, lambda x: x, '- None: every cited file:line exists')}

## Diagrams
- Class diagram: `context/brownfield/diagrams/class-diagram.mmd`
- System I/O map: `context/brownfield/diagrams/io-map.mmd`
- Information lifecycle: `context/brownfield/diagrams/lifecycle.mmd`
"""


def iter_cited(obj):
    if isinstance(obj, dict):
        if 'citation' in obj:
            yield obj
        for value in obj.values():
            yield from iter_cited(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from iter_cited(value)


# --- shards ------------------------------------------------------------------

def shards(graph, max_files=25, statuses=None, reachability=None):
    """One extraction shard per graph domain, split by folder when a domain has more than
    max_files leaves. Datastore leaves and leaves without a file are skipped. With
    `statuses`, only leaves whose computed reachability is in that set are kept."""
    status_of = (reachability or {}).get('nodes', {})
    out = []
    for domain in graph['root'].get('children') or []:
        leaves = [l for l in leaves_of(domain, {}).values() if l.get('file') and l.get('kind') != 'datastore']
        if statuses is not None:
            leaves = [l for l in leaves if status_of.get(l['id'], {}).get('status', 'unknown') in statuses]
        if not leaves:
            continue
        files = sorted({l['file'] for l in leaves})
        loc = {l['file']: l.get('loc') or 0 for l in leaves}
        name = domain.get('name') or domain['id']
        if len(files) <= max_files:
            groups = [(name, files)]
        else:
            by_dir = {}
            for f in files:
                by_dir.setdefault(os.path.dirname(f), []).append(f)
            groups, current, label = [], [], None
            for d in sorted(by_dir):
                for f in by_dir[d]:
                    if len(current) >= max_files:
                        groups.append((label, current)); current = []
                    if not current:
                        label = f"{name} / {os.path.basename(d) or d or '(root)'}"
                    current.append(f)
            if current:
                groups.append((label, current))
            seen = {}
            for i, (label, fs) in enumerate(groups):
                seen[label] = seen.get(label, 0) + 1
                if seen[label] > 1:
                    groups[i] = (f'{label} {seen[label]}', fs)
        for label, fs in groups:
            out.append({'name': label, 'domain': name, 'files': fs, 'loc': sum(loc[f] for f in fs)})
    return out


# --- security ----------------------------------------------------------------

SEVERITIES = ['Critical', 'High', 'Medium', 'Low']


def security_report(result, date):
    confirmed = sorted(result.get('confirmed') or [],
                       key=lambda f: (SEVERITIES.index(f['severity']) if f.get('severity') in SEVERITIES else 9,
                                      str(f.get('file')), f.get('line') or 0))
    refuted = result.get('refuted') or []
    counts = {s: sum(1 for f in confirmed if f.get('severity') == s) for s in SEVERITIES}
    one = lambda v, n=300: ' '.join(str(v if v is not None else '').split()).replace('|', '/')[:n]
    out = ['---', 'Status: Draft', f'Last Updated: {date}', 'Generated by: codebase-xray:security-sweep', '---', '',
           '# Security Findings', '',
           'Whole-codebase sweep against the OWASP-based checklist in `resources/standards/security-checklist.md`. '
           'Critical and High findings each survived two agents trying to refute them; Medium and Low were not '
           'panel-checked.', '',
           '| Severity | Count |', '|---|---|'] + [f'| {s} | {counts[s]} |' for s in SEVERITIES] + [
           '', f'{len(refuted)} Critical/High candidate(s) were refuted by the panel and are listed at the end.', '',
           '## Summary', '', '| ID | Severity | Title | Category | Location |', '|---|---|---|---|---|']
    for i, f in enumerate(confirmed, 1):
        f['id'] = f'SEC-{i:03d}'
        out.append(f"| {f['id']} | {one(f.get('severity'), 10)} | {one(f.get('title'), 90)} | "
                   f"{one(f.get('category'), 40)} | `{one(f.get('file'), 120)}:{f.get('line')}` |")
    for f in confirmed:
        out += ['', f"### {f['id']} [{one(f.get('severity'), 10)}] {one(f.get('title'), 120)}",
                f"- **Location:** `{one(f.get('file'), 160)}:{f.get('line')}`",
                f"- **Category:** {one(f.get('category'), 80)}",
                f"- **Problem:** {one(f.get('problem'), 800)}",
                f"- **Attack path:** {one(f.get('attack_path'), 800)}",
                f"- **Reachability:** {one(f.get('reachability') or 'unknown', 20)}",
                f"- **Recommendation:** {one(f.get('recommendation'), 800)}"]
        if f.get('citation') and f['citation'] != 'ok':
            out.append(f"- **Citation check:** {f['citation']}")
        if f.get('panel'):
            out.append(f"- **Panel:** {one(f['panel'], 600)}")
    if refuted:
        out += ['', '## Refuted by the panel', '']
        out += [f"- [{one(f.get('severity'), 10)}] {one(f.get('title'), 120)} (`{one(f.get('file'), 120)}:{f.get('line')}`): "
                f"{one(f.get('panel'), 400)}" for f in refuted]
    gaps = result.get('failedModules') or []
    if gaps:
        out += ['', '## Coverage gaps', '', 'These modules were not swept (agent failed): ' + ', '.join(map(str, gaps))]
    return '\n'.join(out) + '\n'


# --- cli ---------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('reach'); r.add_argument('graph'); r.add_argument('--out', required=True)
    s = sub.add_parser('sql'); s.add_argument('root'); s.add_argument('--out', required=True)
    c = sub.add_parser('cite'); c.add_argument('result'); c.add_argument('root')
    b = sub.add_parser('brief'); b.add_argument('xdir'); b.add_argument('--date', required=True)
    b.add_argument('--out', required=True)
    sh = sub.add_parser('shards'); sh.add_argument('graph'); sh.add_argument('--out', required=True)
    sh.add_argument('--max-files', type=int, default=25)
    sh.add_argument('--status', help='comma list of reachability statuses to keep; needs --reachability')
    sh.add_argument('--reachability')
    se = sub.add_parser('security'); se.add_argument('result'); se.add_argument('--date', required=True)
    se.add_argument('--out', required=True)
    a = p.parse_args(argv)

    if a.cmd == 'reach':
        data = reach(read_json(a.graph))
        write_json(a.out, data)
        print(f"reach: {data['counts']} from {len(data['entryPoints'])} entry point(s)")
    elif a.cmd == 'sql':
        data = sql_objects(a.root)
        write_json(a.out, data)
        by = {}
        for o in data['objects']:
            key = o['called_from_code'].split(' ')[0]
            by[key] = by.get(key, 0) + 1
        print(f"sql: {len(data['objects'])} object(s), called_from_code {by}; "
              f"{len(data['dynamicSqlSites'])} dynamic SQL site(s)")
    elif a.cmd == 'cite':
        result = read_json(a.result)
        tally = cite(result, a.root)
        write_json(a.result, result)
        print(f'cite: {tally}')
        if any(k != 'ok' for k in tally):
            print('cite: some citations failed; they are listed in the brief', file=sys.stderr)
    elif a.cmd == 'brief':
        with open(a.out, 'w') as fh:
            fh.write(brief(a.xdir, a.date))
        print(f'brief: wrote {a.out}')
    elif a.cmd == 'shards':
        statuses = set(a.status.split(',')) if a.status else None
        if statuses and not a.reachability:
            p.error('--status needs --reachability')
        rch = read_json(a.reachability) if a.reachability else None
        data = shards(read_json(a.graph), a.max_files, statuses, rch)
        write_json(a.out, data)
        print(f"shards: {len(data)} shard(s), {sum(len(m['files']) for m in data)} file(s), "
              f"{sum(m['loc'] for m in data)} LOC")
    elif a.cmd == 'security':
        with open(a.out, 'w') as fh:
            fh.write(security_report(read_json(a.result), a.date))
        print(f'security: wrote {a.out}')


if __name__ == '__main__':
    main()
