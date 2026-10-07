'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync(__dirname+'/newspapers.js','utf8');
const ctx={URL,editorial:{}};vm.createContext(ctx);
vm.runInContext(code.slice(code.indexOf('const REGION_ORDER'),code.indexOf('const dayJst'))+code.slice(code.indexOf('function verificationLabel'),code.indexOf('function failureLabel'))+code.slice(code.indexOf('function compactSummary'),code.indexOf('function card'))+code.slice(code.indexOf('function regionFor'),code.indexOf('function render')),ctx);
const source=(id='guardian-paper',n=3)=>({id,name:id,country:'英国',region:'ヨーロッパ',kind:'paper',status:'ok',articles:Array.from({length:n},(_,i)=>({id:id+i,titleJa:'日本語の見出し'+i,summaryJa:'出来事を説明する日本語の要約です。',url:'https://example.test/'+id+'/'+i,translation:'machine',publicationDate:'2026-10-08',verification:'paper-listed'}))});
const paper=source();assert.equal(ctx.readingList([paper]).rows.length,3);
const rss=source('bangkokpost-web');rss.kind='web';rss.country='タイ';rss.articles.forEach(a=>a.verification='feed-featured');
assert.equal(ctx.readingList([rss]).rows.length,0);
const web=source('china-web');web.kind='web';web.articles.forEach(a=>a.verification='web-featured');
assert.equal(ctx.readingList([web]).rows.length,0);
assert.equal(ctx.readingList([paper,rss,web]).rows.length,3); // Never fill a regional quota.
assert.equal(ctx.readingList([source('guardian-paper',25)]).rows.length,25); // No 20-item target.
web.articles[0].verification='web-top';assert.equal(ctx.readingList([web]).rows.length,0);
web.articles[0].positionEvidence={type:'web-top',selector:'.lead'};assert.equal(ctx.readingList([web]).rows.length,1);
const mainichi=source('mainichi-paper');mainichi.country='日本';mainichi.articles[0].url='https://mainichi.jp/articles/20261008/ddm/001/040/123000c';mainichi.articles[1].url='https://mainichi.jp/articles/20261008/ddm/013/040/123000c';
assert.equal(ctx.readingList([mainichi]).rows.length,1);
const unavailable=source();unavailable.status='unavailable';assert.equal(ctx.readingList([unavailable]).rows.length,0);
const empty=source();empty.articles.forEach(a=>delete a.summaryJa);assert.equal(ctx.readingList([empty]).rows.length,0);
ctx.editorial[rss.articles[0].url]={verification:'web-top',positionEvidence:{type:'web-top',selector:'.fake'},summaryJa:'説明です。'};assert.equal(ctx.readingList([rss]).rows.length,0);
assert.match(ctx.verificationLabel(paper.articles[0]),/トップ順位は未確認/);
assert.match(ctx.verificationLabel(web.articles[0]),/紙面とは別/);
console.log('PASS verified placements only, historical RSS excluded, no quotas, page boundaries, missing summaries');
vm.runInContext(code.slice(code.indexOf('function compactSummary'),code.indexOf('function card')),ctx);
assert.equal(ctx.compactSummary({}),null);
assert.equal(ctx.compactSummary({summaryJa:'途中で終わった説明…'}),null);
assert.equal(ctx.compactSummary({summaryJa:'完結した説明です。続き…'}).text,'完結した説明です。');
const pope=ctx.headlineInsights({titleJa:'教皇レオ14世がヨーロッパの統一について話すためにメスに到着'});
assert.match(pope.issue,/欧州の結束/);assert.match(pope.viewpoint,/発言/);
assert.equal(ctx.headlineInsights({titleJa:'新しい詩集を発表'}).issue,null);
assert.equal(ctx.headlineInsights({titleJa:'AIへの懸念',issue:'既存の問い'}).issue,'既存の問い');
console.log('PASS absent insights, complete summary sentences, grounded headline prompts');

