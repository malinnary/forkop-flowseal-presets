import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('importer',Path(__file__).resolve().parents[1]/'tools/import_upstream.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
export_spec=importlib.util.spec_from_file_location('exporter',Path(__file__).resolve().parents[1]/'tools/export_candidates.py')
exporter=importlib.util.module_from_spec(export_spec)
export_spec.loader.exec_module(exporter)

class ImportTests(unittest.TestCase):
    def test_cmd_escaping_and_boundaries(self):
        parsed=module.parse_strategy('start "zapret" /min "%BIN%winws.exe" --wf-tcp=443 ^\n--filter-tcp=443 --dpi-desync-fake-tls=^! --new ^\n--filter-udp=%GameFilterUDP% --dpi-desync=fake\n')
        self.assertEqual(len(parsed['blocks']),2)
        self.assertIn('--dpi-desync-fake-tls=!',parsed['blocks'][0])
        self.assertEqual(parsed['runtime_variables'],['GameFilterUDP'])
        self.assertEqual(parsed['capture_options'],['--wf-tcp=443'])

    def test_reject_commands(self):
        with self.assertRaises(ValueError):
            module.parse_strategy('start "zapret" /min "%BIN%winws.exe" --filter-tcp=443 & malicious\n')

    def test_reject_unknown_launcher(self):
        with self.assertRaises(ValueError): module.parse_strategy('echo changed upstream')

    def test_export_preserves_filters_and_duplicate_arguments(self):
        args,omitted=exporter.convert({'blocks':[
            ['--filter-tcp=443','--hostlist=%LISTS%a.txt','--dpi-desync-fake-tls=0x00','--dpi-desync-fake-tls=!'],
            ['--filter-udp=%GameFilterUDP%','--dpi-desync=fake']]},'/test')
        self.assertEqual(omitted,[1])
        self.assertIn('--hostlist=/test/lists/a.txt',args)
        self.assertEqual(sum(x.startswith('--dpi-desync-fake-tls=') for x in args),2)

    def test_export_rejects_unresolved_variable(self):
        with self.assertRaises(ValueError): exporter.convert({'blocks':[['--filter-tcp=%UNKNOWN%']]},'/test')

if __name__=='__main__': unittest.main()
