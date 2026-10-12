import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import xray  # noqa: E402


def graph(leaves, edges, entries, **extra):
    root = {'id': 'sys', 'kind': 'system', 'children': [
        {'id': 'dom:a', 'kind': 'domain', 'children': [{'id': i, 'name': i, 'kind': 'module', 'file': f'{i}.py'}
                                                     for i in leaves]}]}
    return {'root': root, 'edges': [{'source': s, 'target': t, 'kind': 'call'} for s, t in edges],
            'entryPoints': entries, **extra}


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fh:
        fh.write(text)


class ReachTest(unittest.TestCase):
    def test_classifies_from_entry_points(self):
        data = xray.reach(graph(['main', 'svc', 'old'], [('main', 'svc')], ['main']))
        status = {k: v['status'] for k, v in data['nodes'].items()}
        self.assertEqual(status, {'main': 'active', 'svc': 'active', 'old': 'dormant'})
        self.assertEqual(data['nodes']['svc']['via'], ['main', 'svc'])

    def test_edge_from_dormant_node_does_not_activate(self):
        data = xray.reach(graph(['main', 'a', 'b'], [('a', 'b')], ['main']))
        self.assertEqual(data['nodes']['b']['status'], 'dormant')

    def test_cycles_terminate(self):
        data = xray.reach(graph(['main', 'a', 'b'], [('main', 'a'), ('a', 'b'), ('b', 'a')], ['main']))
        self.assertEqual(data['counts']['active'], 3)

    def test_possible_dynamic_target_is_unknown_not_dormant(self):
        g = graph(['main', 'plugin'], [], ['main'],
                  dynamicTargets=[{'id': 'plugin', 'reason': 'Class.forName(name)', 'site': 'main.py:3'}])
        self.assertEqual(xray.reach(g)['nodes']['plugin']['status'], 'unknown')

    def test_unbounded_dynamic_makes_every_unreached_node_unknown(self):
        g = graph(['main', 'a', 'b'], [], ['main'], unboundedDynamic=[{'site': 'main.py:9'}])
        data = xray.reach(g)
        self.assertEqual(data['counts']['dormant'], 0)
        self.assertEqual(data['counts']['unknown'], 2)

    def test_no_entry_points_refuses(self):
        with self.assertRaises(SystemExit):
            xray.reach(graph(['a'], [], []))

    def test_unknown_entry_point_refuses(self):
        with self.assertRaises(SystemExit):
            xray.reach(graph(['a'], [], ['nope']))

    def test_dangling_edge_is_orphaned(self):
        data = xray.reach(graph(['main'], [('main', 'Gone')], ['main']))
        self.assertEqual(data['counts']['orphaned'], 1)
        self.assertEqual(data['orphaned'][0]['ref'], 'Gone')


class SqlTest(unittest.TestCase):
    def test_call_status(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'db/procs.sql', 'CREATE PROCEDURE [dbo].[usp_Used] AS\nGO\n'
                                        'CREATE OR ALTER PROC dbo.usp_Unused AS\nGO\n'
                                        'CREATE TRIGGER trg_Audit ON T AFTER INSERT AS\n')
            write(root, 'app/repo.cs', 'cmd.CommandText = "usp_Used";\n')
            objs = {o['name']: o for o in xray.sql_objects(root)['objects']}
            self.assertEqual(objs['usp_Used']['called_from_code'], 'true')
            self.assertEqual(objs['usp_Used']['code_refs'], ['app/repo.cs:1'])
            self.assertEqual(objs['usp_Unused']['called_from_code'], 'false')
            self.assertEqual(objs['usp_Unused']['type'], 'procedure')
            self.assertTrue(objs['trg_Audit']['called_from_code'].startswith('n/a'))

    def test_dynamic_sql_downgrades_false_to_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'db/p.sql', 'CREATE PROCEDURE usp_Maybe AS\n')
            write(root, 'db/run.sql', "EXEC sp_executesql @sql\n")
            obj = xray.sql_objects(root)['objects'][0]
            self.assertTrue(obj['called_from_code'].startswith('unknown'))

    def test_skips_vendored_dirs(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'db/p.sql', 'CREATE VIEW v_Thing AS SELECT 1\n')
            write(root, 'node_modules/x/index.js', 'v_Thing\n')
            self.assertEqual(xray.sql_objects(root)['objects'][0]['called_from_code'], 'false')


class CiteTest(unittest.TestCase):
    def test_annotates_every_citation(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'a.py', 'one\ntwo\n')
            result = {'classes': [{'name': 'A', 'file': 'a.py', 'line': 2},
                                  {'name': 'B', 'file': 'a.py', 'line': 99},
                                  {'name': 'C', 'file': 'nope.py', 'line': 1}],
                      'x': {'y': [{'file': '../../etc/passwd', 'line': 1}]}}
            xray.cite(result, root)
            self.assertEqual([c['citation'] for c in result['classes']], ['ok', 'bad-line', 'missing-file'])
            self.assertEqual(result['x']['y'][0]['citation'], 'outside-root')

    def test_line_ranges_check_first_line(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'a.py', 'x\n' * 10)
            result = {'f': {'file': 'a.py', 'line': '3-7'}}
            xray.cite(result, root)
            self.assertEqual(result['f']['citation'], 'ok')


