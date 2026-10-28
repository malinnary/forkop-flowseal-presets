import os
import subprocess
import tempfile
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
        header, payload = path.read_bytes().split(b'\n__FLOWSEAL_PAYLOAD__\n', 1)
        self.assertNotIn(b'base64', header)
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

    @unittest.skipUnless(os.name == 'posix', 'Requires POSIX shell')
    def test_shell_extract_only(self):
        path = ROOT / 'dist/forkop-flowseal-install.run'
        if not path.exists(): self.skipTest('Build first')
        header, payload = path.read_bytes().split(b'\n__FLOWSEAL_PAYLOAD__\n', 1)
        # Exercise the real extraction/checksum logic, but never install anything on CI.
        header=b'\n'.join(line for line in header.split(b'\n') if not line.startswith((b'[ "$(id -u)"',b'[ -r /etc/openwrt_release ]')))
        header=header.replace(b'sh "$task_dir/install.sh"', b'test -f "$task_dir/install.sh" && echo EXTRACT_OK')
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'test.run'
            script.write_bytes(header+b'\n__FLOWSEAL_PAYLOAD__\n'+payload)
            result=subprocess.run(['sh',str(script)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('EXTRACT_OK',result.stdout)
