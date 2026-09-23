"""Daily newspaper snapshots. No article bodies or paper images are republished."""
import hashlib
import html
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
JST = ZoneInfo('Asia/Tokyo')

# One comparison set: 4 Japanese outlets + 8 overseas outlets.
# Paper sources are kept where an official dated front-page/article-list page is available.
SOURCES = [
    dict(id='asahi-paper', name='朝日新聞', country='日本', region='日本', kind='paper', lang='ja',
         url='https://www.asahi.com/shimen/{compact}/', edition='朝刊・公式記事一覧（地域版未確認）', max_articles=3),
    dict(id='guardian-paper', name='The Guardian', country='英国', region='英国', kind='paper', lang='en',
         url='https://www.theguardian.com/theguardian', edition='公式紙面記事一覧（地域版未確認）', max_articles=3),
    dict(id='mainichi-paper', name='毎日新聞', country='日本', region='日本', kind='paper', lang='ja',
         url='https://mainichi.jp/shimen/tokyo/m/?sd={compact}', edition='東京朝刊', max_articles=3),

    dict(id='asahi-web', name='朝日新聞', country='日本', region='日本', kind='web', lang='ja',
         url='https://www.asahi.com/', edition='日本向けWeb', domain='asahi.com', max_articles=1,
         selectors='.p-topNews__firstNews a.c-articleModule__link[data-realizer-area="TopNews:1"]'),
    dict(id='mainichi-web', name='毎日新聞', country='日本', region='日本', kind='web', lang='ja',
         url='https://mainichi.jp/', edition='日本向けWeb', domain='mainichi.jp', max_articles=1,
         selectors='.toppickup > a, .toppickuplist li > a, main article h2 a, main article h3 a'),
    dict(id='yomiuri-web', name='読売新聞', country='日本', region='日本', kind='web', lang='ja',
         url='https://www.yomiuri.co.jp/', edition='日本向けWeb', domain='yomiuri.co.jp', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'),
    dict(id='nikkei-web', name='日本経済新聞', country='日本', region='日本', kind='web', lang='ja',
         url='https://www.nikkei.com/', edition='日本向けWeb', domain='nikkei.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'),

    dict(id='guardian-web', name='The Guardian', country='英国', region='英国', kind='web', lang='en',
         url='https://www.theguardian.com/international', edition='国際版Web', domain='theguardian.com', max_articles=1,
         selectors='main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)', fallback_url='https://www.theguardian.com/world/rss'),
    dict(id='nyt-web', name='The New York Times', country='米国', region='米国', kind='web', lang='en',
         url='https://www.nytimes.com/international/', edition='国際版Web', domain='nytimes.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)',
         fallback_url='https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
    dict(id='ft-web', name='Financial Times', country='英国', region='英国', kind='web', lang='en',
         url='https://www.ft.com/', edition='国際版Web', domain='ft.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'),
    dict(id='reuters-web', name='Reuters', country='国際', region='通信社', kind='web', lang='en',
         url='https://www.reuters.com/', edition='国際版Web', domain='reuters.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'),
    dict(id='lemonde-web', name='Le Monde', country='フランス', region='欧州', kind='web', lang='en',
         url='https://www.lemonde.fr/en/', edition='英語版Web', domain='lemonde.fr', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'),
    dict(id='aljazeera-web', name='Al Jazeera', country='カタール', region='中東・グローバルサウス', kind='web', lang='en',
         url='https://www.aljazeera.com/', edition='英語版Web', domain='aljazeera.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)',
         fallback_url='https://www.aljazeera.com/xml/rss/all.xml'),
    dict(id='scmp-web', name='South China Morning Post', country='香港', region='アジア', kind='web', lang='en',
         url='https://www.scmp.com/', edition='国際版Web', domain='scmp.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'),
    dict(id='bbc-web', name='BBC News', country='英国', region='英国', kind='web', lang='en',
         url='https://www.bbc.com/news', edition='国際版Web', domain='bbc.com', max_articles=1,
         selectors='main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)',
         fallback_url='https://feeds.bbci.co.uk/news/rss.xml'),
]

ISSUE_RULES = [
    (r'気候|エルニーニョ|温暖化|\b(?:climate|El Niño)\b', '気候変動による被害を抑えるため、何を優先すべきか？'),
    (r'起業|创业|entrepreneur', '事業を続けるために必要な条件と課題は何か？'),
    (r'価格|EV|半導体|物価|インフレ|\b(?:price|inflation)\b', '価格や競争の変化は、消費者と産業にどう影響するか？'),
    (r'皇室|天皇|神武', '歴史に関する主張を、どの根拠で確かめるべきか？'),
    (r'極右|選挙|政権交代|\b(?:election|far.right)\b', '政治勢力の変化は、政策や統治にどう影響するか？'),

    (r'ICC|国際刑事裁判所|International Criminal Court', '各国の対応は、国際司法の機能にどう影響するか？'),
    (r'台風|土砂|洪水|地震|災害|\b(?:typhoon|storm|flood|earthquake)\b', '被害の状況から、救助・復旧で何を優先すべきか？'),
    (r'開発|投資|ビーチ|\b(?:development|investment)\b', '開発・投資の利益と地域への負担をどう評価するか？'),
    (r'NHS|A&E|Martha|病院|医療|患者|\b(?:medical|hospital|health)\b', '患者の安全を守るため、どの仕組みを変えるべきか？'),
    (r'ドローン|戦場|軍|戦争|安全保障|フーシ|イラン|ウクライナ|\b(?:Houthi|Iran|Ukraine|military|war)\b', '安全保障上の変化に、関係国はどう対応すべきか？'),
    (r'飲酒|事故|遺族|被害者|\b(?:crash|accident)\b', '被害の原因をどう確かめ、再発を防ぐか？'),
    (r'日米|首脳|同盟|国連|外交|制裁|\b(?:allies|summit|diplomacy)\b', '各国の立場の違いは、協調や交渉にどう影響するか？'),
]

class SourceError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fetch(url, timeout=25, max_bytes=3_000_000):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'IssueQuest-Newspapers/2.0 (+https://issuequest-lab.github.io/issue-quest/)',
        'Accept-Language': 'ja,en-US;q=0.8,en;q=0.7',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(max_bytes).decode('utf-8', errors='replace')


def clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def shorten(s, limit=120):
    s = clean(html.unescape(s or ''))
    if len(s) <= limit:
        return s
    return s[:limit].rstrip(' 、,。.!?…') + '…'


def _utf8_limit(s, max_bytes=450):
    raw = clean(s).encode('utf-8')
    if len(raw) <= max_bytes:
        return clean(s)
    return raw[:max_bytes].decode('utf-8', errors='ignore').rstrip(' 、,。.!?…') + '…'


def extract_description(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    selectors = [
        ('meta', {'property': 'og:description'}),
        ('meta', {'name': 'description'}),
        ('meta', {'name': 'twitter:description'}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs=attrs)
        value = clean(el.get('content', '')) if el else ''
        if len(value) >= 30 and not re.search(r'購読|会員登録|ログイン|subscribe|sign in|access denied|enable javascript', value, re.I):
            return shorten(value, 180)

    def find_description(obj):
        if isinstance(obj, dict):
            value = obj.get('description')
            if obj.get('@type') in ('NewsArticle', 'Article', 'ReportageNewsArticle') and isinstance(value, str) and len(clean(value)) >= 30:
                return clean(value)
            for child in obj.values():
                found = find_description(child)
                if found:
                    return found
        elif isinstance(obj, list):
            for child in obj:
                found = find_description(child)
                if found:
                    return found
        return None

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = find_description(json.loads(script.string or script.get_text()))
        except (json.JSONDecodeError, TypeError):
            value = None
        if value:
            return shorten(value, 180)

    return None


def derive_issue(text):
    text = unicodedata.normalize('NFKC', clean(text))
    for pattern, label in ISSUE_RULES:
        if re.search(pattern, text, flags=re.I):
            return label
    return None


def derive_viewpoint(text):
    text = unicodedata.normalize('NFKC', clean(text))
    if re.search(r'死亡|不明|遺族|両親|被害者|victim|killed|dead|missing', text, flags=re.I):
        return '被害者・当事者への影響を前面に置く'
    if re.search(r'\d+(?:[,.]\d+)?\s*(?:人|億|兆|%|ドル|円|billion|million)', text, flags=re.I):
        return '人数・金額など具体的な規模を前面に置く'
    if re.search(r'計画|方針|支援|拡大|導入|plan|policy|support|expand', text, flags=re.I):
        return '政策・計画の内容と実施方針に焦点を置く'
    if re.search(r'「|」|said|says|speech|演説|発言', text, flags=re.I):
        return '引用した言葉や表現を前面に置く'
    if re.search(r'ICC|国連|首脳|同盟|外交|制裁|allies|summit|diploma', text, flags=re.I):
        return '外交上の立場や各国関係に焦点を置く'
    if re.search(r'ドローン|戦場|軍|安全保障|military|drone', text, re.I):
        return '軍事技術や安全保障の変化に焦点を置く'
    if re.search(r'台風|被災|災害|爪痕|storm|flood', text, re.I):
        return '災害による現地への影響に焦点を置く'
    if re.search(r'関係|会談|対話|交渉|talks|relations', text, re.I):
        return '関係国の対話や関係の変化に焦点を置く'
    if re.search(r'気候|温暖化|エルニーニョ|climate', text, re.I):
        return '気候変動の影響や対策に焦点を置く'
    return None


def _jp_date_in_text(text):
    m = re.search(r'(20\d{2})年\s*0?(\d{1,2})月\s*0?(\d{1,2})日', text)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    return f'{y:04d}-{mo:02d}-{d:02d}'


def _normalize_slash_date(text):
    m = re.search(r'(20\d{2})\s*/\s*0?(\d{1,2})\s*/\s*0?(\d{1,2})', text)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    return f'{y:04d}-{mo:02d}-{d:02d}'


def _article_from_anchor(source, a, publication_date=None, verification='web-featured', date_basis=None):
    heading = a.select_one('.js-headline-text, .toppickup-title, .toppickuplist-title, h1, h2, h3')
    title = clean((heading or a).get_text(' ', strip=True))
    href = a.get('href', '')
    url = urllib.parse.urljoin(source['url'].format(compact=''), href).split('#')[0]
    if not url.startswith('https://'):
        return None
    if source.get('domain'):
        host = (urllib.parse.urlparse(url).hostname or '').lower()
        domain = source['domain'].lower()
        if host != domain and not host.endswith('.' + domain):
            return None
    blocked = {
        'ホーム', 'ニュース', '社会', '政治', '経済', '国際', 'スポーツ', '文化', 'ライフ',
        'Home', 'News', 'World', 'Business', 'Politics', 'Sport', 'Sports', 'Culture', 'Opinion',
        'Live', 'More', 'Menu', 'Sign in', 'Subscribe'
    }
    if title in blocked or not 8 <= len(title) <= 350:
        return None
    return dict(
        id=hashlib.sha256((source['id'] + url).encode()).hexdigest()[:16],
        titleOriginal=title,
        url=url,
        publicationDate=publication_date,
        verification=verification,
        **({'dateBasis': date_basis} if date_basis else {}),
    )


def parse(source, raw, day):
    soup = BeautifulSoup(raw, 'html.parser')
    sid = source['id']
    paper_date = None
    date_basis = None

    if sid == 'asahi-paper':
        title = soup.title.get_text(' ', strip=True) if soup.title else ''
        detected = _jp_date_in_text(title)
        if detected and detected != day:
            raise SourceError('date-unverified', '紙面の日付が取得日と一致しません')
        section = soup.select_one('#shimen-page1')
        if not section:
            raise SourceError('position-unverified', '一面欄を確認できません')
        anchors = section.select('li.HeadlineTop > a, li.Fst > a, li > a')
        if not detected:
            raise SourceError('date-unverified', '紙面の発行日を確認できません')
        paper_date = detected

    elif sid == 'guardian-paper':
        section = soup.select_one('#front-page')
        if not section:
            raise SourceError('position-unverified', '一面欄を確認できません')
        date_el = section.select_one('.fc-container__header__description')
        if not date_el:
            raise SourceError('date-unverified', '紙面の日付を確認できません')
        try:
            paper_date = datetime.strptime(clean(date_el.get_text()), '%A %d %B %Y').date().isoformat()
        except ValueError as e:
            raise SourceError('date-unverified', '紙面の日付形式を確認できません') from e
        if paper_date > day or paper_date < (datetime.fromisoformat(day)-timedelta(days=2)).date().isoformat():
            raise SourceError('date-unverified', '紙面の日付が対象範囲外です')
        anchors = section.select('h3 a')

    elif sid == 'mainichi-paper':
        option = soup.select_one('select[name=soat] option[selected]') or soup.select_one('select[name=soat] option')
        if option:
            detected = _normalize_slash_date(clean(option.get_text()))
            if detected and detected != day:
                raise SourceError('date-unverified', '紙面の日付が取得日と一致しません')
        if not option or not detected:
            raise SourceError('date-unverified', '紙面の発行日を確認できません')
        heading = next((h for h in soup.select('h1,h2,h3') if clean(h.get_text()) in {'1面', '１面'}), None)
        if not heading:
            raise SourceError('position-unverified', '一面欄を確認できません')
        section = heading.parent
        anchors = []
        for _ in range(3):
            anchors = section.select('a:has(h3.articlelist-title), article a, h3 a')
            if anchors:
                break
            section = section.parent
        paper_date = detected

    else:
        selectors = source.get('selectors') or 'main article h2 a, main article h3 a, main h1 a, main h2 a, main h3 a, main a:has(h1), main a:has(h2), main a:has(h3)'
        anchors = soup.select(selectors)
        if not anchors:
            raise SourceError('position-unverified', '主要見出しの掲載位置を確認できません')

    articles, seen = [], set()
    max_articles = source.get('max_articles', 1 if source['kind'] == 'web' else 3)
    for a in anchors:
        article = _article_from_anchor(
            source, a, publication_date=paper_date,
            verification='paper-listed' if source['kind'] == 'paper' else 'web-featured',
            date_basis=date_basis,
        )
        if not article or article['url'] in seen:
            continue
        if article['titleOriginal'].startswith(('（天声人語）', '（しつもん！')):
            continue
        seen.add(article['url'])
        articles.append(article)
        if len(articles) >= max_articles:
            break
    if not articles:
        raise SourceError('no-headlines', '対象の見出しを確認できません')
    return paper_date, articles


def parse_feed(source, raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise SourceError('no-headlines', '公式フィードを解析できません') from e
    rows = []
    for item in root.findall('.//item'):
        title = clean(item.findtext('title') or '')
        url = clean(item.findtext('link') or '')
        if title and url:
            rows.append((title, url))
    if not rows:
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('.//a:entry', ns):
            title = clean(entry.findtext('a:title', default='', namespaces=ns))
            link_el = entry.find('a:link', ns)
            url = clean(link_el.get('href', '') if link_el is not None else '')
            if title and url:
                rows.append((title, url))
    articles = []
    for title, url in rows:
        if not url.startswith('https://') or not 8 <= len(title) <= 350:
            continue
        articles.append(dict(
            id=hashlib.sha256((source['id'] + url).encode()).hexdigest()[:16],
            titleOriginal=title,
            url=url,
            publicationDate=None,
            verification='feed-featured',
        ))
        if len(articles) >= source.get('max_articles', 1):
            break
    if not articles:
        raise SourceError('no-headlines', '公式フィードに見出しがありません')
    return None, articles


def translate(title, cache, source_lang='en'):
    key=hashlib.sha256((source_lang+'|'+title).encode()).hexdigest()
    if key in cache:
        return cache[key]
    if len(title.encode()) > 500:
        raise ValueError('翻訳対象が長すぎます')
    # MyMemory supports many language pairs. Non-English sources are translated directly to Japanese.
    url='https://api.mymemory.translated.net/get?'+urllib.parse.urlencode(dict(q=title,langpair=f'{source_lang}|ja'))
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
        for key in ('url','selectors','domain','fallback_url','max_articles'):
            entry.pop(key, None)
        try:
            try:
                raw=fetch(source['url'].format(compact=day.replace('-','')))
                date, articles=parse(source,raw,day)
            except Exception as primary:
                fallback=source.get('fallback_url')
                if not fallback:
                    raise
                try:
                    raw=fetch(fallback)
                    date,articles=parse_feed(source,raw)
                    entry['fallbackUsed']=True
                    entry['sourceUrl']=fallback
                except Exception:
                    raise primary
            entry.update(status='ok',paperDate=date,articles=articles)
        except SourceError as e:
            entry.update(status='unavailable',errorCode=e.code,error=str(e))
            print(source['id'],e.code,str(e)[:120])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            entry.update(status='unavailable',errorCode='fetch-failed',error='取得に失敗しました')
            print(source['id'],'fetch-failed',type(e).__name__,str(e)[:120])
        except Exception as e:
            entry.update(status='unavailable',errorCode='parse-failed',error='取得内容の確認に失敗しました')
            print(source['id'],'parse-failed',type(e).__name__,str(e)[:120])
        return entry

    entries=list(ThreadPoolExecutor(max_workers=6).map(collect,SOURCES))
    old={s['id']:s for s in previous.get('sources',[])}
    article_pairs=[]
    for entry in entries:
        old_urls={a['url'] for a in old.get(entry['id'],{}).get('articles',[])}
        comparison_date=previous.get('date')
        for a in entry['articles']:
            a['change']='same' if a['url'] in old_urls else 'new'
            a['comparedWith']=comparison_date if old_urls else None
            try:
                if entry['lang']=='ja':
                    a['titleJa']=a['titleOriginal'];a['translation']='original-ja'
                else:
                    a['titleJa']=translate(a['titleOriginal'],cache,entry['lang'])
                    a['translation']='machine'
            except Exception:
                a['titleJa']=None;a['translation']='unavailable'
            article_pairs.append((entry,a))

    def fetch_description(pair):
        _, article = pair
        try:
            return extract_description(fetch(article['url'], timeout=12, max_bytes=1_200_000))
        except Exception:
            return None

    descriptions=list(ThreadPoolExecutor(max_workers=6).map(fetch_description, article_pairs))
    for (entry,a), description in zip(article_pairs, descriptions):
        title_ja=a.get('titleJa') or a['titleOriginal']
        summary=None
        if description:
            try:
                if entry['lang']=='ja':
                    summary=shorten(description,100)
                else:
                    summary=shorten(translate(_utf8_limit(description),cache,entry['lang']),100)
            except Exception:
                summary=None
        a['summaryBasis']='publisher-description' if summary else 'unavailable'
        a['summaryStatus']='ok' if summary else ('translation-failed' if description else 'description-unavailable')
        a['summaryJa']=summary
        a['summaryOriginal']=description
        a['summarySourceUrl']=a['url']
        # Suggestions are derived from the headline, not asserted publisher intent.
        a['issue']=derive_issue(title_ja)
        a['viewpoint']=derive_viewpoint(title_ja)
        a['analysisBasis']='headline-rules'

    payload=dict(schemaVersion=3,date=day,fetchedAt=now.isoformat(),sources=entries)
    if previous.get('date') and not (ROOT / f"newspapers/{previous['date'][:7]}/{previous['date']}.json").exists():
        archive(ROOT,previous)
    archive(ROOT,payload)
    write_json(ROOT/'newspaper-translations.json',cache)
    print('Saved',day,sum(len(s['articles']) for s in entries),'headlines from',sum(s['status']=='ok' for s in entries),'sources')

if __name__=='__main__': main()
