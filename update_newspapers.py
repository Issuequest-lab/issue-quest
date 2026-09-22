"""Daily newspaper snapshots. No article bodies or paper images are republished."""
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
JST = ZoneInfo('Asia/Tokyo')
SOURCES = [
    dict(id='asahi-paper', name='朝日新聞', country='日本', kind='paper', lang='ja', url='https://www.asahi.com/shimen/{compact}/', edition='朝刊・公式記事一覧（地域版未確認）'),
    dict(id='guardian-paper', name='The Guardian', country='英国', kind='paper', lang='en', url='https://www.theguardian.com/theguardian', edition='公式紙面記事一覧（地域版未確認）'),
    dict(id='mainichi-paper', name='毎日新聞', country='日本', kind='paper', lang='ja', url='https://mainichi.jp/shimen/tokyo/m/?sd={compact}', edition='東京朝刊'),
    dict(id='mainichi-web', name='毎日新聞', country='日本', kind='web', lang='ja', url='https://mainichi.jp/', edition='日本向けWeb'),
    dict(id='guardian-web', name='The Guardian', country='英国', kind='web', lang='en', url='https://www.theguardian.com/uk', edition='英国向けWeb'),
]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'IssueQuest-Newspapers/1.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(3_000_000).decode('utf-8')

def clean(s):
    return re.sub(r'\s+', ' ', s).strip()

def parse(source, raw, day):
    soup = BeautifulSoup(raw, 'html.parser')
    sid = source['id']
    paper_date = None
    if sid == 'asahi-paper':
        title = soup.title.get_text() if soup.title else ''
        if f'{day[:4]}年{day[5:7]}月{day[8:]}日' not in title:
            raise ValueError('紙面の日付を確認できません')
        section = soup.select_one('#shimen-page1')
        if not section: raise ValueError('一面欄を確認できません')
        anchors = section.select('li.HeadlineTop > a, li.Fst > a, li > a')
        paper_date = day
    elif sid == 'guardian-paper':
        section = soup.select_one('#front-page')
        if not section: raise ValueError('一面欄を確認できません')
        date_el = section.select_one('.fc-container__header__description')
        if not date_el: raise ValueError('紙面の日付を確認できません')
        paper_date = datetime.strptime(clean(date_el.get_text()), '%A %d %B %Y').date().isoformat()
        if paper_date > day or paper_date < (datetime.fromisoformat(day)-timedelta(days=2)).date().isoformat():
            raise ValueError('紙面の日付が対象範囲外です')
        anchors = section.select('h3 a')
    elif sid == 'mainichi-paper':
        option=soup.select_one('select[name=soat] option[selected]') or soup.select_one('select[name=soat] option')
        if not option or clean(option.get_text()) != '/'.join(str(int(p)) for p in day.split('-')):
            raise ValueError('紙面の日付を確認できません')
        heading=next((h for h in soup.select('h2') if clean(h.get_text())=='1面'),None)
        if not heading: raise ValueError('一面欄を確認できません')
        section=heading.parent.parent
        anchors=section.select('a:has(h3.articlelist-title)')
        paper_date=day
    elif sid == 'mainichi-web':
        anchors = soup.select('.toppickup > a, .toppickuplist li > a')
    else:
        anchors = soup.select('main h3 a, main a:has(h3)')
    articles, seen = [], set()
    for a in anchors:
        heading = a.select_one('.js-headline-text, .toppickup-title, .toppickuplist-title, h3')
        title = clean((heading or a).get_text(' ', strip=True))
        url = urllib.parse.urljoin(source['url'].format(compact=day.replace('-', '')), a.get('href', '')).split('?')[0]
        if not url.startswith('https://') or '/articles/' not in url and source['lang']=='ja': continue
        if url in seen or not 8 <= len(title) <= 350 or title.startswith(('（天声人語）','（しつもん！')): continue
        seen.add(url)
        articles.append(dict(id=hashlib.sha256((source['id']+url).encode()).hexdigest()[:16], titleOriginal=title, url=url,
                             publicationDate=paper_date, verification='paper-listed' if source['kind']=='paper' else 'web-featured'))
        if len(articles)==(1 if sid=='guardian-web' else 3): break
    if not articles: raise ValueError('対象の見出しを確認できません')
    return paper_date, articles

def translate(title, cache):
    key=hashlib.sha256(title.encode()).hexdigest()
    if key in cache:return cache[key]
    if len(title.encode()) > 500: raise ValueError('翻訳対象が長すぎます')
    url='https://api.mymemory.translated.net/get?'+urllib.parse.urlencode(dict(q=title,langpair='en|ja'))
    result=json.loads(fetch(url))
    value=html.unescape(result.get('responseData',{}).get('translatedText','')).strip()
    if result.get('responseStatus')!=200 or not re.search('[ぁ-んァ-ン一-龯]',value) or result.get('quotaFinished'):
        raise ValueError('日本語訳を取得できません')
    cache[key]=value
    return value

def write_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    os.replace(temp,path)

def read_json(path,default):
    return json.loads(path.read_text()) if path.exists() else default

def archive(root,payload):
    day=payload['date']; rel=f'newspapers/{day[:7]}/{day}.json'
    # Retries add a snapshot; prior successful editions remain available.
    daily=read_json(root/rel,dict(date=day,snapshots=[]))
    daily['snapshots'].append(payload)
    write_json(root/rel,daily)
    index=read_json(root/'newspaper-index.json',dict(days=[]))
    index['days']=sorted(set(index['days'])|{day},reverse=True)
    index['updatedAt']=payload['fetchedAt']
    write_json(root/'newspaper-index.json',index)
    write_json(root/'newspaper-latest.json',payload)

def main():
    now=datetime.now(JST);day=now.date().isoformat()
    cache=read_json(ROOT/'newspaper-translations.json',{})
    previous=read_json(ROOT/'newspaper-latest.json',{})
    def collect(source):
        entry=dict(source, sourceUrl=source['url'].format(compact=day.replace('-','')), fetchedAt=now.isoformat(),articles=[])
        entry.pop('url')
        try:
            raw=fetch(entry['sourceUrl']); date, articles=parse(source,raw,day)
            entry.update(status='ok',paperDate=date,articles=articles)
        except Exception as e:
            entry.update(status='unavailable',error='取得または掲載位置・日付の確認に失敗しました')
            print(source['id'],type(e).__name__,str(e)[:100])
        return entry
    entries=list(ThreadPoolExecutor(max_workers=4).map(collect,SOURCES))
    old={s['id']:s for s in previous.get('sources',[])}
    for entry in entries:
        old_urls={a['url'] for a in old.get(entry['id'],{}).get('articles',[])}
        comparison_date=previous.get('date')
        for a in entry['articles']:
            a['change']='same' if a['url'] in old_urls else 'new'
            a['comparedWith']=comparison_date if old_urls else None
            try:
                a['titleJa']=a['titleOriginal'] if entry['lang']=='ja' else translate(a['titleOriginal'],cache)
                a['translation']='original-ja' if entry['lang']=='ja' else 'machine'
            except Exception:
                a['titleJa']=None;a['translation']='unavailable'
    payload=dict(schemaVersion=1,date=day,fetchedAt=now.isoformat(),sources=entries)
    if previous.get('date') and not (ROOT / f"newspapers/{previous['date'][:7]}/{previous['date']}.json").exists():
        archive(ROOT,previous)
    archive(ROOT,payload)
    write_json(ROOT/'newspaper-translations.json',cache)
    print('Saved',day,sum(len(s['articles']) for s in entries),'headlines')

if __name__=='__main__': main()
