"""Compile ordered upstream blocks to Forkop route + nfqws pairs.

Experimental: sing-box and nfqws hostname/L7 discovery are not equivalent.
No automatic installation or network interception is performed here.
"""
import argparse
import ipaddress
import json
import re
from pathlib import Path


def logical(mode, rules):
    assert rules
    return rules[0] if len(rules)==1 else {'type':'logical','mode':mode,'rules':rules}


def domains(values):
    rule={}
    for value in values:
        exact=value.startswith('^')
        value=value.removeprefix('^').lower()
        if not re.fullmatch(r'[a-z0-9_.-]+',value): raise ValueError('Unsupported hostlist syntax: '+value)
        rule.setdefault('domain' if exact else 'domain_suffix',[]).append(value)
    return rule


def ports(network,value):
    rule={'network':network}
    for token in value.split(','):
        if re.fullmatch(r'\d+',token): rule.setdefault('port',[]).append(int(token))
        elif re.fullmatch(r'\d+-\d+',token): rule.setdefault('port_range',[]).append(token.replace('-',':'))
        else: raise ValueError('Unsupported port: '+token)
    return rule


def lines(root,reference):
    if not reference.startswith('%LISTS%'): raise ValueError('Unexpected list path')
    name=reference.removeprefix('%LISTS%')
    if '/' in name or '\\' in name: raise ValueError('Unsafe list path')
    path=root/'lists'/name
    if not path.exists():
        if name in {'list-general-user.txt','list-exclude-user.txt','ipset-exclude-user.txt'}: return []
        raise FileNotFoundError(path)
    return [s.strip() for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip() and not s.lstrip().startswith('#')]


def compile_block(block,root,prefix,capture):
    if any('%GameFilter' in token for token in block): return None
    inc=[];exc=[];ips=[];ip_exc=[];filters=[];opts=[];l7=[]
    for token in block:
        key,_,value=token.partition('=')
        if key in ('--hostlist','--hostlist-exclude'):
            (inc if key=='--hostlist' else exc).extend(lines(root,value))
        elif key in ('--hostlist-domains','--hostlist-exclude-domains'):
            (inc if key=='--hostlist-domains' else exc).extend(value.split(','))
        elif key in ('--ipset','--ipset-exclude'):
            (ips if key=='--ipset' else ip_exc).extend(lines(root,value))
        else:
            if key in ('--filter-tcp','--filter-udp'): filters.append(ports(key.removeprefix('--filter-'),value))
            if key=='--filter-l7': l7=value.split(',')
            token=token.replace('%BIN%',prefix+'/bin/')
            if '%' in token or any(ch.isspace() for ch in token): raise ValueError('Unresolved option')
            opts.append(token)
    if not filters:
        # Respect original WinDivert capture envelope for e.g. EXP's QUIC-only block.
        for token in capture:
            key,_,value=token.partition('=')
            value=','.join(v for v in value.split(',') if '%' not in v)
            filters.append(ports(key.removeprefix('--wf-'),value))
    conditions=[logical('or',filters)]
    if inc: conditions.append(domains(inc))
    if ips: conditions.append({'ip_cidr':[str(ipaddress.ip_network(i,strict=False)) for i in ips]})
    if exc: conditions.append({**domains(exc),'invert':True})
    if ip_exc: conditions.append({'ip_cidr':[str(ipaddress.ip_network(i,strict=False)) for i in ip_exc],'invert':True})
    # QUIC has a corresponding sing-box sniff protocol. Discord/STUN/unknown
    # stay checked inside nfqws; document the broader route selection explicitly.
    if l7==['quic']: conditions.append({'protocol':['quic']})
    return {'route':{'version':3,'rules':[logical('and',conditions)]},'args':opts,
            'l7_checked_by_nfqws':l7,'experimental':True}


def build(inventory,output,prefix):
    manifest=json.loads((inventory/'manifest.json').read_text(encoding='utf-8'))
    output.mkdir(parents=True,exist_ok=False)
    records=[]
    for strategy in manifest['strategies']:
        name=re.sub(r'[^a-z0-9]+','-',strategy['name'].lower()).strip('-')
        dest=output/name;dest.mkdir()
        blocks=[]
        for index,block in enumerate(strategy['blocks']):
            converted=compile_block(block,inventory/'upstream',prefix,strategy['capture_options'])
            if converted is None:continue
            ident=f'block-{index:02d}'
            (dest/(ident+'.json')).write_text(json.dumps(converted['route'],indent=2)+'\n',encoding='utf-8')
            (dest/(ident+'.opts')).write_bytes((' '.join(converted['args'])+'\n').encode('utf-8'))
            blocks.append({'id':ident,**converted})
        records.append({'id':name,'name':strategy['name'],'blocks':blocks})
    (output/'compiled.json').write_text(json.dumps({'upstream':manifest['upstream'],'presets':records},indent=2)+'\n',encoding='utf-8')
    print('Compiled',len(records),'presets;',sum(len(x['blocks']) for x in records),'ordered route/strategy pairs')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('inventory',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prefix',default='/usr/share/forkop-flowseal/upstream')
    a=p.parse_args();build(a.inventory,a.output,a.prefix)
