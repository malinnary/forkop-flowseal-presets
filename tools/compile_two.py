"""Scoped YouTube/Discord adaptation, NOT a full clone of upstream routing."""
import json,re
from pathlib import Path
from compile_forkop import logical,ports,domains

ROOT=Path(__file__).resolve().parents[1]
PREFIX='/usr/share/forkop-flowseal/upstream'
YT=['youtube.com','youtu.be','googlevideo.com','ytimg.com','youtube-nocookie.com',
    'youtubekids.com','youtubei.googleapis.com','youtube.googleapis.com',
    'youtubeembeddedplayer.googleapis.com','jnn-pa.googleapis.com','yt3.ggpht.com',
    'yt4.ggpht.com','yt3.googleusercontent.com','wide-youtube.l.google.com',
    'youtube-ui.l.google.com','yt-video-upload.l.google.com','ytimg.l.google.com']
DISCORD=['discord.com','discord.gg','discord.media','discordapp.com','discordapp.net',
         'discordcdn.com','discord.app','dis.gd','discord-attachments-uploads-prd.storage.googleapis.com']

def clean(block):
    return [arg.replace('%BIN%',PREFIX+'/bin/') for arg in block
            if not arg.startswith(('--hostlist','--ipset'))]

def combine(blocks):
    result=[]
    for block in blocks:
        if result:result.append('--new')
        result.extend(clean(block))
    assert not any('%' in arg for arg in result)
    return result

def select(record):
    blocks=[b for b in record['blocks'] if not any('%GameFilter' in x or x.startswith('--ipset=') for x in b)]
    quic=next(b for b in blocks if '--filter-udp=443' in b or '--filter-l7=quic' in b)
    voice=next(b for b in blocks if any(x.startswith('--filter-l7=discord,stun') for x in b))
    google=next((b for b in blocks if '--hostlist=%LISTS%list-google.txt' in b),None)
    common=next((b for b in blocks if '--filter-tcp=80,443' in b),None)
    media=next((b for b in blocks if '--hostlist-domains=discord.media' in b),None)
    if google is None or common is None:
        # ALT5 intentionally supplies one generic IPv4 TCP block for both services.
        generic=[b for b in blocks if any(x.startswith('--filter-tcp=') for x in b)]
        if len(generic)!=1:raise ValueError('Unknown upstream block layout: '+record['name'])
        google=common=generic[0]
    return [quic,google],[quic,voice]+([media] if media else [])+[common]

def compile_record(record):
    youtube,discord=select(record)
    yt_route=logical('and',[domains(YT),logical('or',[ports('tcp','80,443'),ports('udp','443')])])
    discord_route=logical('or',[
        logical('and',[domains(DISCORD),logical('or',[ports('tcp','80,443,2053,2083,2087,2096,8443'),ports('udp','443')])]),
        ports('udp','19294-19344,50000-50100')])
    blocks=[]
    for name,args,route in [('youtube',combine(youtube),yt_route),('discord',combine(discord),discord_route)]:
        blocks.append({'id':'block-'+name,'args':args,'route':{'version':3,'rules':[route]}})
    return {'id':re.sub(r'[^a-z0-9]+','-',record['name'].lower()).strip('-'),'name':record['name'],'blocks':blocks}

if __name__=='__main__':
    manifest=json.loads((ROOT/'dist/inventory/manifest.json').read_text(encoding='utf-8'))
    output=ROOT/'dist/two-sections';output.mkdir(exist_ok=False)
    records=[compile_record(record) for record in manifest['strategies']]
    for record in records:
        directory=output/record['id'];directory.mkdir()
        for block in record['blocks']:
            (directory/(block['id']+'.opts')).write_bytes((' '.join(block['args'])+'\n').encode())
            (directory/(block['id']+'.json')).write_text(json.dumps(block['route'],indent=2),encoding='utf-8')
    (output/'compiled.json').write_text(json.dumps({'upstream':manifest['upstream'],'presets':records},indent=2),encoding='utf-8')
    print('Compiled',len(records),'scoped presets, exactly two sections each')
