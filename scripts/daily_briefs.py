"""Source-backed Japanese briefs. Never treat search popularity as public opinion."""
import html
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

NS={'ht':'https://trends.google.com/trending/rss'}

def clean(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', text or ''))).strip()

def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC',text)).casefold()

def relevant(topic,text):
    return normalized(topic) in normalized(text)

def japanese(text):
    return bool(re.search('[ぁ-んァ-ン一-龯]',text or ''))

def safe_url(url):
    p=urllib.parse.urlsplit(url)
    return p.scheme=='https' and bool(p.hostname) and not p.username

def fetch(url,timeout=8):
    if not safe_url(url):
        raise ValueError('HTTPS source required')
    req=urllib.request.Request(url,headers={'User-Agent':'IssueQuest/1.2 (+news briefs)'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(700_000).decode('utf-8',errors='replace')

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__();self.descriptions={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='meta':
            key=(attrs.get('property') or attrs.get('name') or '').lower()
            if key in ('og:description','description','twitter:description'):
                self.descriptions[key]=clean(attrs.get('content',''))

def description(raw):
    parser=Metadata();parser.feed(raw)
    for key in ('og:description','description','twitter:description'):
        text=parser.descriptions.get(key,'')
        if 25<=len(text)<=1500 and not re.search(r'ログイン|会員登録|購読して|subscribe|sign in|access denied|enable javascript',text,re.I):
            return text
    return ''

def short(text,limit=160):
    text=clean(text)
    sentences=re.findall(r'.+?[。！？!?](?:[」』])?|.+$',text)
    result=''
    for sentence in sentences:
        if re.search(r'(?:…|\.\.\.)$',sentence.strip()):break
        if len(result+sentence)>limit:break
        result+=sentence
    return result or (text if len(text)<=limit and not re.search(r'(?:…|\.\.\.)$',text) else '')

def translate(text):
    if japanese(text):return text
    query=urllib.parse.urlencode({'q':text[:300],'langpair':'en|ja'})
    obj=json.loads(fetch('https://api.mymemory.translated.net/get?'+query))
    result=clean(obj.get('responseData',{}).get('translatedText',''))
    if obj.get('responseStatus')!=200 or obj.get('quotaFinished') or not japanese(result):
        raise ValueError('Japanese translation unavailable')
    return result

def issue_for(topic,text):
    rules=[
      (r'中傷|誹謗|嫌がらせ', '被害を防ぐために、どの行為を問題とし、どんな対応が必要か？','正当な批判と攻撃を分け、被害者保護と表現の自由を両立する対応を考えるため。'),
      (r'構想外|移籍|退団|引退|契約解除', '所属や起用は何が変わる見込みで、本人とチームにどう影響するか？','決定済みの情報と見通しを分け、来季の活動や戦力への影響を理解するため。'),
      (r'指数|株価|ナスダック|日経平均|為替|相場', '値動きの要因は何で、一時的な変化と継続する変化をどう見分けるか？','期間や比較対象、複数の要因を確認し、一日の値動きだけで結論を出さないため。'),
      (r'マルシェ|まつり|祭り|地元事業|地域活性|にぎわい', '企画は地域のどんな課題に応え、住民や事業者にどのような効果があるか？','開催自体を目的にせず、参加・消費・継続性などの成果で評価するため。'),
      (r'ファンミーティング|ファンイベント', 'どのような交流や今後の活動が公表され、参加者に何が伝えられたか？','本人の発信と周囲の解釈を分け、活動や参加の判断につながる情報を押さえるため。'),
      (r'警報|大雨|台風|洪水|土砂|地震|避難', 'どの地域・時間帯に影響があり、生活や移動の予定をどう変える必要があるか？','対象地域・発表時刻・公式の最新情報を確かめ、行動を判断するため。'),
      (r'感染|医療|薬|治療|病院', '誰が対象で、効果・リスクについて何が確認されているか？','対象条件と根拠を分けて、情報を自分に当てはめてよいか判断するため。'),
      (r'選挙|政策|法案|首相|政府|予算|税率', '何が変わり、誰にどのような利益や負担が生じるか？','発言や計画と実施済みの内容を分け、生活への影響を判断するため。'),
      (r'価格|値上げ|物価|料金|発売|製品', '従来と比べて何が変わり、費用に見合う価値があるか？','価格・条件・代替案を比べ、利用や購入の判断につなげるため。'),
      (r'戦争|軍|停戦|外交|制裁', '確認された動きは何で、関係者や市民への影響はどう変わるか？','各当事者の主張と確認済みの事実を分け、影響を把握するため。'),
      (r'逮捕|容疑|疑惑|告発|不正|裁判|訴訟', '報道で確認された事実と主張はどこまでで、何が未確認か？','疑惑や一方の主張を確定事実として扱わず、判断の根拠を見極めるため。'),
      (r'試合|優勝|選手|大会|リーグ|ゴルフ|野球|NFL|nfl|サッカー|得点|決勝', '結果を左右した要因は何で、次の試合や順位にどう影響するか？','一度の結果だけでなく、成績・条件・今後の日程を比べて評価するため。'),
      (r'ドラマ|朝ドラ|番組|映画|出演|主演|予告編|放送|俳優|女優|あらすじ|主題歌', '作品・出演・放送について何が新しく発表され、いつ確認できるか？','公式の発表と感想・憶測を分け、作品を理解したり視聴を判断したりするため。'),
      (r'交際|熱愛|朝帰り|結婚|離婚|YouTuber|ユーチューバー|SNS', '本人の公表と周囲の推測を分けると、何が事実として確認できるか？','私生活についての憶測や反響の大きさだけで判断しないため。'),
      (r'死亡|死去|訃報', '公表された経緯と功績は何で、未確認の情報はどこか？','本人・関係者の発表と推測を区別し、出来事を正確に理解するため。'),
    ]
    for pattern,question,reason in rules:
        if re.search(pattern,text):return question,reason
    return f'「{topic}」について何が新しく確認され、誰の判断や行動に関係するか？','単に話題かどうかでなく、答えによって理解や行動が変わる問いかを確かめるため。'

def feed_articles(item):
    rows=[]
    for n in item.findall('ht:news_item',NS):
        row={k:clean(n.findtext('ht:news_item_'+field,'',NS)) for k,field in [('title','title'),('url','url'),('source','source'),('snippet','snippet')]}
        if row['title'] and safe_url(row['url']):rows.append(row)
    return rows

def search_articles(topic):
    query=urllib.parse.urlencode({'q':topic+' when:2d','hl':'ja','gl':'JP','ceid':'JP:ja'})
    root=ET.fromstring(fetch('https://news.google.com/rss/search?'+query))
    rows=[]
    for n in root.findall('./channel/item')[:8]:
        title=clean(n.findtext('title'));url=clean(n.findtext('link'))
        source=clean(n.findtext('source'))
        if source and title.endswith(' - '+source):title=title[:-len(source)-3]
        if relevant(topic,title) and safe_url(url):rows.append(dict(title=title,url=url,source=source,snippet='',publishedAt=n.findtext('pubDate')))
    return rows

def make_brief(topic,rows):
    candidates=[r for r in rows if relevant(topic,r['title']+' '+r.get('snippet',''))]
    if not candidates:
        try:candidates=search_articles(topic)
        except Exception:candidates=[]
    selected=[];seen=set()
    for row in candidates:
        key=normalized(row['title'])
        if key in seen:continue
        seen.add(key);selected.append(row)
        if len(selected)==2:break
    if not selected:return dict(topic=topic,status='unavailable')
    lead=selected[0]
    try:title=translate(lead['title'])
    except Exception:return dict(topic=topic,status='translation-unavailable')
    excerpt=lead.get('snippet','')
    if not excerpt:
        try:excerpt=description(fetch(lead['url']))
        except Exception:excerpt=''
    # An unrelated/generic publisher description is not a summary of this topic.
    if excerpt and not relevant(topic,excerpt):excerpt=''
    try:summary=short(translate(excerpt)) if excerpt else ''
    except Exception:summary=''
    basis='publisher-description' if summary else 'related-headline'
    summary=summary or short(title,180)
    if not summary:return dict(topic=topic,status='unavailable')
    question,reason=issue_for(topic,title+' '+summary)
    sources=[dict(title=title,url=lead['url'],name=lead['source'],publishedAt=lead.get('publishedAt'))]
    for row in selected[1:]:
        try:other=translate(row['title'])
        except Exception:continue
        sources.append(dict(title=other,url=row['url'],name=row['source'],publishedAt=row.get('publishedAt')))
    return dict(topic=topic,status='ok',summary=summary,summaryBasis=basis,issue=question,whyItMatters=reason,analysisBasis='related-news-rules',sources=sources)

def build_briefs(raw,topics):
    root=ET.fromstring(raw)
    by_topic={clean(item.findtext('title')):feed_articles(item) for item in root.findall('./channel/item')}
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(lambda t:make_brief(t,by_topic.get(t,[])),topics))
