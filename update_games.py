"""Collect bounded official Japanese patch notes; preserve dated, monthly snapshots."""
import concurrent.futures
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CATEGORIES = {
    '安定性': r'クラッシュ|進行不能|進行でき|フリーズ|ハング|強制終了|セーブ|起動',
    '性能・画質': r'フレーム|FPS|VRAM|CPU|GPU|描画|パフォーマンス|レイトレーシング|カクつ|グラフィック|解像度',
    '操作性': r'操作|カメラ|キー|ボタン|ロックオン|メニュー|地図|UI|設定|利便',
    'バランス': r'威力|攻撃力|ダメージ|上方|下方|バランス|消費|効果時間|性能調整',
    'コンテンツ': r'追加|新たな|DLC|拡張|クエスト|ミッション',
}

def clean(s): return re.sub(r'\s+', ' ', s).strip()
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def parse_date(s):
    m = re.search(r'(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})', s)
    if not m: return None
    try: return date(*map(int,m.groups())).isoformat()
    except ValueError: return None

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'IssueQuest-GameUpdates/1.0 (+https://issuequest-lab.github.io/issue-quest/)','Accept-Language':'ja'})
    with urllib.request.urlopen(req,timeout=20) as r:
        b=r.read(3_000_001)
        if len(b)>3_000_000: raise ValueError('response-too-large')
        return b.decode('utf-8')

def platforms(text):
    result=[]
    for label,pattern in [('PS5',r'PlayStation\s*[®™]?\s*5|PS5'),('PS4',r'PlayStation\s*[®™]?\s*4|PS4'),('PC',r'Steam|PC版|Windows'),('Xbox',r'Xbox'),('Switch 2',r'Switch\s*2')]:
        if re.search(pattern,text,re.I):result.append(label)
    return result

def classify(text):
    return next((k for k,v in CATEGORIES.items() if re.search(v,text,re.I)), 'その他の修正')

def make_record(game,url,title,day,scope,body,lines,now):
    if not day or day > now[:10]: raise ValueError('date-unverified-or-future')
    if day < game['releaseDate']: return None
    version=re.search(r'(?:App\s*Ver\.?|Version|Ver\.?)\s*([0-9]+(?:\.[0-9]+)+)',body,re.I)
    changes=[];seen=set()
    for text in lines:
        text=clean(text)
        if len(text)<8 or text in seen:continue
        if not re.search(r'修正|追加|調整|変更|改善|最適化|緩和|削減|対応',text):continue
        if re.search(r'適用.*(?:ください|必要)|よろしく|詳細.*(?:サイト|確認)|予定|今後',text):continue
        seen.add(text)
        changes.append({'category':classify(text),'text':text if len(text)<=180 else text[:177]+'…','excerpt':True,'platforms':platforms(text) or scope})
    if not changes:raise ValueError('changes-unverified')
    # A concise selection, not a mirror of the full patch note.
    chosen=[]
    for category in [*CATEGORIES,'その他の修正']:
        found=next((x for x in changes if x['category']==category),None)
        if found:chosen.append(found)
    chosen=chosen[:4]
    return {'id':digest(url)[:20],'url':url,'date':day,'title':title,'version':version.group(1) if version else '未確認','platforms':scope,'platformBasis':'公式の対象機種表記（FF16初期分はPS5独占期間）','changes':chosen,'categories':list(dict.fromkeys(c['category'] for c in changes)),'contentHash':digest(body),'lastVerifiedAt':now,'firstSeenAt':now,'evidence':'公式発表／実機検証なし'}

def parse_detail(game,url,title,day,html,now):
    soup=BeautifulSoup(html,'html.parser');article=soup.select_one('article')
    if not article:raise ValueError('article-not-found')
    body=article.get_text(' ',strip=True)
    scope=[]
    if game['parser']=='elden':
        marker=article.find(string=re.compile('対象プラットフォーム'))
        if marker:scope=platforms(marker.parent.find_next_sibling().get_text(' ',strip=True))
        lines=[x.get_text(' ',strip=True) for x in article.select('li') if not x.find('li')]
    else:
        scope=['PC'] if 'PC版' in title else ['PS5'] if day<game.get('ps5ExclusiveUntil','') else []
        lines=[x.get_text(' ',strip=True) for x in article.select('.p-news-main_area li, .p-news-main_area p') if not x.find('li')]
    return make_record(game,url,title,day,scope,body,lines,now)

