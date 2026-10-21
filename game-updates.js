'use strict';
(() => {
const $=s=>document.querySelector(s),categories=['安定性','性能・画質','操作性','バランス','コンテンツ','その他の修正'];
let payload=null,days=[],revision=0,selected=new Set();
const n=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
const dateTime=s=>new Date(s).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false})+' JST';
const today=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(new Date());
function link(url,text='公式の変更内容 ↗'){const a=n('a',text,'source');try{if(new URL(url).protocol!=='https:')return n('span','出典URL未確認');}catch{return n('span','出典URL未確認');}a.href=url;a.target='_blank';a.rel='noopener noreferrer';const d=n('details',undefined,'source-details');d.append(n('summary','参考情報'),a);return d;}
async function read(path){const r=await fetch(path+'?t='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('記録を読み込めませんでした。時間をおいて再読み込みしてください。');return r.json();}
function options(el,values,label=x=>x){el.replaceChildren(...values.map(v=>{const o=n('option',label(v));o.value=v;return o;}));}
function matchPlatform(u,p){return p==='all'||(p==='unknown'?!u.platforms.length:u.platforms.includes(p));}
function matching(g){const p=$('#platform').value;return g.updates.filter(u=>matchPlatform(u,p)).map(u=>({...u,changes:u.changes.filter(c=>matchPlatform({platforms:c.platforms||u.platforms},p))})).filter(u=>u.changes.length);}
function selection(){const count=selected.size;$('#selectedCount').textContent=count?`比較に選択：${count} / 3作品`:'2作品を選ぶと比較できます';$('#compareBtn').disabled=count<2;}
function reset(){selected.clear();$('#compareArea').hidden=true;selection();}
function excerpt(c){return `${c.category}：${c.text}`;}
function note(u,details=false){const box=n('div',undefined,details?'history':'box');box.append(n(details?'strong':'h4',`${u.date} · Ver.${u.version}`));box.append(n('p',`対象：${u.platforms.join('・')||'未確認'} ／ 公式発表`,'meta'));
for(const c of u.changes)box.append(n('p',excerpt(c),details?'':'insight-row'));
box.append(n('p','公式発表をもとに整理。','hint'),link(u.url));return box;}
function gameCard(g){const card=n('article',undefined,'card');card.append(n('div',g.company,'meta'),n('h3',g.name),n('p',`PS5発売日：${g.releaseDate}`,'meta'));
card.id='game-'+g.id;
if(g.deepDive){const d=g.deepDive,story=n('section',undefined,'deep-dive');story.append(n('p',`深掘り記事 · ${d.publishedAt}公開 · ${d.asOf}時点`,'meta'),n('h4',d.title),n('p',d.summary,'insight-row'),n('p','中心となるイシュー：'+d.issue,'insight-row'));
const listen=n('button','この作品の音声を選ぶ','btn');listen.type='button';listen.onclick=()=>{$('#search').value=g.name;$('#platform').value='PS5';reset();render();$('#readPlay').scrollIntoView({block:'center',behavior:'smooth'});$('#readStatus').textContent='この作品を選択しました。再生ボタンで開始できます。';};story.append(listen);
for(const c of d.chapters){const section=n('details');section.open=true;section.append(n('summary',c.title));for(const text of c.paragraphs)section.append(n('p',text));story.append(section);}
story.append(n('p','変更の意味や評価は編集上の考察です。公式の修正発表と、実機での解消確認は区別しています。','hint'));const sources=n('details');sources.append(n('summary','参考情報（読み上げ対象外）'));for(const s of d.sources)sources.append(link(s.url,s.title));story.append(sources);card.append(story);}
if(g.sourceStatus!=='ok')card.append(n('p',g.sourceStatus==='failed'?'今回の確認に失敗。前回までの記録を表示しています。':'一部の公式履歴を取得できていません。','warn'));
card.append(n('p',`公式情報の確認：${dateTime(g.checkedAt)}`,'meta'));
const updates=matching(g),latest=updates[0];card.append(n('h4',`${$('#platform').selectedOptions[0].textContent}の最新確認記録`));
if(latest){card.append(note(latest));if(latest.lastVerifiedAt!==g.checkedAt)card.append(n('p',`この記録の最終確認：${dateTime(latest.lastVerifiedAt)}`,'warn'));}
else card.append(n('p','この機種を対象と明記した更新は、この取得範囲では未確認です。','insight-row'));
card.append(n('h4','発売時 → 発売後の代表的な変化'));
if(g.milestones.length&&['PS5','all'].includes($('#platform').value))for(const m of g.milestones){const box=n('div',undefined,'box');box.append(n('p',`発売時：${m.before}`,'insight-row'),n('p',`発売後：${m.after}`,'insight-row'),n('p',`${m.date} · Ver.${m.version} ／ ${m.basis}`,'hint'),link(m.url));card.append(box);}
else card.append(n('p','発売時との具体的な差は未確認。以下の更新履歴と区別しています。','insight-row'));
const cumulative=n('details');cumulative.append(n('summary',`発売後の変更履歴（確認範囲：${updates.length}記録）`),n('p',g.baseline,'hint'));
for(const category of categories){const history=updates.flatMap(u=>u.changes.filter(c=>c.category===category).map(c=>({u,c})));if(!history.length)continue;cumulative.append(n('h4',category));for(const {u,c} of history.slice(0,5)){const p=n('p',`${u.date} · ${c.text}`);p.append(document.createTextNode(' '),link(u.url,'出典'));cumulative.append(p);}if(history.length>5)cumulative.append(n('p',`ほか${history.length-5}件は全更新履歴へ。`,'hint'));}
card.append(cumulative);
const all=n('details');all.append(n('summary',`全更新履歴・機種差（${g.updates.length}記録）`),n('p','PC限定や機種未確認の変更を、PS5にも適用されたとは扱いません。','hint'));for(const u of g.updates)all.append(note(u,true));card.append(all);
const other=g.updates.find(u=>!matchPlatform(u,'PS5'));if(other&&$('#platform').value==='PS5')card.append(n('p',`別枠の最新：${other.date} · ${other.platforms.join('・')||'機種未確認'} · Ver.${other.version}（全更新履歴で確認）`,'meta'));
const label=n('label',undefined,'choose'),input=n('input');input.type='checkbox';input.checked=selected.has(g.id);input.addEventListener('change',()=>{if(input.checked){if(selected.size===3){input.checked=false;$('#selectedCount').textContent='比較は3作品までです。';return;}selected.add(g.id);}else selected.delete(g.id);selection();$('#compareArea').hidden=true;});label.append(input,document.createTextNode('比較に選ぶ'));card.append(label);return card;}
function render(){const area=$('#cards');area.replaceChildren();if(!payload)return;const q=$('#search').value.trim().toLowerCase();const games=payload.games.filter(g=>!q||JSON.stringify(g).toLowerCase().includes(q));area.append(...games.map(gameCard));window.dispatchEvent(new CustomEvent('game-data',{detail:{games,platform:$('#platform').value}}));if(!games.length)area.append(n('p','この条件に合う作品がありません。'));$('#status').textContent=`確認日 ${payload.date} · ${games.length}作品 · 更新 ${dateTime(payload.checkedAt)}`+(payload.date<today()?' — 過去の記録です。':'');}
function compare(){const games=payload.games.filter(g=>selected.has(g.id));const table=n('table'),head=n('tr');head.append(n('th','比較項目'));for(const g of games)head.append(n('th',g.name));const thead=n('thead');thead.append(head);table.append(thead);const body=n('tbody');for(const category of ['発売時との違い',...categories]){const tr=n('tr');tr.append(n('th',category));for(const g of games){const td=n('td');if(category==='発売時との違い'){if(g.milestones.length&&['PS5','all'].includes($('#platform').value)){for(const m of g.milestones){const p=n('p',`${m.before} → ${m.after}（${m.date}）`);p.append(link(m.url,'出典'));td.append(p);}}else td.append(n('p','比較できる根拠が未確認'));}else{const u=matching(g).find(u=>u.changes.some(c=>c.category===category));if(u){td.append(n('p',`${u.date} · ${u.platforms.join('・')||'機種未確認'}`,'meta'),n('p',u.changes.find(c=>c.category===category).text),link(u.url,'出典'));}else td.append(n('p','取得範囲に記録なし（変更なしとは限りません）'));}tr.append(td);}body.append(tr);}table.append(body);$('#comparison').replaceChildren(table);$('#compareArea').hidden=false;$('#compareArea').scrollIntoView({behavior:'smooth'});}
async function loadDay(){const token=++revision;reset();payload=null;render();$('#status').textContent='履歴を読み込んでいます…';try{const d=$('#day').value;let archive;try{archive=await read(`game-updates/${d.slice(0,7)}/${d}.json`);}catch(e){const latest=await read('game-updates-latest.json');if(latest.date!==d)throw e;archive={snapshots:[latest]};}if(token!==revision)return;options($('#snapshot'),archive.snapshots.map((_,i)=>String(i)),i=>dateTime(archive.snapshots[i].checkedAt));$('#snapshot').value=String(archive.snapshots.length-1);const apply=()=>{reset();payload=archive.snapshots[Number($('#snapshot').value)];render();};$('#snapshot').onchange=apply;apply();}catch(e){if(token===revision)$('#status').textContent=e.message;}}
function month(){options($('#day'),days.filter(d=>d.startsWith($('#month').value)));return loadDay();}
$('#platform').onchange=()=>{reset();render();};$('#search').oninput=()=>{reset();render();};$('#month').onchange=month;$('#day').onchange=loadDay;$('#compareBtn').onclick=compare;$('#clearBtn').onclick=()=>{reset();render();};
(async()=>{try{const index=await read('game-updates-index.json');days=index.days.filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)).sort().reverse();if(!days.length)throw Error('まだ更新の記録がありません。');options($('#month'),[...new Set(days.map(d=>d.slice(0,7)))]);await month();}catch(e){$('#status').textContent=e.message;}})();
})();

