'use strict';
(() => {
  const el=id=>document.getElementById(id);
  const play=el('readPlay'),stop=el('readStop'),next=el('readNext'),rate=el('readRate'),status=el('readStatus'),cards=el('cards');
  const synth=window.speechSynthesis;
  if(!synth||!window.SpeechSynthesisUtterance){status.textContent='このブラウザは音声再生に対応していません。Chromeなど対応ブラウザで開いてください。';rate.disabled=true;return;}
  let queue=[],index=0,state='idle',generation=0,current=null,activeTarget=null;
  try{const saved=localStorage.getItem('newspaper-read-rate');if([...rate.options].some(o=>o.value===saved))rate.value=saved;}catch{}
  // Short utterances avoid long-text engine stalls. Cancel/restart supports Android pause reliably.
  function chunks(text){return (text.match(/[^。！？!?]+[。！？!?]?/gu)||[]).flatMap(s=>s.match(/[\s\S]{1,100}/gu)||[]).map(s=>s.trim()).filter(Boolean);}
  function collect(){return [...cards.querySelectorAll('article.card')].flatMap((card,article)=>{
    const title=card.querySelector('h3')?.textContent||'';
    const fields=[card.querySelector('.meta'),card.querySelector('h3'),...card.querySelectorAll('.insight-row')];
    return fields.filter(Boolean).flatMap(target=>chunks(target.textContent).map(text=>({text,card,title,article,target})));
  });}
  function clearHighlight(){if(activeTarget){activeTarget.classList.remove('audio-reading');activeTarget=null;}cards.querySelectorAll('.reading').forEach(c=>c.classList.remove('reading'));}
  function buttons(){play.textContent=state==='playing'?'一時停止':state==='paused'?'▶ 再開':'▶ 記事を聞く';play.disabled=!cards.querySelector('article.card');stop.disabled=state==='idle';next.disabled=state==='idle'||!queue.slice(index+1).some(q=>q.article!==queue[index]?.article);}
  function cancel(){generation++;synth.cancel();current=null;}
  function finish(message){state='idle';cancel();queue=[];index=0;clearHighlight();status.textContent=message;buttons();}
  function speak(){
    if(index>=queue.length){finish('表示中の記事をすべて読み終えました。');return;}
    const item=queue[index],token=++generation;
    clearHighlight();
    status.textContent=`読み上げ中 ${item.article+1} / ${queue.at(-1).article+1}件：${item.title}`;
    const u=new SpeechSynthesisUtterance(item.text);current=u;u.lang='ja-JP';u.rate=Number(rate.value);
    const voice=synth.getVoices().find(v=>/^ja(?:-|_)?/i.test(v.lang));if(voice)u.voice=voice;
    u.onstart=()=>{if(token!==generation||state!=='playing')return;activeTarget=item.target;activeTarget.classList.add('audio-reading');item.card.classList.add('reading');};
    u.onend=()=>{if(token!==generation||state!=='playing')return;index++;speak();};
    u.onerror=e=>{if(token!==generation)return;finish(e.error==='language-unavailable'||e.error==='voice-unavailable'?'日本語の音声が利用できません。端末の読み上げ設定を確認してください。':'音声を再生できませんでした。「記事を聞く」で再試行してください。');};
    buttons();try{synth.speak(u);}catch{finish('音声を再生できませんでした。ブラウザを変えてお試しください。');}
  }
  play.addEventListener('click',()=>{
    if(state==='playing'){state='paused';cancel();clearHighlight();status.textContent='一時停止中。再開すると現在の文の先頭から読みます。';buttons();return;}
    if(state==='idle'){queue=collect();index=0;}
    if(!queue.length){finish('読み上げる記事がありません。');return;}
    state='playing';cancel();speak();
  });
  stop.addEventListener('click',()=>finish('停止しました。再生すると最初の記事から読みます。'));
  next.addEventListener('click',()=>{const i=queue.findIndex((q,i)=>i>index&&q.article!==queue[index].article);if(i<0)return;cancel();index=i;if(state==='playing')speak();else{clearHighlight();status.textContent='次の記事で一時停止中：'+queue[index].title;buttons();}});
  rate.addEventListener('change',()=>{try{localStorage.setItem('newspaper-read-rate',rate.value);}catch{}if(state==='playing'){cancel();speak();}});
  new MutationObserver(()=>finish('表示中の記事を日本語で順に読み上げます。')).observe(cards,{childList:true});
  window.addEventListener('pagehide',()=>finish('停止しました。'));
  buttons();
})();