def discover(game,html):
    if game['parser']=='ff16':
        data=json.loads(html)
        return [(urllib.parse.urljoin(game['source'],x['link']['url']),x['title'],parse_date(x['date'])) for x in data if x.get('label')=='UPDATE' and '体験版' not in x['title'] and x['link'].get('mode')=='link']
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for a in soup.select('a[href]'):
        title=a.get_text(' ',strip=True);url=urllib.parse.urljoin(game['source'],a['href'])
        if urllib.parse.urlparse(url).netloc!=urllib.parse.urlparse(game['source']).netloc:continue
        if '/newsdetail/' in url and re.search(r'アップデート|レギュレーション',title):rows.append((url,title,parse_date(title)))
    return list(dict.fromkeys(rows))

def parse_ronin(game,html,now):
    soup=BeautifulSoup(html,'html.parser');result=[]
    for section in soup.select('section.topics-section[id]'):
        h=section.select_one('h5')
        if not h:continue
        title=h.get_text(' ',strip=True);scope=platforms(title)
        record=make_record(game,game['source']+'#'+section['id'],title,parse_date(title),scope,section.get_text(' ',strip=True),[x.get_text(' ',strip=True) for x in section.select('li') if not x.find('li')],now)
        if record:result.append(record)
    return result

def collect(game,old,now):
    records={r['id']:r for r in old.get('updates',[])};errors=[];fresh=[]
    try:
        html=fetch(game['source'])
        if game['parser']=='ronin':fresh=parse_ronin(game,html,now)
        else:
            refs=discover(game,html)
            if not refs:raise ValueError('update-index-empty')
            def read(ref):
                url,title,day=ref
                if not day or day<game['releaseDate'] or day>now[:10]:return None
                # Recheck every record, including edited historical notes.
                return parse_detail(game,url,title,day,fetch(url),now)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures={pool.submit(read,ref):ref for ref in refs}
                for f,ref in futures.items():
                    try:
                        result=f.result()
                        if result:fresh.append(result)
                    except Exception as exc:errors.append({'url':ref[0],'reason':type(exc).__name__})
        if not fresh:raise ValueError('no-confirmed-updates')
        state='partial' if errors else 'ok'
    except Exception as exc:
        errors.append({'url':game['source'],'reason':type(exc).__name__});state='failed'
    for r in fresh:
        previous=records.get(r['id'])
        if previous:r['firstSeenAt']=previous.get('firstSeenAt',now)
        records[r['id']]=r
    return {**game,'checkedAt':now,'sourceStatus':state,'errors':errors,'updates':sorted(records.values(),key=lambda x:(x['date'],x['id']),reverse=True),'coverage':'取得できた公式履歴のみ。全更新の網羅・現在の実機状態は未確認。'}

def save(root,payload):
    day=payload['date'];month=day[:7];directory=root/'game-updates'/month;directory.mkdir(parents=True,exist_ok=True)
    path=directory/(day+'.json');archive=json.loads(path.read_text()) if path.exists() else {'date':day,'snapshots':[]}
    if not any(s['checkedAt']==payload['checkedAt'] for s in archive['snapshots']):archive['snapshots'].append(payload)
    def write(path,data):
        temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.replace(path)
    write(path,archive);write(root/'game-updates-latest.json',payload)
    days=sorted((p.stem for p in (root/'game-updates').glob('*/*.json')),reverse=True)
    write(root/'game-updates-index.json',{'updatedAt':payload['checkedAt'],'days':days})

def main():
    now=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds')
    catalog=json.loads((ROOT/'game-catalog.json').read_text())['games'];path=ROOT/'game-updates-latest.json'
    old=json.loads(path.read_text()) if path.exists() else {'games':[]};previous={g['id']:g for g in old['games']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:games=list(pool.map(lambda g:collect(g,previous.get(g['id'],{}),now),catalog))
    payload={'schemaVersion':1,'date':now[:10],'checkedAt':now,'games':games};save(ROOT,payload)
    print(json.dumps([{'game':g['id'],'status':g['sourceStatus'],'updates':len(g['updates'])} for g in games],ensure_ascii=False))
    if all(g['sourceStatus']=='failed' for g in games):print('WARNING: all sources failed; preserved previous records with explicit failed status')
if __name__=='__main__':main()
