export const RELATIONS=['obsoletes','obsoletedBy','updates','updatedBy'];
export const LABELS={obsoletes:'Obsoletes',obsoletedBy:'Obsoleted by',updates:'Updates',updatedBy:'Updated by'};
export function validateCapture(data){
 if(!data||data.schema!=='coolcode.rfctrail.v1'||!Number.isFinite(Date.parse(data.capturedAt))||!Array.isArray(data.records)||!data.records.length||data.records.length>30000)throw Error('Unrecognized RFC capture.');
 const seen=new Set();
 for(const r of data.records){if(!Number.isInteger(r.id)||r.id<1||r.id>999999||seen.has(r.id)||typeof r.title!=='string'||!r.title||!/^\d{4}-\d{2}$/.test(r.date)||Number(r.date.slice(5))<1||Number(r.date.slice(5))>12||!['status','publicationStatus','stream','area','group','draft'].every(k=>typeof r[k]==='string')||!['authors','keywords','also'].every(k=>Array.isArray(r[k])&&r[k].every(x=>typeof x==='string'))||!RELATIONS.every(k=>Array.isArray(r[k])&&r[k].every(n=>Number.isInteger(n)&&n>0&&n<=999999))||(r.draft&&!/^draft-[a-zA-Z0-9_.-]+$/.test(r.draft)))throw Error('Invalid or duplicate RFC record.');seen.add(r.id);}
 return data;
}
export function filterRecords(records,{query='',status='',stream='',from='',to='',sort='newest'}={}){
 const low=from===''?null:Number(from),high=to===''?null:Number(to);if((low!==null&&(!Number.isInteger(low)||low<1900||low>2200))||(high!==null&&(!Number.isInteger(high)||high<1900||high>2200))||(low!==null&&high!==null&&low>high))throw Error('Use years from 1900 to 2200, with the start no later than the end.');
 const exact=query.trim().match(/^(?:rfc\s*)?(\d+)$/i),terms=query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
 return records.filter(r=>(exact?r.id===Number(exact[1]):terms.every(t=>[r.title,...r.authors,...r.keywords,...r.also,r.group,r.draft].join(' ').toLocaleLowerCase().includes(t)))&&(!status||r.status===status)&&(!stream||r.stream===stream)&&(low===null||Number(r.date.slice(0,4))>=low)&&(high===null||Number(r.date.slice(0,4))<=high)).sort((a,b)=>sort==='number'?a.id-b.id:sort==='oldest'?a.date.localeCompare(b.date)||a.id-b.id:b.date.localeCompare(a.date)||b.id-a.id);
}
export function buildGraph(records){
 const byId=new Map(records.map(r=>[r.id,r])),edges=new Map(),adj=new Map(records.map(r=>[r.id,[]]));
 for(const r of records)for(const key of RELATIONS)for(const target of r[key]){const reverse=key==='obsoletedBy'||key==='updatedBy',type=key.startsWith('obsolete')?'obsoletes':'updates',from=reverse?target:r.id,to=reverse?r.id:target,k=`${from}:${type}:${to}`;if(from===to)continue;edges.set(k,{from,to,type});}
 for(const e of edges.values()){if(!adj.has(e.from))adj.set(e.from,[]);if(!adj.has(e.to))adj.set(e.to,[]);adj.get(e.from).push(e);adj.get(e.to).push(e);}
 return {byId,edges:[...edges.values()],adj};
}
export function trail(graph,id,{depth=1,limit=80,kind='all'}={}){
 if(!graph.byId.has(id))throw Error('RFC is not present in this capture.');if(!Number.isInteger(depth)||depth<1||depth>3||!Number.isInteger(limit)||limit<1||limit>300)throw Error('Invalid trail bounds.');
 const seen=new Map([[id,0]]),queue=[id];let truncated=false;
 while(queue.length){const n=queue.shift(),d=seen.get(n);if(d>=depth)continue;for(const edge of graph.adj.get(n)||[]){if(kind!=='all'&&edge.type!==kind)continue;const other=edge.from===n?edge.to:edge.from;if(seen.has(other))continue;if(seen.size>=limit){truncated=true;continue;}seen.set(other,d+1);queue.push(other);}}
 return {ids:[...seen.keys()],edges:graph.edges.filter(e=>seen.has(e.from)&&seen.has(e.to)&&(kind==='all'||e.type===kind)),truncated,missing:[...seen.keys()].filter(n=>!graph.byId.has(n))};
}
export function neighbors(graph,id){const out={obsoletes:[],obsoletedBy:[],updates:[],updatedBy:[]};for(const e of graph.adj.get(id)||[]){const key=e.from===id?e.type:e.type==='obsoletes'?'obsoletedBy':'updatedBy';out[key].push(e.from===id?e.to:e.from);}for(const k of RELATIONS)out[k]=[...new Set(out[k])].sort((a,b)=>a-b);return out;}
export function compareCaptures(older,newer){validateCapture(older);validateCapture(newer);const old=new Map(older.records.map(r=>[r.id,r])),current=new Map(newer.records.map(r=>[r.id,r]));const added=[],removed=[],changed=[];for(const r of newer.records){if(!old.has(r.id))added.push(r.id);else {const fields=Object.keys(r).filter(k=>JSON.stringify(r[k])!==JSON.stringify(old.get(r.id)[k]));if(fields.length)changed.push({id:r.id,fields});}}for(const r of older.records)if(!current.has(r.id))removed.push(r.id);return {added,removed,changed};}
export function receipt(capture,graph,id,options){const t=trail(graph,id,options);return {schema:'coolcode.rfctrail.receipt.v1',capturedAt:capture.capturedAt,source:capture.source,focus:id,depth:options.depth,limited:t.truncated,records:t.ids.map(n=>graph.byId.get(n)).filter(Boolean),relationships:t.edges};}
export function csv(records){const q=x=>{let s=String(x??'');if(/^[=+@\t\r-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};const keys=['id','title','date','status','publicationStatus','stream','group','authors','obsoletes','obsoletedBy','updates','updatedBy','draft'];return '\uFEFF'+[keys,...records.map(r=>keys.map(k=>Array.isArray(r[k])?r[k].join(' | '):r[k]))].map(row=>row.map(q).join(',')).join('\r\n');}
export function rfcUrl(id,where='editor'){if(!Number.isInteger(id)||id<1||id>999999)throw Error('Invalid RFC number.');return where==='tracker'?`https://datatracker.ietf.org/doc/rfc${id}/`:where==='errata'?`https://www.rfc-editor.org/errata/rfc${id}`:`https://www.rfc-editor.org/info/rfc${id}`;}
export async function readBounded(stream,limit){const reader=stream.getReader(),chunks=[];let length=0;try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>limit)throw Error('Capture is larger than the supported size.');chunks.push(value);}}finally{await reader.cancel().catch(()=>{});}const out=new Uint8Array(length);let n=0;for(const c of chunks){out.set(c,n);n+=c.length;}return out;}
export async function fetchBytes(url,limit=10*1024*1024){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);try{const r=await fetch(url,{signal:controller.signal});if(!r.ok)throw Error(`Request returned HTTP ${r.status}.`);return await readBounded(r.body,limit);}catch(e){if(controller.signal.aborted)throw Error('The download timed out. Reload to try again.');throw e;}finally{clearTimeout(timer);}}
