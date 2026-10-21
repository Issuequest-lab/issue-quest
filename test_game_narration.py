import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import game_narration as n


def wav(rate=24000,frames=2400):
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(b'\0\0'*frames)
    return b.getvalue()

class NarrationTests(unittest.TestCase):
    def test_pronunciation_keeps_meaning(self):
        self.assertEqual(n.pronunciation('アニモ（Aniimo）。PS5とPC。NPCのUI。'), 'アニモ。ピーエスファイブとピーシー。エヌピーシーのユーアイ。')
        self.assertEqual(n.pronunciation('スペルSPECIAL'), 'スペルSPECIAL')
    def test_long_text_not_lost(self):
        s=('長い文章を読みます。さらに説明します。'*40)
        parts=list(n.chunks(s))
        self.assertEqual(''.join(parts),s)
        self.assertLessEqual(max(map(len,parts)),180)
    def test_wav_timing_and_wrong_rate(self):
        self.assertEqual(len(n.wav_pcm(wav()))/(n.SAMPLE_RATE*2),.1)
        with self.assertRaises(ValueError):n.wav_pcm(wav(rate=48000))
        with self.assertRaises(ValueError):n.wav_pcm(wav(frames=0))
    def test_cache_and_failed_request(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(n,'request',side_effect=[b'{}',wav()]) as request:
                a=n.pcm('音声。',d)
                self.assertEqual(n.pcm('音声。',d),a)
                self.assertEqual(request.call_count,2)
            with patch.object(n,'request',side_effect=OSError('offline')):
                with self.assertRaises(OSError):n.pcm('別の音声。',d)
            self.assertEqual(len(list(Path(d).glob('*.pcm.z'))),1)

if __name__=='__main__':unittest.main()
