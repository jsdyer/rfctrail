#!/usr/bin/env python3
"""Collect the public RFC Editor metadata index, validate, then publish atomically."""
import argparse, calendar, datetime as dt, gzip, hashlib, json, re, shutil, tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RELATIONS = {'obsoletes':'obsoletes','obsoleted-by':'obsoletedBy','updates':'updates','updated-by':'updatedBy'}
MONTHS = {name:i for i,name in enumerate(calendar.month_name) if name}
def parse_source(raw, config):
    if len(raw)>config['maximumSourceBytes'] or b'<!DOCTYPE' in raw.upper(): raise ValueError('Unexpected XML size or document type')
    root=ET.fromstring(raw)
    if root.tag.rsplit('}',1)[-1]!='rfc-index': raise ValueError('Not an RFC index')
    for e in root.iter(): e.tag=e.tag.rsplit('}',1)[-1]
    records=[]; seen=set()
    for entry in root.findall('rfc-entry'):
        code=entry.findtext('doc-id','')
        if not re.fullmatch(r'RFC[0-9]{1,6}',code): raise ValueError('Invalid RFC identity')
        number=int(code[3:])
        if number<1 or number in seen: raise ValueError('Duplicate RFC identity')
        seen.add(number)
        title=' '.join(entry.findtext('title','').split())
        if not title: raise ValueError('RFC has no title')
        year=entry.findtext('date/year',''); month=entry.findtext('date/month','')
        if not year.isdigit() or not 1900<=int(year)<=dt.datetime.now(dt.timezone.utc).year+1 or month not in MONTHS: raise ValueError('Invalid publication month')
        date=f'{int(year):04d}-{MONTHS[month]:02d}'
        r={'id':number,'title':title,'date':date,'authors':[x.text for x in entry.findall('author/name') if x.text], 'status':entry.findtext('current-status','UNKNOWN'), 'publicationStatus':entry.findtext('publication-status','UNKNOWN'), 'stream':entry.findtext('stream','Unknown'), 'area':entry.findtext('area',''), 'group':entry.findtext('wg_acronym',''), 'draft':entry.findtext('draft',''), 'also':[x.text for x in entry.findall('is-also/doc-id') if x.text], 'keywords':[x.text for x in entry.findall('keywords/kw') if x.text]}
        for source,target in RELATIONS.items():
            values=[x.text for x in entry.findall(source+'/doc-id')]
            if any(not re.fullmatch(r'RFC[0-9]{1,6}',x or '') for x in values): raise ValueError('Invalid relationship identity')
            r[target]=sorted(set(int(x[3:]) for x in values))
        if r['draft'] and not re.fullmatch(r'draft-[a-zA-Z0-9_.-]+',r['draft']): raise ValueError('Invalid draft name')
        records.append(r)
    if not config['minimumRecords']<=len(records)<=config['maximumRecords']: raise ValueError('Source count outside configured bounds')
    return sorted(records,key=lambda x:x['id'])
def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def collect(root=ROOT, source_file=None, now=None):
    cfg=json.loads((root/'web/config.json').read_text()); now=now or dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if not 1<=cfg['retainedCaptures']<=52:raise ValueError('retainedCaptures must be 1–52')
    if cfg['sourceUrl']!='https://www.rfc-editor.org/rfc-index.xml':raise ValueError('Use the documented official RFC index URL')
    old_path=root/'web/data/index.json'; old=json.loads(old_path.read_text()) if old_path.exists() else {'captures':[]}
    if source_file: raw=Path(source_file).read_bytes(); etag=None
    else:
        req=urllib.request.Request(cfg['sourceUrl'],headers={'User-Agent':'CoolCode RFC Trail/1.0 (https://coolcode.ca/rfctrail/)','Accept':'application/xml,text/xml;q=0.9,*/*;q=0.5'})
        with urllib.request.urlopen(req,timeout=60) as response:
            raw=response.read(cfg['maximumSourceBytes']+1); etag=response.headers.get('ETag')
    records=parse_source(raw,cfg); digest=hashlib.sha256(raw).hexdigest()
    previous=old['captures'][0] if old['captures'] else None
    if previous and len(records)<previous['recordCount']*(1-cfg['maximumDropFraction']):raise ValueError('Unexpected record-count drop; existing capture preserved')
    with tempfile.TemporaryDirectory(dir=root,prefix='.refresh-') as temp:
        stage=Path(temp)/'data'
        if (root/'web/data').exists():shutil.copytree(root/'web/data',stage)
        else:stage.mkdir()
        captures=old['captures']
        if not previous or previous['sourceSha256']!=digest:
            ident=now.replace('-','').replace(':','')+'-'+digest[:10]; relative='captures/'+ident+'.json.gz'
            capture={'schema':'coolcode.rfctrail.v1','capturedAt':now,'source':cfg['sourceUrl'],'sourceSha256':digest,'coverage':'All published RFC entries in the RFC Editor index','records':records}
            packed=gzip.compress((json.dumps(capture,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0)
            (stage/'captures').mkdir(exist_ok=True);(stage/relative).write_bytes(packed)
            entry={'id':ident,'file':relative,'capturedAt':now,'recordCount':len(records),'sourceSha256':digest,'sha256':hashlib.sha256(packed).hexdigest(),'bytes':len(packed),'through':max(r['date'] for r in records)}
            captures=[entry]+captures
        captures=captures[:cfg['retainedCaptures']]
        keep={x['file'] for x in captures}
        for p in (stage/'captures').glob('*.json.gz'):
            if p.relative_to(stage).as_posix() not in keep:p.unlink()
        index={'schema':'coolcode.rfctrail.index.v1','checkedAt':now,'source':cfg['sourceUrl'],'sourceEtag':etag,'captures':captures}
        write_json(stage/'index.json',index)
        write_json(stage/'status.json',{'checkedAt':now,'capturedAt':captures[0]['capturedAt'],'records':len(records),'through':max(r['date'] for r in records),'retainedCaptures':len(captures),'source':cfg['sourceUrl'],'sourceSha256':digest})
        target=root/'web/data';backup=root/'web/.data-backup'
        if backup.exists():shutil.rmtree(backup)
        if target.exists():target.rename(backup)
        try:stage.rename(target)
        except BaseException:
            if backup.exists():backup.rename(target)
            raise
        if backup.exists():shutil.rmtree(backup)
    print(f'{len(records):,} RFC records; {len(captures)} retained capture(s); checked {now}')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-file',type=Path);args=parser.parse_args();collect(source_file=args.source_file)
