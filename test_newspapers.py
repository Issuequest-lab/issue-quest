import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import update_newspapers as u

class NewspaperTests(unittest.TestCase):
    def test_clipped_metadata_falls_back_to_public_article_paragraphs(self):
        text='北京では住宅環境の変化により鳩を飼う場所が減り、文化を継ぐ若い人の不足が課題となっています。'
        raw=f'<meta name="description" content="1934年の随筆を紹介する冒頭だけの説明文で終わる…"><article><p>{text}</p></article>'
        self.assertEqual(u.extract_description(raw),text)
    def test_summary_does_not_append_clipped_tail(self):
        self.assertEqual(u.complete_summary('出来事を説明します。続きは途中…'),'出来事を説明します。')
        self.assertIsNone(u.complete_summary('紹介の冒頭しかなく途中で切れた説明…'))

    def test_generic_homepage_headings_are_not_top_position_evidence(self):
        source=next(s for s in u.SOURCES if s['id']=='aljazeera-web')
        raw='<main><h2><a href="/news/recipe">A food story in a general list</a></h2></main>'
        with self.assertRaises(u.SourceError) as cm:u.parse(source,raw,'2026-10-08')
        self.assertEqual(cm.exception.code,'position-unverified')

    def test_description_prefers_article_metadata_and_rejects_login(self):
        text='地域の開発計画について、規模と住民への影響を専門家と現地の取材から説明する記事です。'
        self.assertEqual(u.extract_description(f'<meta property="og:description" content="{text}">'),text)
        self.assertIsNone(u.extract_description('<meta name="description" content="Subscribe to continue reading all our latest news and analysis.">'))
        self.assertIsNone(u.extract_description('<script type="application/ld+json">{"@type":"Organization","description":"This publisher brings you all the latest news from around the world."}</script>'))

    def test_issue_is_a_question_and_unknown_topics_are_not_invented(self):
        self.assertTrue(u.derive_issue('ビーチ6000億円開発計画').endswith('？'))
        self.assertIsNone(u.derive_issue('New award for local artist'))
        self.assertIsNone(u.derive_viewpoint('新しい詩集を発表'))
        self.assertIn('規模',u.derive_viewpoint('ビーチ6000億円開発計画'))

    def test_summary_length_and_multibyte_translation_limit(self):
        self.assertLessEqual(len(u.shorten('説明文です。'*100,100)),101)
        self.assertLessEqual(len(u._utf8_limit('説明文です。'*100).encode('utf-8')),453)

    def test_asahi_accepts_non_padded_date_and_rejects_wrong_date(self):
        source=next(s for s in u.SOURCES if s['id']=='asahi-paper')
        raw='<title>2026年9月20日朝刊記事一覧</title><div id="shimen-page1"><li class="HeadlineTop"><a href="/articles/a.html">これは確認用の一面記事です</a></li></div>'
        _,articles=u.parse(source,raw,'2026-09-20')
        self.assertEqual(articles[0]['verification'],'paper-listed')
        with self.assertRaises(u.SourceError) as cm:
            u.parse(source,raw,'2026-09-21')
        self.assertEqual(cm.exception.code,'date-unverified')

    def test_asahi_web_uses_lead_story_not_breaking_news(self):
        source=next(s for s in u.SOURCES if s['id']=='asahi-web')
        raw='<a href="/articles/latest.html">これは速報の記事です</a><div class="p-topNews__firstNews"><a class="c-articleModule__link" data-realizer-area="TopNews:1" href="/articles/lead.html"><span>こちらがトップに配置された記事です</span></a></div>'
        _,articles=u.parse(source,raw,'2026-09-23')
        self.assertEqual(articles[0]['url'],'https://www.asahi.com/articles/lead.html')
        self.assertEqual(articles[0]['verification'],'web-top')
        self.assertEqual(articles[0]['positionEvidence']['type'],'web-top')

    def test_asahi_rejects_missing_publication_date(self):
        source=next(s for s in u.SOURCES if s['id']=='asahi-paper')
        raw='<title>朝刊記事一覧</title><div id="shimen-page1"><li><a href="/articles/a.html">これは確認用の一面記事です</a></li></div>'
        with self.assertRaises(u.SourceError) as cm:
            u.parse(source,raw,'2026-09-23')
        self.assertEqual(cm.exception.code,'date-unverified')

    def test_month_rollover_preserves_prior_snapshots(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            for day,time in [('2026-09-30','08:00'),('2026-09-30','17:00'),('2026-10-01','08:00')]:
                u.archive(root,dict(date=day,fetchedAt=f'{day}T{time}:00+09:00',sources=[]))
            self.assertEqual(len(u.read_json(root/'newspapers/2026-09/2026-09-30.json',{})['snapshots']),2)
            self.assertTrue((root/'newspapers/2026-10/2026-10-01.json').exists())
            self.assertEqual(u.read_json(root/'newspaper-index.json',{})['days'],['2026-10-01','2026-09-30'])

    def test_translation_errors_not_presented_as_japanese(self):
        with patch.object(u,'fetch',return_value='{"responseStatus":429,"responseData":{"translatedText":"quota exceeded"}}'):
            with self.assertRaises(ValueError):u.translate('Example headline',{},'en')

    def test_reject_stale_guardian_paper(self):
        s=next(s for s in u.SOURCES if s['id']=='guardian-paper')
        raw='<section id="front-page"><div class="fc-container__header__description">Friday 18 September 2026</div><h3><a href="https://www.theguardian.com/test">Example headline for paper</a></h3></section>'
        with self.assertRaises(u.SourceError) as cm:
            u.parse(s,raw,'2026-09-22')
        self.assertEqual(cm.exception.code,'date-unverified')

    def test_overseas_catalog_covers_requested_regions(self):
        regions={s['region'] for s in u.SOURCES}
        self.assertTrue({'日本','アフリカ','中東','ヨーロッパ','アメリカ','アジア（その他）','韓国','中国'} <= regions)
        countries={s['country'] for s in u.SOURCES}
        self.assertTrue({'タイ','マレーシア','韓国','中国'} <= countries)

    def test_feed_dates_dedup_and_description(self):
        src={'id':'feed','max_articles':3}
        raw='<rss><channel><item><title>Old headline is not current news</title><link>https://news.test/old</link><pubDate>Mon, 01 Jun 2026 10:00:00 +0000</pubDate></item><item><title>A current headline about regional policy</title><link>https://news.test/current</link><pubDate>Thu, 24 Sep 2026 10:00:00 +0000</pubDate><description>A brief publisher description covering the regional policy decision.</description></item><item><title>A current headline about regional policy</title><link>https://news.test/current</link><pubDate>Thu, 24 Sep 2026 10:00:00 +0000</pubDate></item></channel></rss>'
        _,rows=u.parse_feed(src,raw,'2026-09-25')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['publicationDate'],'2026-09-24')
        self.assertEqual(rows[0]['verification'],'feed-featured')
        self.assertIn('publisher',rows[0]['feedDescription'])
        with self.assertRaises(u.SourceError):u.parse_feed(src,raw,'2026-10-01')

    def test_unconfigured_web_source_is_not_promoted_to_top(self):
        s=next(s for s in u.SOURCES if s['id']=='nyt-web')
        raw='<main><article><h2><a href="https://www.nytimes.com/world/test.html">A sufficiently long example headline</a></h2></article></main>'
        with self.assertRaises(u.SourceError):u.parse(s,raw,'2026-10-08')

    def test_missing_lead_never_falls_back_to_regular_headings(self):
        s=next(s for s in u.SOURCES if s['id']=='asahi-web')
        with self.assertRaises(u.SourceError):
            u.parse(s,'<main><h2><a href="/articles/recipe">普通の見出しで一面ではありません</a></h2></main>','2026-10-08')

    def test_mainichi_rejects_other_pages_even_when_container_spans_sections(self):
        s=next(s for s in u.SOURCES if s['id']=='mainichi-paper')
        raw='<select name="soat"><option selected>2026/10/08</option></select><main><div><h2>1面</h2></div><article><h3><a href="/articles/20261008/ddm/001/010/001000c">こちらは一面の掲載記事です</a></h3></article><h2>料理</h2><article><h3><a href="/articles/20261008/ddm/013/010/002000c">こちらは生活面の料理記事です</a></h3></article></main>'
        _,rows=u.parse(s,raw,'2026-10-08')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['positionEvidence']['type'],'paper-front-page')
        self.assertIn('/ddm/001/',rows[0]['url'])

if __name__=='__main__':unittest.main()


