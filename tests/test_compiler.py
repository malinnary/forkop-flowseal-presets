import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('compiler',Path(__file__).resolve().parents[1]/'tools/compile_forkop.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CompilerTests(unittest.TestCase):
    def test_strict_domain(self):
        self.assertEqual(c.domains(['^dns.google','youtube.com']),{'domain':['dns.google'],'domain_suffix':['youtube.com']})
    def test_port_ranges(self):
        self.assertEqual(c.ports('udp','443,50000-50100'),{'network':'udp','port':[443],'port_range':['50000:50100']})
    def test_exclusion_and_preserved_payload(self):
        result=c.compile_block(['--filter-tcp=443','--hostlist-domains=a.com','--hostlist-exclude-domains=x.a.com','--dpi-desync=fake'],Path('.'),'/test',[])
        self.assertEqual(result['args'],['--filter-tcp=443','--dpi-desync=fake'])
        self.assertEqual(result['route']['rules'][0]['rules'][-1],{'domain_suffix':['x.a.com'],'invert':True})
    def test_games_are_explicitly_omitted(self):
        self.assertIsNone(c.compile_block(['--filter-udp=%GameFilterUDP%'],Path('.'),'/test',[]))
    def test_missing_dependency_rejected(self):
        with self.assertRaises(FileNotFoundError):c.lines(Path('.'),'%LISTS%unexpected.txt')

if __name__=='__main__':unittest.main()
