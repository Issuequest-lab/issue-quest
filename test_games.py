import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import update_games as g
NOW='2026-10-13T08:00:00+09:00'
GAME={'id':'test','name':'Test','parser':'elden','source':'https://www.eldenring.jp/news.html','releaseDate':'2022-02-25'}
HTML='''<article><p>対象プラットフォーム</p><p>PlayStation 5 / Steam</p><h2>修正</h2><ul><li>特定条件で進行不能になる不具合の修正</li></ul><p>App Ver. 1.20</p></article>'''
class Tests(unittest.TestCase):
 def test_platform_and_version(self):
  r=g.parse_detail(GAME,'https://www.eldenring.jp/test','更新','2026-10-12',HTML,NOW)
  self.assertEqual(r['platforms'],['PS5','PC']);self.assertEqual(r['version'],'1.20');self.assertEqual(r['changes'][0]['category'],'安定性')
 def test_invalid_and_future_dates(self):
  self.assertIsNone(g.parse_date('2026/02/30'))
  with self.assertRaises(ValueError):g.parse_detail(GAME,'https://a.jp','更新','2026-10-14',HTML,NOW)
 def test_unknown_platform_not_ps5(self):
  r=g.parse_detail(GAME,'https://a.jp','更新','2026-10-12',HTML.replace('PlayStation 5 / Steam','機種不明'),NOW);self.assertEqual(r['platforms'],[])
 def test_no_changes_rejected(self):
  with self.assertRaises(ValueError):g.parse_detail(GAME,'https://a.jp','更新','2026-10-12','<article>新作発売！</article>',NOW)
 def test_release_gate(self):
  self.assertIsNone(g.parse_detail(GAME,'https://a.jp','更新','2022-02-24',HTML,NOW))
 def test_discovery_ignores_general_news(self):
  html='<a href="/newsdetail/a.html">2026.10.12 アップデートのお知らせ</a><a href="/newsdetail/b.html">2026.10.12 新作発売</a><a href="https://other.jp/newsdetail/c.html">2026.10.12 アップデート</a>'
  self.assertEqual(len(g.discover(GAME,html)),1)
 def test_ff16_excludes_demo(self):
  ff={**GAME,'parser':'ff16'}
  rows=[{'label':'UPDATE','title':t,'date':'2026.10.12','link':{'mode':'link','url':'/news/test/'}} for t in ['体験版アップデート','PC版アップデート']]
  self.assertEqual(len(g.discover(ff,json.dumps(rows))),1)
 def test_ronin_unknown_not_assumed(self):
  game={**GAME,'parser':'ronin'}
  h='<section class="topics-section" id="ver1"><h5>Ver.1.09 <span>2025/03/11</span></h5><ul><li>進行不能になる不具合を修正</li></ul></section>'
  self.assertEqual(g.parse_ronin(game,h,NOW)[0]['platforms'],[])
 def test_failure_keeps_old(self):
  old={'updates':[{'id':'old','date':'2025-01-01','lastVerifiedAt':'2025-01-02'}]}
  with patch.object(g,'fetch',side_effect=OSError('offline')):result=g.collect(GAME,old,NOW)
  self.assertEqual(result['sourceStatus'],'failed');self.assertEqual(result['updates'],old['updates'])
 def test_month_rollover_multiple_snapshots(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for day,hour in [('2026-09-30','08'),('2026-10-01','08'),('2026-10-01','17')]:g.save(root,{'date':day,'checkedAt':day+'T'+hour+':00:00+09:00','games':[]})
   self.assertTrue((root/'game-updates/2026-09/2026-09-30.json').exists());self.assertEqual(len(json.loads((root/'game-updates/2026-10/2026-10-01.json').read_text())['snapshots']),2)
 def test_same_note_recheck_dedup(self):
  with patch.object(g,'fetch',side_effect=lambda url:'<a href="/newsdetail/a.html">2026.10.12 アップデート</a>' if url==GAME['source'] else HTML):
   a=g.collect(GAME,{},NOW);b=g.collect(GAME,a,'2026-10-13T17:00:00+09:00')
  self.assertEqual(len(b['updates']),1);self.assertEqual(b['updates'][0]['firstSeenAt'],NOW)
if __name__=='__main__':unittest.main()
