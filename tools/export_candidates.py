"""Export review-only nfqws candidates; never modify a router."""
import argparse
import json
import re
import shlex
from pathlib import Path


def convert(record, prefix):
    blocks=[]
    omitted=[]
    for index, block in enumerate(record['blocks']):
        # Explicit policy: preserve service rules, omit optional game-port rules.
        if any('%GameFilter' in arg for arg in block):
            omitted.append(index)
            continue
        result=[]
        for arg in block:
            arg=arg.replace('%BIN%',prefix+'/bin/').replace('%LISTS%',prefix+'/lists/')
            if '%' in arg or arg.startswith('--wf-'):
                raise ValueError('Unresolved Windows option')
            result.append(arg)
        if blocks: blocks.append('--new')
        blocks.extend(result)
    return blocks, omitted


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('inventory',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--prefix',default='/usr/share/forkop-flowseal/upstream')
    a=p.parse_args()
    if not re.fullmatch(r'/[a-zA-Z0-9/_-]+',a.prefix): raise ValueError('Unsafe prefix')
    manifest=json.loads((a.inventory/'manifest.json').read_text(encoding='utf-8'))
    a.output.mkdir(parents=True,exist_ok=False)
    report=[]
    for record in manifest['strategies']:
        name=re.sub(r'[^a-z0-9]+','-',record['name'].lower()).strip('-')
        argv,omitted=convert(record,a.prefix)
        (a.output/(name+'.args.json')).write_text(json.dumps(argv,indent=2)+'\n',encoding='utf-8')
        (a.output/(name+'.opts')).write_text(shlex.join(argv)+'\n',encoding='utf-8')
        missing=[folder+'/'+file for kind,file in record['references']
                 for folder in ['bin' if kind=='BIN' else 'lists']
                 if not (a.inventory/'upstream'/folder/file).is_file()]
        report.append({'name':name,'status':'review-only','omitted_optional_game_blocks':omitted,
                       'missing_files':missing,'capture_options_for_forkop_review':record['capture_options']})
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Exported',len(report),'review-only candidates; not installable.')
