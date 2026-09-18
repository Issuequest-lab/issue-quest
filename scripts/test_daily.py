import unittest
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

if __name__ == '__main__':
    unittest.main()
