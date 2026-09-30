'use strict';
// Read the news, then continue to other topics and world newspapers.
function renderDailyBriefs(box,payload){
  box.replaceChildren();
  const element=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
  const topics=Array.isArray(payload.topics)?payload.topics:[];
  const briefs=(Array.isArray(payload.briefs)?payload.briefs:[]).filter(b=>b&&b.status==='ok'&&topics.includes(b.topic)&&typeof b.summary==='string'&&b.summary.trim());
  let extra=null;
  briefs.forEach((brief,index)=>{
    const card=element('article',null,'daily-brief');
    card.append(element('h3',brief.topic));
    const summary=element('p',null,'daily-brief-summary');
    summary.append(element('strong',brief.summaryBasis==='publisher-description'?'要約':'話題の要点（関連見出しから）'),document.createTextNode(brief.summary));card.append(summary);
    if(typeof brief.issue==='string'&&brief.issue.trim()){
      const issue=element('p',null,'daily-brief-issue');issue.append(element('strong','イシュー候補'),document.createTextNode(brief.issue));card.append(issue);
    }
    const details=element('details',null,'daily-brief-details');details.append(element('summary','なぜこの問い？・関連報道'));
    if(brief.verifiedAt){const date=new Date(brief.verifiedAt);if(!Number.isNaN(date.getTime()))details.append(element('p','情報確認：'+date.toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false})+' JST'+(brief.retained?'（本日取得できた内容を表示）':'')));}
    if(brief.whyItMatters)details.append(element('p',brief.whyItMatters));
    for(const source of (Array.isArray(brief.sources)?brief.sources:[]).slice(0,2)){
      try{if(new URL(source.url).protocol!=='https:')continue;}catch{continue;}
      const p=element('p');p.append(element('span',source.title));
      const link=element('a',source.name||'出典');link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';p.append(document.createTextNode(' '),link);details.append(p);
    }
    card.append(details);
    if(index<5)box.append(card);
    else{
      if(!extra){extra=element('details',null,'daily-brief-more read-more');extra.append(element('summary',`ほかの話題も読む（${briefs.length-5}件）`));box.append(extra);}
      extra.append(card);
    }
  });
  // No invented summaries for legacy data or topics without relevant reporting.
  const unavailable=topics.filter(t=>!briefs.some(b=>b.topic===t));
  if(unavailable.length){
    const more=element('details',null,'daily-brief-more');more.append(element('summary',`話題名のみ（${unavailable.length}件）`));
    more.append(element('p',unavailable.join('・')));box.append(more);
  }
  if(briefs.length)box.append(element('p','記事の説明文・関連見出しをもとに整理。イシューは考えるための候補です。検索増加の原因や世間の総意を示すものではありません。','daily-brief-note'));
  return briefs.length;
}

