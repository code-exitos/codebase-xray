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


if __name__ == '__main__':
    unittest.main()
