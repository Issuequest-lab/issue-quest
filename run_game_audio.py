"""Download the pinned official free engine, start locally, build and shut it down."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from game_narration import BASE_URL, ENGINE_VERSION, SPEAKER

URL = ('https://github.com/VOICEVOX/voicevox_nemo_engine/releases/download/' + ENGINE_VERSION +
       '/voicevox_engine-linux-cpu-x64-' + ENGINE_VERSION + '.vvpp')
SHA256 = '8e8409d0b6cbd035ec9c5cc8f22e35563b2df8de7aba095859eb15cebf446ee3'
ROOT = Path(__file__).resolve().parent


def main():
    with tempfile.TemporaryDirectory(prefix='game-nemo-') as directory:
        directory = Path(directory)
        binary = os.environ.get('GAME_NEMO_BINARY')
        if not binary:
            archive = directory / 'engine.zip'
            urllib.request.urlretrieve(URL, archive)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
                raise ValueError('Nemo download checksum mismatch')
            engine = directory / 'engine'
            with zipfile.ZipFile(archive) as z:
                z.extractall(engine)
            binary = engine / 'run'
            binary.chmod(0o755)
        with open(directory / 'engine.log', 'w+') as log:
            process = subprocess.Popen([str(binary), '--host','127.0.0.1','--port','50121',
                                        '--cpu_num_threads','4','--disable_mutable_api'],
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(90):
                    if process.poll() is not None:
                        raise RuntimeError('Nemo stopped before readiness')
                    try:
                        with urllib.request.urlopen(BASE_URL + '/speakers',timeout=2) as r:
                            speakers = json.load(r)
                        if not any(s['id']==SPEAKER for v in speakers for s in v['styles']):
                            raise ValueError('Required Nemo voice is absent')
                        break
                    except OSError:
                        time.sleep(1)
                else:
                    raise TimeoutError('Nemo startup timed out')
                target = 'warm_game_audio.py' if 'GAME_AUDIO_WARM_SHARD' in os.environ else 'build_game_audio_nemo.py'
                subprocess.run([os.sys.executable, str(ROOT/target)],check=True,cwd=ROOT)
            except BaseException:
                log.flush(); log.seek(0)
                print(log.read()[-4000:],flush=True)
                raise
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait()

if __name__ == '__main__':
    main()
