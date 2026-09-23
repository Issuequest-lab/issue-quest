import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import update_newspapers as u

class NewspaperTests(unittest.TestCase):
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

    def test_overseas_catalog_has_eight_outlets_and_regions(self):
        overseas={s['name'] for s in u.SOURCES if s['region']!='日本'}
        self.assertEqual(overseas,{
            'The Guardian','The New York Times','Financial Times','Reuters','Le Monde',
            'Al Jazeera','South China Morning Post','BBC News'
        })
        regions={s['region'] for s in u.SOURCES}
        self.assertTrue({'日本','米国','英国','欧州','アジア','中東・グローバルサウス','通信社'} <= regions)

    def test_web_parser_keeps_source_region_and_single_featured_story(self):
        s=next(s for s in u.SOURCES if s['id']=='nyt-web')
        raw='<main><article><h2><a href="https://www.nytimes.com/2026/09/23/world/test.html">A sufficiently long example headline for testing</a></h2></article></main>'
        _,articles=u.parse(s,raw,'2026-09-23')
        self.assertEqual(len(articles),1)
        self.assertEqual(articles[0]['verification'],'web-featured')

if __name__=='__main__':unittest.main()
