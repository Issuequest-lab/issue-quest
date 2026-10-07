'use strict';
const $=s=>document.querySelector(s), raw='https://raw.githubusercontent.com/Issuequest-lab/issue-quest/main/';
let editorial={},days=[],payload=null,revision=0,selected=new Map();
const REGION_ORDER=['日本','アフリカ','中東','ヨーロッパ','アメリカ','アジア（その他）','韓国','中国'];
const dayJst=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(new Date());
const time=s=>new Date(s).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false})+' JST';
const jpDate=s=>{const [y,m,d]=s.split('-').map(Number);return `${y}年${m}月${d}日`;};
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
async function read(path){const results=await Promise.all([raw,'./'].map(async base=>{try{const r=await fetch(base+path+'?t='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(12000)});if(r.ok)return await r.json();}catch(e){}return null;}));const available=results.filter(Boolean),stamp=d=>d.updatedAt||d.fetchedAt||d.snapshots?.at(-1)?.fetchedAt||'';if(available.length)return available.sort((a,b)=>stamp(b).localeCompare(stamp(a)))[0];throw Error('通信できませんでした。時間をおいて再読み込みしてください。');}
function options(el,values,label=x=>x){el.replaceChildren(...values.map(v=>{const o=node('option',label(v));o.value=v;return o;}));}
function reset(){selected.clear();$('#compareArea').hidden=true;updateSelection();}
function updateSelection(){const n=selected.size;$('#selectedCount').textContent=n===0?'2件選ぶと比較できます':`比較に選択：${n} / 3件`;$('#compareBtn').disabled=n<2;$('#clearBtn').hidden=n===0;}
function link(url,text){const a=node('a',text,'source');try{if(new URL(url).protocol!=='https:')return node('span','リンク未確認');}catch{return node('span','リンク未確認');}a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function verificationLabel(a){
  if(a.verification==='paper-top')return '紙の一面トップ確認済み';
  if(a.verification==='web-top')return 'Webトップ確認済み（紙面とは別）';
  return '紙の一面掲載確認（トップ順位は未確認）';
}
function verifiedPosition(s,a){
  if(s.kind==='web')return a.verification==='web-top'&&a.positionEvidence?.type==='web-top'&&!!a.positionEvidence?.selector;
  if(s.kind!=='paper'||!a.publicationDate||!['paper-listed','paper-top'].includes(a.verification))return false;
  // Historical snapshots from these parsers were bounded to the official front-page section.
  if(s.id==='asahi-paper'||s.id==='guardian-paper')return true;
  // Mainichi's URL explicitly identifies Tokyo morning edition page 001.
  if(s.id==='mainichi-paper'){
    try{return new URL(a.url).hostname==='mainichi.jp'&&new URL(a.url).pathname.startsWith(`/articles/${a.publicationDate.replaceAll('-','')}/ddm/001/`);}catch{return false;}
  }
  return a.positionEvidence?.type==='paper-front-page'&&!!a.positionEvidence?.selector;
}
function failureLabel(s){switch(s.errorCode){case'fetch-failed':return '取得失敗';case'date-unverified':return '発行日確認失敗';case'position-unverified':return '掲載位置確認失敗';case'no-headlines':return '見出し確認失敗';case'parse-failed':return '掲載内容確認失敗';default:return '未取得';}}
function insightRow(label,text,cls=''){const p=node('p',undefined,`insight-row ${cls}`.trim());p.append(node('strong',label),document.createTextNode(text));return p;}
function compactSummary(a){
  if(a.summaryBasis==='article-reviewed'&&a.summaryJa)return {label:'何の記事？',text:a.summaryJa};
  const text=(a.summaryJa||'').normalize('NFKC').trim();
  if(!text)return null;
  // Keep complete sentences, never hide a clipped tail behind an ellipsis.
  const sentences=[];let start=0,depth=0;
  for(let i=0;i<text.length;i++){
    if('「『（('.includes(text[i]))depth++;
    if('」』）)'.includes(text[i]))depth=Math.max(0,depth-1);
    if(depth===0&&'。！？!?'.includes(text[i])){sentences.push(text.slice(start,i+1).trim());start=i+1;}
  }
  if(sentences.length){let result=sentences[0];for(const next of sentences.slice(1)){if((result+next).length>90)break;result+=next;}return {label:'要約',text:result};}
  if(!/(?:…|\.\.\.)$/.test(text))return {label:'要約',text};
  return null;
}
function headlineInsights(a){
  if(a.analysisBasis==='article-reviewed')return {issue:a.issue||null,viewpoint:a.viewpoint||null};
  const title=(a.titleJa||'').normalize('NFKC');
  // Questions are comparison prompts, not claims about the article's conclusions.
  const rules=[
    [/(?:欧州|ヨーロッパ).*(?:統一|結束|連帯)/,'欧州の結束を進めるうえで、何が課題になるか？','欧州の結束をめぐる発言・働きかけに焦点'],
    [/(?:学生|進路|教育|学校)/,'学ぶ人の選択や学習環境に、何が影響しているか？','教育や学ぶ人の動向に焦点'],
    [/(?:土石流|山津波|洪水|地震|災害)/,'被害を踏まえ、救助・生活再建で何を優先すべきか？','災害の被害と現地の状況に焦点'],
    [/\bAI\b|人工知能/,'AIの利用で、どのような影響や課題を確かめるべきか？','AIの利用に伴う懸念に焦点'],
    [/(?:地雷|国防|軍事|安全保障)/,'安全を守るため、事実確認と対応をどう進めるべきか？','安全保障上のリスクと対応に焦点'],
    [/(?:支出|予算).*(?:中止|キャンセル|削減)/,'支出の停止は誰に影響し、判断の根拠は何か？','公的支出を止める判断に焦点'],
  ];
  const match=rules.find(([pattern])=>pattern.test(title));
  return {issue:a.issue||match?.[1]||null,viewpoint:a.viewpoint||match?.[2]||null};
}
function card(s,a,choosable=true){
  const el=node('article',undefined,'card');
  el.append(node('div',`${s.name} · ${s.country} · ${s.kind==='paper'?'紙面':'Web'}`,'meta'));
  el.append(node('div',verificationLabel(a),'tag'));
  el.append(node('h3',a.titleJa||'日本語訳を取得できませんでした'));
  if(s.kind==='paper')el.append(node('p',`紙面発行日：${a.publicationDate}`,'meta'));
  const insight=node('div',undefined,'insight');
  const summary=compactSummary(a);
  const inferred=headlineInsights(a);
  if(summary)insight.append(insightRow(summary.label,summary.text,'summary'));
  if(a.backgroundJa)insight.append(insightRow('背景・用語',a.backgroundJa,'background')); 
  if(inferred.issue)insight.append(insightRow('イシュー候補',inferred.issue,'issue'));
  if(inferred.viewpoint)insight.append(insightRow(a.analysisBasis==='article-reviewed'?'記事の視点':'視点（推定）',inferred.viewpoint,'viewpoint'));
  if(insight.childElementCount)el.append(insight);
  const details=node('details',undefined,'meta-details');
  details.append(node('summary','日付・出典・補足'));
  details.append(node('p',s.kind==='paper'?`紙面発行日：${a.publicationDate||'未確認'} / ${s.edition}`:`掲載日：${a.publicationDate||'未確認'} / ${s.edition}`));
  details.append(node('p',`取得：${time(s.fetchedAt)}`));
  details.append(node('p',verificationLabel(a)));
  if(a.translation==='machine')details.append(node('p','海外見出し・説明文は自動翻訳です。'));
  if(s.kind==='paper'&&a.publicationDate&&a.publicationDate!==payload.date)details.append(node('p','取得日とは異なる発行日の紙面です。','notice'));
  if(a.comparedWith)details.append(node('p',`${a.comparedWith}の前回取得と比較：${a.change==='same'?'継続掲載':'今回の記録に追加'}`));
  details.append(node('p',a.summaryBasis==='article-reviewed'?'説明：原文を確認して日本語で整理。問いは編集上の候補です。':summary?.label==='要約'?'要約：記事の説明文・冒頭から文単位で抜粋。問い・視点：見出しから推定。':'問い・視点：見出しから推定した比較の手がかりです。記事の結論を示すものではありません。'));
  if(a.summaryJa&&a.summaryJa!==summary?.text)details.append(node('p',`取得した説明文：${a.summaryJa}`));
  details.append(node('p',a.titleOriginal),link(s.sourceUrl,'掲載位置の確認元'));
  el.append(details,link(a.url,'元記事を開く ↗'));
  if(choosable){const label=node('label',undefined,'choose'),input=document.createElement('input');input.type='checkbox';input.checked=selected.has(a.id);input.addEventListener('change',()=>{if(input.checked){if(selected.size>=3){input.checked=false;$('#selectedCount').textContent='比較は3件まで。1件解除してください。';return;}selected.set(a.id,{s,a});}else selected.delete(a.id);updateSelection();});label.append(input,document.createTextNode('比較に選ぶ'));el.append(label);}
  return el;
}
function unavailableCard(s){const el=node('article',undefined,'card error');el.append(node('div',`${s.name} · ${s.country} · ${s.kind==='paper'?'紙面':'Web'}`,'meta'),node('h3',s.name),node('p',failureLabel(s),'notice'),node('p',s.error||'この取得回では情報を確認できませんでした。','meta'));if(s.sourceUrl)el.append(link(s.sourceUrl,'確認元を開く ↗'));return el;}
// Classify publisher regions/editions, never the locations mentioned in a headline.
function regionFor(s){
  const countries={'日本':'日本','韓国':'韓国','中国':'中国','香港':'中国','米国':'アメリカ','カナダ':'アメリカ','英国':'ヨーロッパ','フランス':'ヨーロッパ','ドイツ':'ヨーロッパ','カタール':'中東','タイ':'アジア（その他）','マレーシア':'アジア（その他）'};
  return countries[s.country]||({'欧州':'ヨーロッパ','英国':'ヨーロッパ','米国':'アメリカ','中東・グローバルサウス':'中東','アジア':'アジア（その他）','通信社':'ヨーロッパ'}[s.region])||s.region||'その他';
}
function readingList(sources){
  const rows=[],seen=new Set(),counts=Object.fromEntries(REGION_ORDER.map(r=>[r,0]));
  for(const s of sources){
    if(s.status!=='ok'||(s.country==='日本'&&s.kind!=='paper'))continue;
    const region=regionFor(s);
    for(const stored of s.articles||[]){
      // Editorial translation overrides cannot promote an unverified placement.
      if(!verifiedPosition(s,stored))continue;
      const a={...stored,...(editorial[stored.url]||{})};
      if(!a.titleJa||a.translation==='unavailable'||!compactSummary(a))continue;
      let key;
      try{const url=new URL(a.url);if(url.protocol!=='https:')continue;url.hash='';for(const k of [...url.searchParams.keys()])if(k.startsWith('utm_')||k==='iref')url.searchParams.delete(k);key=url.href;}catch{continue;}
      if(seen.has(key))continue;seen.add(key);
      rows.push({s,a,region});counts[region]=(counts[region]||0)+1;
    }
  }
  return {rows,counts,japan:counts['日本'],foreign:rows.length-counts['日本']};
}
function render(){
  const area=$('#cards');area.replaceChildren();if(!payload)return;
  const kind=$('#kind').value,q=$('#search').value.trim().toLowerCase();let articleCount=0,japanCount=0;const groups=new Map(),shownSources=new Set();
  const selection=readingList(payload.sources);
  for(const {s,a,region} of selection.rows){
    if(kind!=='all'&&s.kind!==kind)continue;
      const haystack=`${a.titleJa||''} ${a.titleOriginal||''} ${a.summaryJa||''} ${a.issue||''} ${a.viewpoint||''} ${s.name} ${region}`.toLowerCase();
      if(q&&!haystack.includes(q))continue;
      if(!groups.has(region))groups.set(region,[]);
      groups.get(region).push(card(s,a));articleCount++;shownSources.add(s.id);
      if(s.country==='日本')japanCount++;
  }
  const ordered=[...groups.entries()].filter(([,els])=>els.length).sort(([a],[b])=>{const ai=REGION_ORDER.indexOf(a),bi=REGION_ORDER.indexOf(b);return (ai<0?999:ai)-(bi<0?999:bi);});
  for(const [region,els] of ordered){const section=node('section',undefined,'region'),h=node('h2',undefined,'region-title');h.append(document.createTextNode(region),node('span',`${els.length}件`,'region-count'));const grid=node('div',undefined,'source-grid');grid.append(...els);section.append(h,grid);area.append(section);}
  if(!area.children.length)area.append(node('p','この条件では、掲載位置と日本語の説明を確認できた記事がありません。'));
  $('#latestHeading').textContent=`${jpDate(payload.date)}の新聞比較`;
  $('#status').textContent=`更新 ${time(payload.fetchedAt)} · 表示 ${articleCount}件（日本 ${japanCount}・海外 ${articleCount-japanCount}） · ${shownSources.size}取得元`+(payload.date<dayJst()?(days[0]<dayJst()?' — 今日の記録はまだありません。':' — 過去の記録を表示中。'):'');
  $('#balanceNote').textContent='紙の一面掲載、またはWebトップの掲載位置を確認できた記事だけを表示しています。地域比率・件数の目標は設けず、通常記事やRSS配信で補充しません。紙の一面掲載は、一面トップであることを意味しません。';
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
(async()=>{try{try{editorial=(await read('newspaper-context.json')).articles||{};}catch{}const idx=await read('newspaper-index.json');days=idx.days.filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d));if(!days.length)throw Error('まだ取得履歴がありません。');options($('#month'),[...new Set(days.map(d=>d.slice(0,7)))]);await setMonth();}catch(e){$('#status').textContent=e.message;}})();




