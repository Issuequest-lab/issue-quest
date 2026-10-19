'use strict';
(() => {
  const features=[['地図・探索',/地図|マップ|探索|NPC|祝福|ファストトラベル/],['カメラ・ロックオン',/カメラ|ロックオン/],['操作・メニュー',/操作|ボタン|メニュー|設定|キー|フィルタ|ソート|表示順/],['セーブ・進行',/セーブ|ロード|進行|チャプター|トロフィー/],['武器・戦闘',/武器|攻撃|戦技|ダメージ|威力|強靭|ガード|戦闘|バトル/],['魔法・アビリティ',/魔法|祈祷|魔術|アビリティ|召喚|スキル/],['オンライン',/オンライン|マルチプレイ|通信|協力|侵入|マッチング/],['画質・動作性能',/画質|描画|グラフィック|解像度|レイトレーシング|フレーム|パフォーマンス|FPS/],['衣装・外観',/衣装|外観|装束|見た目/],['追加コンテンツ',/DLC|追加コンテンツ|クエスト|ミッション|楽譜/]];
  const feature=text=>features.find(([,re])=>re.test(text))?.[0];
  const hash=s=>{let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}return (h>>>0).toString(36);};
  const spoken=s=>String(s).replace(/https?:\/\/\S+/g,'').replace(/修正対象：/g,'修正された問題は、').replace(/[《》「」■●]/g,'').replace(/\s+/g,' ').replace(/…$/,'。ここでは変更の要点までを紹介しています。');
  const day=s=>{const [y,m,d]=s.split('-').map(Number);return `${y}年${m}月${d}日`;};
  const matches=(platforms,p)=>p==='all'||(p==='unknown'?!platforms.length:platforms.includes(p));
  function build(games,p){
    const chapters=[];
    for(const g of games){
      const groups=new Map(),add=(key,item)=>{if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item);};
      if(['PS5','all'].includes(p))for(const m of g.milestones||[])add(feature(m.before+' '+m.after)||'追加コンテンツ',{date:m.date,text:`発売時は、${spoken(m.before)}。${day(m.date)}には、${spoken(m.after)}。`,baseline:true});
      const seen=new Set();
      for(const u of [...g.updates].sort((a,b)=>a.date.localeCompare(b.date)))for(const c of u.timelineChanges||u.changes||[]){
        if(!matches(c.platforms||u.platforms||[],p))continue;
        if(!c.text||/^(以下の不具合が修正されます|[■●\s]*追加コンテンツ)[。.]?$/.test(c.text))continue;
        const key=u.date+'|'+c.text;if(seen.has(key))continue;seen.add(key);
        add(feature(c.text)||c.category||'その他の変更',{date:u.date,text:spoken(c.text),version:u.version,platforms:c.platforms||u.platforms});
      }
      for(const [key,items] of groups){
        items.sort((a,b)=>a.date.localeCompare(b.date)||Number(b.baseline||0)-Number(a.baseline||0));
        const lines=[`${g.name}。${key}の変化を、古い順に振り返ります。`];
        if(!items.some(i=>i.baseline))lines.push(`発売時の${key}の全仕様は確認できていないため、確認できた発売後の変更から説明します。`);
        let previous='';
        for(const item of items){if(item.baseline){lines.push(item.text);continue;}
          const stamp=item.date+'|'+item.version+'|'+(p==='all'?(item.platforms||[]).join('・'):'');
          if(stamp!==previous){lines.push(`${day(item.date)}${item.version&&item.version!=='未確認'?'、バージョン'+item.version:''}${p==='all'?'、対象は'+((item.platforms||[]).join('、')||'機種未確認'):''}の変更です。`);previous=stamp;}
          lines.push(item.text.replace(/[。.]?$/,'。'));
        }
        lines.push(`${g.name}の${key}について、確認できた変更はここまでです。`);
        chapters.push({id:g.id+':'+key,title:g.name+' ／ '+key,lines});
      }
    }
    return chapters;
  }
  if(typeof module!=='undefined')module.exports={build,hash,spoken};
  if(typeof document==='undefined')return;
  const $=id=>document.getElementById(id),synth=window.speechSynthesis;
  let chapters=[],queue=[],position=0,playing=false,token=0,utterance=null,storageKey='',active=null;
  const save=()=>{if(!storageKey)return;try{localStorage.setItem(storageKey,JSON.stringify({id:queue[position]?.id||null,done:position>=queue.length}));}catch{}};
  function clear(){active?.classList.remove('audio-reading');active=null;}
  function cancel(){token++;synth?.cancel();utterance=null;clear();}
  function chapterAt(){return queue[position]?.chapter??0;}
  function show(){const c=chapterAt();$('readChapter').value=String(c);const box=$('audioText');if(box.dataset.chapter!==String(c)){box.replaceChildren();for(const [i,line] of (chapters[c]?.lines||[]).entries()){const p=document.createElement('p');p.textContent=line;p.id='speech-line-'+c+'-'+i;box.append(p);}box.dataset.chapter=String(c);} }
  function buttons(){const ready=queue.length>0&&!!synth&&!!window.SpeechSynthesisUtterance;$('readPlay').disabled=!ready;$('readPlay').textContent=playing?'一時停止':position>0&&position<queue.length?'▶ 続きから聞く':'▶ 変化の歴史を聞く';$('readStop').disabled=!playing;$('readNext').disabled=!ready||chapterAt()>=chapters.length-1;$('readPrev').disabled=!ready||chapterAt()===0;$('readRestart').disabled=!ready;$('readChapter').disabled=!ready;}
  function estimate(){const rate=Number($('readRate').value)||1;const total=queue.reduce((n,x)=>n+x.text.length,0);const rest=queue.slice(position).reduce((n,x)=>n+x.text.length,0);$('readEstimate').textContent=`全${chapters.length}章・約${Math.max(1,Math.ceil(total/(300*rate)))}分 ／ 残り約${Math.ceil(rest/(300*rate))}分（文字数からの目安）`;}
  function pause(message='一時停止しました。続きから再開できます。'){playing=false;cancel();save();$('readStatus').textContent=message;buttons();estimate();}
  function speak(){
    if(position>=queue.length){playing=false;cancel();save();$('readStatus').textContent='すべての章を読み終えました。';buttons();estimate();return;}
    show();const item=queue[position],stamp=++token;clear();
    $('readStatus').textContent=`${item.chapter+1} / ${chapters.length}章：${chapters[item.chapter].title}`;
    const u=new SpeechSynthesisUtterance(item.text);utterance=u;u.lang='ja-JP';u.rate=Number($('readRate').value)||1;const voice=synth.getVoices().find(v=>/^ja/i.test(v.lang));if(voice)u.voice=voice;
    u.onstart=()=>{if(stamp!==token)return;active=$('speech-line-'+item.chapter+'-'+item.line);active?.classList.add('audio-reading');if($('audioTranscript').open)active?.scrollIntoView({block:'nearest',behavior:'smooth'});};
    u.onend=()=>{if(stamp!==token||!playing)return;position++;save();estimate();speak();};
    u.onerror=e=>{if(stamp!==token)return;pause('音声が停止しました。再開ボタンでこの文から再試行できます。');};
    try{synth.speak(u);}catch{pause('音声を再生できません。この文の位置を保存しました。');}buttons();
  }
  function go(c){cancel();position=queue.findIndex(q=>q.chapter===c);if(position<0)position=0;save();show();estimate();if(playing)speak();else{$('readStatus').textContent='選択中：'+chapters[c].title;buttons();}}
  $('readPlay').onclick=()=>{if(playing){pause();return;}if(position>=queue.length)position=0;playing=true;cancel();speak();};
  $('readStop').onclick=()=>pause();$('readNext').onclick=()=>go(Math.min(chapters.length-1,chapterAt()+1));$('readPrev').onclick=()=>go(Math.max(0,chapterAt()-1));$('readRestart').onclick=()=>go(0);$('readChapter').onchange=()=>go(Number($('readChapter').value));
  $('readRate').onchange=()=>{try{localStorage.setItem('game-read-rate',$('readRate').value);}catch{}estimate();if(playing){cancel();speak();}};
  try{const rate=localStorage.getItem('game-read-rate');if([...$('readRate').options].some(o=>o.value===rate))$('readRate').value=rate;}catch{}
  window.addEventListener('game-data',e=>{
    if(storageKey)save();playing=false;cancel();chapters=build(e.detail.games,e.detail.platform);queue=[];
    chapters.forEach((c,chapter)=>c.lines.forEach((line,i)=>{const parts=(line.match(/[^。！？]+[。！？]?/gu)||[]).flatMap(s=>s.match(/[\s\S]{1,90}/gu)||[]);parts.forEach((text,j)=>queue.push({text,chapter,line:i,id:c.id+':'+hash(line)+':'+j}));}));
    storageKey='game-read-v2:'+e.detail.platform+':'+hash(e.detail.games.map(g=>g.id).join('|'));position=0;
    try{const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(saved&&!saved.done){const i=queue.findIndex(q=>q.id===saved.id);if(i>=0)position=i;}}catch{}
    $('readChapter').replaceChildren(...chapters.map((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=(i+1)+'. '+c.title;return o;}));
    $('audioText').dataset.chapter='';show();estimate();buttons();
    $('readStatus').textContent=!synth?'このブラウザは音声再生に対応していません。':!queue.length?'この機種・作品の読み上げ可能な履歴がありません。':position>0?'保存した位置から再開できます。':'機能別に、発売後の変更を古い順で聴けます。出典やURLは読み上げません。';
  });
  window.addEventListener('pagehide',()=>pause());
})();
