import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import update_newspapers as u

class NewspaperTests(unittest.TestCase):
    def test_reject_wrong_date_and_no_top_inference(self):
        source=u.SOURCES[0]
        raw='<title>2026年09月20日朝刊記事一覧</title><div id="shimen-page1"><li class="HeadlineTop"><a href="/articles/a.html">これは確認用の一面記事です</a></li></div>'
        _,articles=u.parse(source,raw,'2026-09-20')
        self.assertEqual(articles[0]['verification'],'paper-listed')
        with self.assertRaises(ValueError):u.parse(source,raw,'2026-09-21')
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
            with self.assertRaises(ValueError):u.translate('Example headline',{})
    def test_reject_stale_paper(self):
        s=u.SOURCES[1]
        raw='<section id="front-page"><div class="fc-container__header__description">Friday 18 September 2026</div><h3><a href="https://www.theguardian.com/test">Example headline</a></h3></section>'
        with self.assertRaises(ValueError):u.parse(s,raw,'2026-09-22')

if __name__=='__main__':unittest.main()
