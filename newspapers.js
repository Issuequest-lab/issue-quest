'use strict';
const $=s=>document.querySelector(s), raw='https://raw.githubusercontent.com/Issuequest-lab/issue-quest/main/';
let days=[],payload=null,revision=0,selected=new Map();
const REGION_ORDER=['日本','米国','英国','欧州','アジア','中東・グローバルサウス','通信社','その他'];
const dayJst=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(new Date());
const time=s=>new Date(s).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false})+' JST';
const jpDate=s=>{const [y,m,d]=s.split('-').map(Number);return `${y}年${m}月${d}日`;};
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
async function read(path){const results=await Promise.all([raw,'./'].map(async base=>{try{const r=await fetch(base+path+'?t='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(12000)});if(r.ok)return await r.json();}catch(e){}return null;}));const available=results.filter(Boolean),stamp=d=>d.updatedAt||d.fetchedAt||d.snapshots?.at(-1)?.fetchedAt||'';if(available.length)return available.sort((a,b)=>stamp(b).localeCompare(stamp(a)))[0];throw Error('通信できませんでした。時間をおいて再読み込みしてください。');}
function options(el,values,label=x=>x){el.replaceChildren(...values.map(v=>{const o=node('option',label(v));o.value=v;return o;}));}
function reset(){selected.clear();$('#compareArea').hidden=true;updateSelection();}
function updateSelection(){const n=selected.size;$('#selectedCount').textContent=n===0?'2件選ぶと比較できます':`比較に選択：${n} / 3件`;$('#compareBtn').disabled=n<2;$('#clearBtn').hidden=n===0;}
function link(url,text){const a=node('a',text,'source');try{if(new URL(url).protocol!=='https:')return node('span','リンク未確認');}catch{return node('span','リンク未確認');}a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function verificationLabel(a){if(a.verification==='paper-top')return '一面トップ確認済み';if(a.verification==='paper-listed')return '一面掲載確認';if(a.verification==='feed-featured')return '公式フィード主要見出し';return 'Web主要見出し';}
function failureLabel(s){switch(s.errorCode){case'fetch-failed':return '取得失敗';case'date-unverified':return '発行日確認失敗';case'position-unverified':return '掲載位置確認失敗';case'no-headlines':return '見出し確認失敗';case'parse-failed':return '掲載内容確認失敗';default:return '未取得';}}
function insightRow(label,text,cls=''){const p=node('p',undefined,`insight-row ${cls}`.trim());p.append(node('strong',label),document.createTextNode(text));return p;}
function card(s,a,choosable=true){
  const el=node('article',undefined,'card');
  el.append(node('div',`${s.name} · ${s.country} · ${s.kind==='paper'?'紙面':'Web'}`,'meta'));
  el.append(node('h3',a.titleJa||'日本語訳を取得できませんでした'));
  const insight=node('div',undefined,'insight');
  insight.append(insightRow('要約',a.summaryJa||(a.summaryStatus==='translation-failed'?'説明文の日本語訳を取得できませんでした。':'この記録には記事の説明文がありません。'),'summary'));
  insight.append(insightRow('イシュー候補',a.issue||'見出しだけでは問いを特定できません。','issue'));
  insight.append(insightRow('視点（推定）',a.viewpoint||'見出しだけでは焦点を特定できません。','viewpoint'));
  insight.append(node('small',a.summaryJa?'要約：記事の説明文から抜粋。問い・視点：見出しから推定。':'問い・視点：見出しから推定。'));
  el.append(insight);
  el.append(node('span',verificationLabel(a),'tag'));
  if(a.translation==='machine')el.append(node('span','自動翻訳','tag'));
  if(a.translation==='unavailable')el.append(node('p','翻訳未取得。原文は詳細から確認できます。','notice'));
  if(a.dateBasis==='official-url')el.append(node('span','発行日：公式日付URL','tag'));



  el.append(node('p',s.kind==='paper'?`紙面発行日：${a.publicationDate||'未確認'} / ${s.edition}`:`掲載日：${a.publicationDate||'未確認'} / ${s.edition}`,'meta'));
  el.append(node('p',`取得：${time(s.fetchedAt)}`,'meta'));
  if(s.kind==='paper'&&a.publicationDate&&a.publicationDate!==payload.date)el.append(node('p','取得日とは異なる発行日の紙面です。','notice'));
  if(a.comparedWith)el.append(node('p',`${a.comparedWith}の前回取得と比較：${a.change==='same'?'継続掲載':'今回の記録に追加'}`,'meta'));
  const details=node('details',undefined,'meta-details');details.append(node('summary','原文・出典'));details.append(node('p',a.titleOriginal));details.append(link(s.sourceUrl,'掲載位置の確認元'));el.append(details,link(a.url,'元記事を開く ↗'));
  if(choosable){const label=node('label',undefined,'choose'),input=document.createElement('input');input.type='checkbox';input.checked=selected.has(a.id);input.addEventListener('change',()=>{if(input.checked){if(selected.size>=3){input.checked=false;$('#selectedCount').textContent='比較は3件まで。1件解除してください。';return;}selected.set(a.id,{s,a});}else selected.delete(a.id);updateSelection();});label.append(input,document.createTextNode('比較に選ぶ'));el.append(label);}
  return el;
}
function unavailableCard(s){const el=node('article',undefined,'card error');el.append(node('div',`${s.name} · ${s.country} · ${s.kind==='paper'?'紙面':'Web'}`,'meta'),node('h3',s.name),node('p',failureLabel(s),'notice'),node('p',s.error||'この取得回では情報を確認できませんでした。','meta'));if(s.sourceUrl)el.append(link(s.sourceUrl,'確認元を開く ↗'));return el;}
function render(){
  const area=$('#cards');area.replaceChildren();if(!payload)return;
  const kind=$('#kind').value,q=$('#search').value.trim().toLowerCase();let articleCount=0,successSources=0,failedSources=0;const groups=new Map();
  for(const s of payload.sources){
    if(kind!=='all'&&s.kind!==kind)continue;
    const region=s.region||s.country||'その他';if(!groups.has(region))groups.set(region,[]);
    if(s.status!=='ok'){groups.get(region).push(unavailableCard(s));failedSources++;continue;}
    successSources++;
    for(const a of s.articles){
      const haystack=`${a.titleJa||''} ${a.titleOriginal||''} ${a.summaryJa||''} ${a.issue||''} ${a.viewpoint||''} ${s.name} ${region}`.toLowerCase();
      if(q&&!haystack.includes(q))continue;
      groups.get(region).push(card(s,a));articleCount++;
    }
  }
  const ordered=[...groups.entries()].filter(([,els])=>els.length).sort(([a],[b])=>{const ai=REGION_ORDER.indexOf(a),bi=REGION_ORDER.indexOf(b);return (ai<0?999:ai)-(bi<0?999:bi);});
  for(const [region,els] of ordered){const section=node('section',undefined,'region'),h=node('h2',undefined,'region-title');h.append(document.createTextNode(region),node('span',`${els.length}件`,'region-count'));const grid=node('div',undefined,'source-grid');grid.append(...els);section.append(h,grid);area.append(section);}
  if(!area.children.length)area.append(node('p','条件に合う記事はありません。'));
  $('#latestHeading').textContent=`${jpDate(payload.date)}の新聞比較`;
  $('#status').textContent=`更新 ${time(payload.fetchedAt)} · 見出し ${articleCount}件 · 取得成功 ${successSources}取得元 · 未取得 ${failedSources}取得元`+(payload.date<dayJst()?(days[0]<dayJst()?' — 今日の記録はまだありません。':' — 過去の記録を表示中。'):'');
}
async function loadDay(){
  const seq=++revision;reset();payload=null;$('#cards').replaceChildren();$('#status').textContent='履歴を読み込んでいます…';
  try{
    const day=$('#day').value;let data;
    try{data=await read(`newspapers/${day.slice(0,7)}/${day}.json`);}catch(error){const latest=await read('newspaper-latest.json');if(latest.date!==day)throw error;data={snapshots:[latest]};}
    if(seq!==revision)return;
    options($('#snapshot'),data.snapshots.map((_,i)=>String(i)),i=>time(data.snapshots[i].fetchedAt));$('#snapshot').value=String(data.snapshots.length-1);
    const apply=()=>{reset();payload=data.snapshots[Number($('#snapshot').value)];render();};$('#snapshot').onchange=apply;apply();
  }catch(e){if(seq===revision)$('#status').textContent=e.message;}
}
function setMonth(){const month=$('#month').value;options($('#day'),days.filter(d=>d.startsWith(month)));return loadDay();}
$('#month').onchange=setMonth;$('#day').onchange=loadDay;$('#kind').onchange=render;$('#search').oninput=render;$('#clearBtn').onclick=()=>{reset();render();};$('#compareBtn').onclick=()=>{const area=$('#comparison');area.replaceChildren(...[...selected.values()].map(({s,a})=>card(s,a,false)));$('#compareArea').hidden=false;$('#compareArea').scrollIntoView({behavior:'smooth'});};
(async()=>{try{const idx=await read('newspaper-index.json');days=idx.days.filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d));if(!days.length)throw Error('まだ取得履歴がありません。');options($('#month'),[...new Set(days.map(d=>d.slice(0,7)))]);await setMonth();}catch(e){$('#status').textContent=e.message;}})();
