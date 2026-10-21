"""Free, local VOICEVOX Nemo narration; never sends article text to a paid API."""
import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
import wave
import zlib
from pathlib import Path

ENGINE_VERSION = '0.24.0'
SPEAKER = 10005  # VOICEVOX Nemo 女声1 / ノーマル
SAMPLE_RATE = 24000
SETTINGS = dict(speedScale=1.0, intonationScale=1.0, pitchScale=0.0,
                prePhonemeLength=0.08, postPhonemeLength=0.32,
                outputSamplingRate=SAMPLE_RATE, outputStereo=False)
VOICE = 'voicevox-nemo-' + ENGINE_VERSION + '-10005-v1'
CREDIT = 'VOICEVOX Nemo（女声1）'
BASE_URL = 'http://127.0.0.1:50121'


def pronunciation(text):
    # Only change the speech input. Captions and source wording remain intact.
    text = re.sub(r'アニモ\s*[（(]Aniimo[）)]', 'アニモ', text, flags=re.I)
    names = {'FINAL FANTASY XVI':'ファイナルファンタジー シックスティーン',
             'ELDEN RING':'エルデンリング', 'Rise of the Ronin':'ライズ オブ ザ ローニン',
             'Aniimo':'アニモ', 'Twining':'ツイニング',
             'PS5':'ピーエスファイブ', 'PS4':'ピーエスフォー',
             'Xbox Series X|S':'エックスボックス シリーズ エックス エス',
             'Xbox':'エックスボックス', 'NPC':'エヌピーシー', 'DLC':'ディーエルシー',
             'FPS':'エフピーエス', 'PC':'ピーシー', 'UI':'ユーアイ',
             'PvP':'ピーブイピー', 'PvE':'ピーブイイー'}
    for name, reading in names.items():
        text = re.sub(r'(?<![A-Za-z])'+re.escape(name)+r'(?![A-Za-z])', reading, text, flags=re.I)
    text = text.replace('→', '、その後、').replace('／', '、')
    return re.sub(r'\s+', ' ', text).strip()


def chunks(text, limit=180):
    """Bound synthesis memory, preferring sentence/phrase boundaries over hard cuts."""
    while len(text) > limit:
        candidates = [text.rfind(c, 0, limit) for c in '。！？、；']
        end = max(candidates)
        cut = end + 1 if end >= limit // 3 else limit
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


def request(path, data=None):
    payload = json.dumps(data).encode() if data is not None else b''
    req = urllib.request.Request(BASE_URL + path, data=payload,
                                 headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=180) as response:
        return response.read()


def wav_pcm(data):
    with wave.open(io.BytesIO(data), 'rb') as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype()) != (1, 2, SAMPLE_RATE, 'NONE'):
            raise ValueError('Unexpected Nemo WAV format')
        raw = w.readframes(w.getnframes())
        if not raw or len(raw) != w.getnframes() * 2:
            raise ValueError('Empty or truncated Nemo audio')
        return raw


def cache_key(text):
    return hashlib.sha256((VOICE + json.dumps(SETTINGS,sort_keys=True) + pronunciation(text)).encode()).hexdigest()


def shard_for(text):
    return int(cache_key(text)[:8], 16) % 8


def pcm(text, cache):
    cache = Path(cache) / ('shard-' + str(shard_for(text)))
    cache.mkdir(parents=True, exist_ok=True)
    speech = pronunciation(text)
    key = cache_key(text)
    path = cache / (key + '.pcm.z')
    if path.exists():
        try:
            raw = zlib.decompress(path.read_bytes())
            if raw and len(raw) % 2 == 0:
                return raw
        except zlib.error:
            pass
    parts = []
    for part in chunks(speech):
        query = json.loads(request('/audio_query?' + urllib.parse.urlencode({'speaker':SPEAKER,'text':part})))
        query.update(SETTINGS)
        parts.append(wav_pcm(request('/synthesis?speaker=' + str(SPEAKER), query)))
    raw = b''.join(parts)
    if not raw:
        raise ValueError('No speech to synthesize')
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(zlib.compress(raw, 3))
    tmp.replace(path)
    return raw
