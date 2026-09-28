import unittest
from unittest.mock import patch
import daily_briefs as b
from update_daily import parse_feed

class FeedTests(unittest.TestCase):
    def test_valid_feed_deduplicates_and_ignores_empty_titles(self):
        raw = '<rss><channel>' + ''.join('<item><title>'+t+'</title></item>' for t in ['A','B','C','D','E','A','']) + '</channel></rss>'
        self.assertEqual(parse_feed(raw), ['A','B','C','D','E'])
    def test_incomplete_feed_cannot_overwrite_good_data(self):
        with self.assertRaises(ValueError):
            parse_feed('<rss><channel><item><title>A</title></item></channel></rss>')
    def test_error_page_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_feed('<html><body>Service unavailable</body></html>')

class BriefTests(unittest.TestCase):
    def test_missing_or_unrelated_reporting_is_not_invented(self):
        with patch.object(b,'search_articles',return_value=[]):
            self.assertEqual(b.make_brief('青柳晃洋',[dict(title='無関係の記事',url='https://example.com',source='報道',snippet='')])['status'],'unavailable')
    def test_japanese_summary_and_source_are_retained(self):
        row=dict(title='青柳晃洋が来季戦力構想外',url='https://example.com/article',source='報道',snippet='')
        with patch.object(b,'fetch',return_value='<meta name="description" content="青柳晃洋について来季の所属が変わる見通しを伝え、チームの発表を紹介しています。">'):
            out=b.make_brief('青柳晃洋',[row])
        self.assertEqual(out['summaryBasis'],'publisher-description')
        self.assertIn('所属',out['issue'])
        self.assertEqual(out['sources'][0]['url'],row['url'])
    def test_failed_description_uses_labelled_headline(self):
        row=dict(title='福本莉子が映画で主演',url='https://example.com/a',source='報道',snippet='')
        with patch.object(b,'fetch',side_effect=TimeoutError):out=b.make_brief('福本莉子',[row])
        self.assertEqual(out['summaryBasis'],'related-headline')
        self.assertEqual(out['summary'],row['title'])
    def test_incomplete_sentences_and_unsafe_sources(self):
        self.assertEqual(b.short('最初の文です。続きは途中…'),'最初の文です。')
        self.assertEqual(b.short('途中で終わる…'),'')
        self.assertFalse(b.safe_url('javascript:alert(1)'))
        self.assertFalse(b.safe_url('http://example.com'))
    def test_no_political_or_popularity_claim(self):
        question,reason=b.issue_for('日本バレーボール協会','日本バレーボール協会がSNS中傷に声明')
        self.assertIn('被害',question)
        self.assertNotIn('本人の公表',question)

if __name__ == '__main__':
    unittest.main()

