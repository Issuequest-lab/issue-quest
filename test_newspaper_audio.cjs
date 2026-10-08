const fs=require('fs'),vm=require('vm'),assert=require('assert');
const code=fs.readFileSync(__dirname+'/newspaper-audio.js','utf8');
function setup(supported=true){
 const elements={};for(const id of ['readPlay','readStop','readNext','readRate','readStatus','cards'])elements[id]={value:'1',options:[{value:'1'},{value:'1.5'}],addEventListener(t,f){this[t]=f;}};
 const articles=['最初の記事','次の記事'].map(title=>({classList:{add(){},remove(){}},querySelector:s=>({textContent:s==='h3'?title:'新聞社'}),querySelectorAll:()=>[{textContent:'要約。日本語の説明です。'}]}));
 elements.cards.querySelector=()=>articles[0];elements.cards.querySelectorAll=s=>s==='.reading'?[]:articles;
 let observer;const spoken=[];const win={addEventListener(t,f){this[t]=f;},SpeechSynthesisUtterance:function(t){this.text=t;}};
 const synth={cancel(){},getVoices:()=>[{lang:'ja-JP'}],speak:u=>spoken.push(u)};if(supported)win.speechSynthesis=synth;
 vm.runInNewContext(code,{window:win,document:{getElementById:id=>elements[id]},SpeechSynthesisUtterance:win.SpeechSynthesisUtterance,MutationObserver:class{constructor(f){observer=f}observe(){}},localStorage:{getItem(){},setItem(){}}});
 return {elements,spoken,win,change:()=>observer()};
}
const s=setup(),e=s.elements;e.readPlay.click();assert.equal(s.spoken[0].lang,'ja-JP');assert.equal(e.readPlay.textContent,'一時停止');
let old=s.spoken.at(-1);e.readPlay.click();assert.equal(e.readPlay.textContent,'▶ 再開');old.onend();assert.equal(s.spoken.length,1);
e.readPlay.click();assert.equal(s.spoken.length,2);e.readNext.click();assert.match(e.readStatus.textContent,/2 \/ 2件/);
e.readRate.value='1.5';e.readRate.change();assert.equal(s.spoken.at(-1).rate,1.5);
old=s.spoken.at(-1);s.change();assert.equal(e.readStop.disabled,true);const count=s.spoken.length;old.onend();assert.equal(s.spoken.length,count);
e.readPlay.click();for(let i=0;i<30&&!e.readStop.disabled;i++)s.spoken.at(-1).onend();assert.match(e.readStatus.textContent,/すべて読み終え/);
e.readPlay.click();s.win.pagehide();assert.equal(e.readStop.disabled,true);
const unsupported=setup(false);assert.match(unsupported.elements.readStatus.textContent,/対応していません/);
console.log('PASS: Japanese voice, pause/restart, stale callbacks, next, speed, filter reset, completion, page exit, unsupported browser');
