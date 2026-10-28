"""Build an allowlisted alpha archive. No credentials or router backups allowed."""
import hashlib
import io
import json
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
inventory=root/'dist/inventory'
compiled=root/'dist/two-sections'
files={}
def add(path,data,mode=0o644):
    assert path not in files
    files[path]=(data,mode)
for folder in sorted(compiled.iterdir()):
    if not folder.is_dir():continue
    for path in folder.iterdir():
        assert path.suffix in {'.json','.opts'}
        add('root/usr/share/forkop-flowseal/presets-v2/'+folder.name+'/'+path.name,path.read_bytes().replace(b'\r\n',b'\n'))
names=sorted(p.name for p in compiled.iterdir() if p.is_dir())
assert len(names)==22
add('root/usr/share/forkop-flowseal/catalog.txt',('\n'.join(names)+'\n').encode())
for path in (inventory/'upstream/bin').glob('*.bin'):
    add('root/usr/share/forkop-flowseal/upstream/bin/'+path.name,path.read_bytes())
for filename,target,mode in [
    ('flowseal-presets','root/usr/sbin/flowseal-presets',0o755),
    ('flowseal-presets.js','root/www/luci-static/resources/view/flowseal-presets.js',0o644),
    ('menu.json','root/usr/share/luci/menu.d/flowseal-presets.json',0o644),
    ('acl.json','root/usr/share/rpcd/acl.d/flowseal-presets.json',0o644),
    ('install.sh','install.sh',0o755),('dependencies.sh','dependencies.sh',0o755),
    ('forkop-packages.sha256','forkop-packages.sha256',0o644),
    ('uninstall.sh','uninstall.sh',0o755)]:
    add(target,(root/'files'/filename).read_bytes().replace(b'\r\n',b'\n'),mode)
add('root/usr/share/forkop-flowseal/LICENSE.flowseal.txt',(inventory/'LICENSE.flowseal.txt').read_bytes())
add('root/usr/share/forkop-flowseal/upstream.lock.json',(root/'upstream.lock.json').read_bytes())
for filename in ['README.md','TESTING.md','LICENSE','RELEASE_NOTES.md']:add(filename,(root/filename).read_bytes())
add('install-files.txt', ''.join(p.removeprefix('root/')+'\n' for p in sorted(files) if p.startswith('root/')).encode())
checksums=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,(data,_) in sorted(files.items()))
add('SHA256SUMS',checksums.encode())
target=root/'dist/forkop-flowseal-alpha.tar.gz'
with tarfile.open(target,'w:gz') as archive:
    for name,(data,mode) in sorted(files.items()):
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode
        archive.addfile(info,io.BytesIO(data))
print('Built',target.name,'files:',len(files),'sha256:',hashlib.sha256(target.read_bytes()).hexdigest())
payload=target.read_bytes()
header=(root/'files/selfextract.sh').read_text(encoding='utf-8').replace('@SHA256@',hashlib.sha256(payload).hexdigest())
installer=root/'dist/forkop-flowseal-install.run'
installer.write_bytes(header.encode()+payload)
installer.with_suffix('.run.sha256').write_text(hashlib.sha256(installer.read_bytes()).hexdigest()+'  '+installer.name+'\n',encoding='ascii')
print('One-command installer:',installer)