class BriefTest(unittest.TestCase):
    def test_renders_sections(self):
        with tempfile.TemporaryDirectory() as d:
            json.dump(xray.reach(graph(['main', 'old'], [], ['main'], method='madge')),
                      open(os.path.join(d, 'reachability.json'), 'w'))
            json.dump({'objects': [], 'dynamicSqlSites': []}, open(os.path.join(d, 'sql-objects.json'), 'w'))
            json.dump({'modules': ['core'], 'failedModules': ['legacy'],
                       'classes': [{'name': 'Old', 'reachability': 'dormant'}], 'ioSurfaces': [],
                       'synthesis': {'load_bearing': [], 'knowledge_capture_points': []},
                       'safeToDrop': [{'item': 'old', 'file': 'old.py', 'line': 1, 'evidence': 'no inbound edges'}],
                       'contested': []}, open(os.path.join(d, 'xray-result.json'), 'w'))
            md = xray.brief(d, '2026-10-12')
            self.assertIn('Last Updated: 2026-10-12', md)
            self.assertIn('| Graph nodes | 1 | 1 | 0 | 0 |', md)
            self.assertIn('**Incomplete scan.**', md)
            self.assertIn('**old** `old.py:1`', md)
            self.assertIn('graph built with madge', md)


class ShardsTest(unittest.TestCase):
    def tree(self, n):
        leaves = [{'id': f'l{i}', 'kind': 'module', 'file': f"A/{'x' if i < n // 2 else 'y'}/f{i}.vb", 'loc': 10}
                  for i in range(n)]
        return {'root': {'id': 'sys', 'kind': 'system', 'children': [
            {'id': 'dom:a', 'name': 'A', 'kind': 'domain', 'children': leaves},
            {'id': 'dom:data', 'name': 'Data stores', 'kind': 'domain',
             'children': [{'id': 'ds:t', 'name': 't', 'kind': 'datastore'}]}]}}

    def test_one_shard_per_domain_skipping_datastores(self):
        out = xray.shards(self.tree(4))
        self.assertEqual([m['name'] for m in out], ['A'])
        self.assertEqual(out[0]['loc'], 40)

    def test_large_domain_splits_by_folder_with_unique_names(self):
        out = xray.shards(self.tree(60), max_files=25)
        self.assertTrue(all(len(m['files']) <= 25 for m in out))
        self.assertEqual(sum(len(m['files']) for m in out), 60)
        self.assertEqual(len({m['name'] for m in out}), len(out))
        for m in out:  # a shard's label names every folder its files come from
            for f in m['files']:
                self.assertIn(os.path.basename(os.path.dirname(f)), m['name'])

    def test_status_filter(self):
        rch = {'nodes': {'l0': {'status': 'active'}, 'l1': {'status': 'dormant'}}}
        out = xray.shards(self.tree(2), statuses={'active'}, reachability=rch)
        self.assertEqual(out[0]['files'], ['A/x/f0.vb'])


class SecurityReportTest(unittest.TestCase):
    def test_orders_by_severity_and_numbers(self):
        md = xray.security_report({'confirmed': [
            {'severity': 'Medium', 'title': 'm', 'file': 'a.vb', 'line': 1},
            {'severity': 'Critical', 'title': 'sqli | x', 'file': 'b.vb', 'line': 2}],
            'refuted': [{'severity': 'High', 'title': 'r', 'file': 'c.vb', 'line': 3, 'panel': 'input is constant'}]},
            '2026-10-12')
        self.assertLess(md.index('SEC-001 [Critical]'), md.index('SEC-002 [Medium]'))
        self.assertIn('sqli / x', md)
        self.assertIn('## Refuted by the panel', md)
        self.assertIn('| Critical | 1 |', md)


class SqlDynamicTest(unittest.TestCase):
    def test_js_exec_is_not_dynamic_sql_and_built_names_are_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, 'db/s.sql', 'CREATE PROCEDURE fetchCustomer AS SELECT 1\nGO\nCREATE PROCEDURE rptOld AS SELECT 1\n')
            write(root, 'web/js/jquery.js', 'var m = re.exec(s);\n')
            write(root, 'app/Db.vb', 'cmd.CommandText = "fetch" & LookupName\n')
            data = xray.sql_objects(root)
            status = {o['name']: o['called_from_code'] for o in data['objects']}
            self.assertEqual(data['dynamicSqlSites'], [])
            self.assertTrue(status['fetchCustomer'].startswith('unknown'))
            self.assertEqual(status['rptOld'], 'false')


if __name__ == '__main__':
    unittest.main()
