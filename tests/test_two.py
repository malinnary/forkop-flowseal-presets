import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from compile_two import compile_record

class TwoSectionsTests(unittest.TestCase):
    def test_all_pinned_presets(self):
        path=ROOT/'dist/inventory/manifest.json'
        if not path.exists():self.skipTest('Import pinned upstream first')
        source=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(len(source['strategies']),22)
        for strategy in source['strategies']:
            with self.subTest(strategy=strategy['name']):
                output=compile_record(strategy)
                self.assertEqual([b['id'] for b in output['blocks']],['block-youtube','block-discord'])
                for block in output['blocks']:
                    self.assertFalse(any(a.startswith(('--hostlist','--ipset')) for a in block['args']))
                    self.assertFalse(any('%' in a for a in block['args']))
                    self.assertIn('--new',block['args'])
                self.assertFalse(any('50000-50100' in a for a in output['blocks'][0]['args']))
                self.assertTrue(any('50000-50100' in a for a in output['blocks'][1]['args']))

if __name__=='__main__':unittest.main()
