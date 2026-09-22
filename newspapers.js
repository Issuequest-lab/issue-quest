'use strict';
const $=s=>document.querySelector(s), raw='https://raw.githubusercontent.com/Issuequest-lab/issue-quest/main/';
let days=[],payload=null,revision=0,selected=new Map();
const dayJst=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(new Date());
const time=s=>new Date(s).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false})+' JST';
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
async function read(path){for(const base of [raw,'./']){try{const r=await fetch(base+path,{cache:'no-store',signal:AbortSignal.timeout(12000)});if(r.ok)return await r.json();}catch(e){}}throw Error('通信できませんでした。時間をおいて再読み込みしてください。');}
function options(el,values,label=x=>x){el.replaceChildren(...values.map(v=>{const o=node('option',label(v));o.value=v;return o;}));}
function reset(){selected.clear();$('#compareArea').hidden=true;updateSelection();}
function updateSelection(){$('#selectedCount').textContent=`比較に選択：${selected.size} / 3件`;$('#compareBtn').disabled=selected.size<2;}
function link(url,text){const a=node('a',text,'source');try{if(new URL(url).protocol!=='https:')return node('span','リンク未確認');}catch{return node('span','リンク未確認');}a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function card(s,a,choosable=true){const el=node('article',undefined,'card');el.append(node('div',`${s.name} · ${s.country} · ${s.kind==='paper'?'紙面':'Web'}`,'meta'));
el.append(node('h3',a.titleJa||'日本語訳を取得できませんでした'));
el.append(node('span',a.verification==='paper-top'?'一面トップ確認済み':a.verification==='paper-listed'?'一面掲載のみ確認':'Web掲載・トップ位置未確認','tag'));
if(a.translation==='machine')el.append(node('span','自動翻訳','tag'));if(a.translation==='unavailable')el.append(node('p','翻訳未取得。原文は下の詳細から確認できます。','notice'));
el.append(node('p',s.kind==='paper'?`紙面発行日：${a.publicationDate} / ${s.edition}`:`掲載日：${a.publicationDate||'未確認'} / ${s.edition}`,'meta'));
el.append(node('p',`取得：${time(s.fetchedAt)}`,'meta'));
if(s.kind==='paper'&&a.publicationDate!==payload.date)el.append(node('p','取得日とは異なる発行日の紙面です。','notice'));
if(a.comparedWith)el.append(node('p',`${a.comparedWith}の前回取得と比較：${a.change==='same'?'継続掲載':'今回の記録に追加'}`,'meta'));
const details=node('details');details.append(node('summary','原文・出典'));details.append(node('p',a.titleOriginal));details.append(link(s.sourceUrl,'掲載位置の確認元'));el.append(details,link(a.url,'元記事を開く ↗'));
if(choosable){const label=node('label',undefined,'choose'),input=document.createElement('input');input.type='checkbox';input.checked=selected.has(a.id);input.addEventListener('change',()=>{if(input.checked){if(selected.size>=3){input.checked=false;$('#selectedCount').textContent='比較は3件まで。選択を解除して入れ替えてください。';return;}selected.set(a.id,{s,a});}else selected.delete(a.id);updateSelection();});label.append(input,document.createTextNode('比較に選ぶ'));el.append(label);}return el;}
function render(){const area=$('#cards');area.replaceChildren();if(!payload)return;const kind=$('#kind').value,q=$('#search').value.trim().toLowerCase();let count=0;
for(const s of payload.sources){if(kind!=='all'&&s.kind!==kind)continue;if(s.status!=='ok'){const err=node('article',undefined,'card error');err.append(node('h3',s.name),node('p',`${s.kind==='paper'?'紙面':'Web'}：未取得`,'notice'),node('p',s.error,'meta'));area.append(err);continue;}
for(const a of s.articles){if(q&&!`${a.titleJa||''} ${a.titleOriginal} ${s.name}`.toLowerCase().includes(q))continue;area.append(card(s,a));count++;}}
if(!area.children.length)area.append(node('p','条件に合う記事はありません。'));
$('#status').textContent=`取得日 ${payload.date} · 更新 ${time(payload.fetchedAt)} · 表示 ${count}件`+(payload.date<dayJst()?(days[0]<dayJst()?' — 今日の記録はまだありません。':' — 過去の記録を表示中。'):'');}
async function loadDay(){const seq=++revision;reset();payload=null;$('#cards').replaceChildren();$('#status').textContent='履歴を読み込んでいます…';try{const day=$('#day').value;let data;try{data=await read(`newspapers/${day.slice(0,7)}/${day}.json`);}catch(error){const latest=await read('newspaper-latest.json');if(latest.date!==day)throw error;data={snapshots:[latest]};}if(seq!==revision)return;options($('#snapshot'),data.snapshots.map((_,i)=>String(i)),i=>time(data.snapshots[i].fetchedAt));$('#snapshot').value=String(data.snapshots.length-1);const apply=()=>{reset();payload=data.snapshots[Number($('#snapshot').value)];render();};$('#snapshot').onchange=apply;apply();}catch(e){if(seq===revision)$('#status').textContent=e.message;}}
function setMonth(){const month=$('#month').value;options($('#day'),days.filter(d=>d.startsWith(month)));return loadDay();}
$('#month').onchange=setMonth;$('#day').onchange=loadDay;$('#kind').onchange=render;$('#search').oninput=render;$('#clearBtn').onclick=()=>{reset();render();};$('#compareBtn').onclick=()=>{const area=$('#comparison');area.replaceChildren(...[...selected.values()].map(({s,a})=>card(s,a,false)));$('#compareArea').hidden=false;$('#compareArea').scrollIntoView({behavior:'smooth'});};
(async()=>{try{const idx=await read('newspaper-index.json');days=idx.days.filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d));if(!days.length)throw Error('まだ取得履歴がありません。');options($('#month'),[...new Set(days.map(d=>d.slice(0,7)))]);await setMonth();}catch(e){$('#status').textContent=e.message;}})();
