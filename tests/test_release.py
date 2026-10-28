import base64
import hashlib
import io
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ReleaseTests(unittest.TestCase):
    def test_built_installer(self):
        path = ROOT / 'dist/forkop-flowseal-install.run'
        if not path.exists(): self.skipTest('Run tools/build_release.py first')
        header, encoded = path.read_bytes().split(b'\n__FLOWSEAL_PAYLOAD__\n', 1)
        payload = base64.b64decode(encoded)
        self.assertIn(hashlib.sha256(payload).hexdigest().encode(), header)
        with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tar:
            names=tar.getnames()
            for name in names:
                self.assertFalse(name.startswith('/') or '..' in name.split('/'))
                self.assertFalse(name.endswith(('.exe','.dll','.sys','.private.tar.gz')))
            for line in tar.extractfile('SHA256SUMS').read().decode().splitlines():
                digest,name=line.split('  ',1)
                self.assertEqual(hashlib.sha256(tar.extractfile(name).read()).hexdigest(),digest)
            inventory=tar.extractfile('install-files.txt').read().decode().splitlines()
            self.assertEqual(sorted('root/'+name for name in inventory),sorted(n for n in names if n.startswith('root/')))
            self.assertEqual(len({n.split('/')[5] for n in names if n.startswith('root/usr/share/forkop-flowseal/presets-v2/')}),22)
