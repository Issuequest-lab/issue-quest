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
  const $=id=>document.getElementById(id),audio=$('gameAudio');
  let manifest=null,playlist=[],chapters=[],trackIndex=0,chapterIndex=-1,revision=0,storageKey='',active=null,pendingTime=null,signature='',lastSave=0;
  const status=text=>{$('readStatus').textContent=text;};
  const track=()=>playlist[trackIndex];
  function clear(){active?.classList.remove('audio-reading');active=null;}
  function save(){if(!storageKey||!track())return;try{localStorage.setItem(storageKey,JSON.stringify({key:track().key,gameId:track().gameId,time:pendingTime??audio.currentTime,chapter:chapters[chapterIndex]?.id}));}catch{}}
  function buttons(){const ready=playlist.length>0;$('readPlay').disabled=!ready;$('readPlay').textContent=audio.paused?'▶ 続きから聞く':'一時停止';$('readStop').disabled=!ready||audio.paused;$('readNext').disabled=!ready||chapterIndex>=chapters.length-1;$('readPrev').disabled=!ready||chapterIndex<=0;$('readRestart').disabled=!ready;$('readChapter').disabled=!ready;audio.hidden=!ready;}
  function estimate(){const rate=Number($('readRate').value)||1,total=playlist.reduce((n,t)=>n+t.duration,0),past=playlist.slice(0,trackIndex).reduce((n,t)=>n+t.duration,0)+(pendingTime??audio.currentTime);$('readEstimate').textContent=playlist.length?`全${chapters.length}章・約${Math.ceil(total/60/rate)}分 ／ 残り約${Math.max(0,Math.ceil((total-past)/60/rate))}分（音声の長さ）`:'';}
  function update(){
    if(!track())return;
    const time=pendingTime??audio.currentTime;
    let index=chapters.findIndex(c=>c.trackIndex===trackIndex&&time>=c.start&&time<c.end);
    if(index<0)index=chapters.findIndex(c=>c.trackIndex===trackIndex);
    const c=chapters[index];if(!c)return;
    if(chapterIndex!==index){chapterIndex=index;$('readChapter').value=String(index);$('audioText').replaceChildren(...c.lines.map((line,i)=>{const p=document.createElement('p');p.textContent=line.text;p.id='speech-line-'+i;return p;}));clear();
      if('mediaSession' in navigator && window.MediaMetadata)navigator.mediaSession.metadata=new MediaMetadata({title:c.title,artist:'ISSUE QUEST',album:'発売後の変化'});
    }
    const line=c.lines.findIndex(l=>time>=l.start&&time<l.end),el=$('speech-line-'+line);
    if(active!==el){clear();if(!audio.paused&&el){active=el;active.classList.add('audio-reading');if($('audioTranscript').open&&!document.hidden)active.scrollIntoView({block:'nearest',behavior:'smooth'});}}
    if(audio.paused)clear();
    if('mediaSession' in navigator){navigator.mediaSession.playbackState=audio.paused?'paused':'playing';if(Number.isFinite(audio.duration)&&audio.duration>0)try{navigator.mediaSession.setPositionState({duration:audio.duration,playbackRate:audio.playbackRate,position:Math.min(audio.currentTime,audio.duration)});}catch{}}
    buttons();estimate();
  }
  async function play(){if(!track())return;try{await audio.play();status('バックグラウンド再生中：'+chapters[chapterIndex]?.title);update();}catch{status('音声を開始できませんでした。再生ボタンをもう一度押してください。');buttons();}}
  function pause(){audio.pause();save();clear();status('一時停止しました。続きから再開できます。');update();}
  function loadTrack(index,time=0){trackIndex=index;chapterIndex=-1;pendingTime=time;audio.src=track().src;audio.playbackRate=Number($('readRate').value)||1;audio.load();$('audioFile').href=track().src;$('audioFile').hidden=false;update();}
  function go(index){if(!chapters[index])return;const running=!audio.paused,c=chapters[index];if(c.trackIndex!==trackIndex)loadTrack(c.trackIndex,c.start);else {if(pendingTime!==null)pendingTime=c.start;else audio.currentTime=c.start;update();}save();status('選択中：'+c.title);if(running)play();}
  $('readPlay').onclick=()=>audio.paused?play():pause();$('readStop').onclick=pause;
  $('readNext').onclick=()=>go(Math.min(chapters.length-1,chapterIndex+1));$('readPrev').onclick=()=>go(Math.max(0,chapterIndex-1));$('readRestart').onclick=()=>go(0);$('readChapter').onchange=()=>go(Number($('readChapter').value));
  $('readRate').onchange=()=>{audio.playbackRate=Number($('readRate').value);try{localStorage.setItem('game-read-rate',$('readRate').value);}catch{}update();};
  try{const rate=localStorage.getItem('game-read-rate');if([...$('readRate').options].some(o=>o.value===rate))$('readRate').value=rate;}catch{}
  audio.addEventListener('loadedmetadata',()=>{if(pendingTime!==null){audio.currentTime=Math.min(pendingTime,Math.max(0,audio.duration-0.1));pendingTime=null;}update();});
  audio.addEventListener('timeupdate',()=>{update();if(Date.now()-lastSave>2000){save();lastSave=Date.now();}});
  audio.addEventListener('play',()=>{status('バックグラウンド再生中');update();});audio.addEventListener('pause',()=>{save();clear();update();});audio.addEventListener('seeked',()=>{save();update();});
  audio.addEventListener('ended',()=>{if(trackIndex+1<playlist.length){loadTrack(trackIndex+1);play();}else{save();status('すべての章を読み終えました。');update();}});
  audio.addEventListener('error',()=>{if(track()){status('音声ファイルを読み込めませんでした。通信状態を確認して再読み込みしてください。');clear();buttons();}});
  if('mediaSession' in navigator)for(const [action,handler] of Object.entries({play,pause,stop:pause,previoustrack:()=>$('readPrev').click(),nexttrack:()=>$('readNext').click(),seekbackward:e=>{audio.currentTime=Math.max(0,audio.currentTime-(e.seekOffset||15));},seekforward:e=>{audio.currentTime=Math.min(audio.duration,audio.currentTime+(e.seekOffset||15));},seekto:e=>{audio.currentTime=e.seekTime;}}))try{navigator.mediaSession.setActionHandler(action,handler);}catch{}
  // Hiding or locking the screen must never pause a native media stream.
  document.addEventListener('visibilitychange',save);window.addEventListener('pagehide',save);
  window.addEventListener('game-data',async e=>{
    const serial=++revision,requested=e.detail.games.map(g=>({gameId:g.id,signature:hash(JSON.stringify(build([g],e.detail.platform)))}));
    try{
      if(!manifest){const r=await fetch('game-audio-manifest.json',{cache:'no-cache'});if(!r.ok)throw Error('manifest');manifest=await r.json();}
      if(serial!==revision)return;
      const next=requested.map(g=>manifest.tracks.find(t=>t.platform===e.detail.platform&&t.gameId===g.gameId&&t.signature===g.signature)).filter(Boolean);
      const nextSignature=next.map(t=>t.key).join('|');if(signature===nextSignature&&playlist.length)return;
      save();audio.pause();playlist=next;signature=nextSignature;chapters=playlist.flatMap((t,ti)=>t.chapters.map(c=>({...c,trackIndex:ti})));chapterIndex=-1;
      $('readChapter').replaceChildren(...chapters.map((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=(i+1)+'. '+c.title;return o;}));
      storageKey='game-file-read-v1:'+e.detail.platform+':'+hash(playlist.map(t=>t.gameId).join('|'));
      if(!playlist.length){audio.removeAttribute('src');audio.load();$('audioText').replaceChildren();$('audioFile').hidden=true;buttons();estimate();status('この表示条件の音声はまだありません。最新日の記録と対象機種を選んでください。');return;}
      let ti=0,time=0;try{const old=JSON.parse(localStorage.getItem(storageKey)||'null');if(old){const i=playlist.findIndex(t=>t.gameId===old.gameId);if(i>=0){ti=i;time=playlist[i].key===old.key?old.time:playlist[i].chapters.find(c=>c.id===old.chapter)?.start||0;}}}catch{}
      loadTrack(ti,time);status(time>0?'保存した位置から再開できます。':'音声ファイルで再生します。開始後は別アプリに切り替えても聴けます。');
    }catch{if(serial!==revision)return;status('音声を準備中、または読み込めませんでした。時間をおいて再読み込みしてください。');}
  });
})();
