"""Generate continuous MP3s locally (no paid service) with sentence timing metadata."""
import hashlib, json, os, subprocess, tempfile
from pathlib import Path
from game_narration import pcm as synthesize, VOICE, CREDIT, SAMPLE_RATE

ROOT=Path(__file__).resolve().parent
CACHE=Path(os.environ.get('GAME_TTS_CACHE', ROOT/'.game-tts-cache'))
MEDIA=ROOT/'game-audio-media'


def digest(value):
 return hashlib.sha256(value.encode()).hexdigest()[:24]

def pcm(text):
 return synthesize(text, CACHE)

def get_tracks():
 script="const {build,hash}=require('./game-audio-files.js');const d=require('./game-updates-latest.json');const out=[];for(const p of ['PS5','PC','all','unknown'])for(const g of d.games){const chapters=build([g],p);if(chapters.length)out.push({gameId:g.id,name:g.name,platform:p,signature:hash(JSON.stringify(chapters)),chapters});}console.log(JSON.stringify(out));"
 return json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT))

def main():
 tracks=get_tracks()
 manifest_path=ROOT/'game-audio-manifest.json'
 old=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'tracks':[]}
 MEDIA.mkdir(exist_ok=True)
 results=[]
 for track in tracks:
  key=digest(VOICE+'|'+track['platform']+'|'+track['signature'])
  found=next((t for t in old['tracks'] if t.get('key')==key and (ROOT/t['src']).exists()),None)
  if found:results.append(found);continue
  path=MEDIA/(key+'.mp3');tmp=MEDIA/(key+'.tmp.mp3')
  print('Generating',track['platform'],track['name'],flush=True)
  encoder=subprocess.Popen(['ffmpeg','-v','error','-y','-f','s16le','-ar',str(SAMPLE_RATE),'-ac','1','-i','pipe:0','-ar','24000','-ac','1','-codec:a','libmp3lame','-b:a','48k',str(tmp)],stdin=subprocess.PIPE)
  elapsed=0;timed=[]
  try:
   for chapter in track['chapters']:
    c={**chapter,'start':elapsed,'lines':[]}
    for text in chapter['lines']:
     raw=pcm(text);end=elapsed+len(raw)/(SAMPLE_RATE*2)
     encoder.stdin.write(raw)
     c['lines'].append({'text':text,'start':round(elapsed,4),'end':round(end,4)})
     elapsed=end
    c['end']=round(elapsed,4);timed.append(c)
   encoder.stdin.close()
   if encoder.wait()!=0:raise RuntimeError('MP3 encoding failed')
   if tmp.stat().st_size>95_000_000:raise ValueError('Audio exceeds repository file size budget')
   tmp.replace(path)
  except BaseException:
   encoder.kill();encoder.wait();tmp.unlink(missing_ok=True);raise
  results.append({**track,'key':key,'chapters':timed,'src':str(path.relative_to(ROOT)),'duration':round(elapsed,4),'credit':CREDIT,'voice':VOICE})
  print('Ready',round(elapsed/60,1),'minutes',flush=True)
 data=json.loads((ROOT/'game-updates-latest.json').read_text())
 result={'schemaVersion':1,'dataCheckedAt':data['checkedAt'],'credit':CREDIT,'voice':VOICE,'tracks':results}
 tmp=manifest_path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')));tmp.replace(manifest_path)
 # Keep media referenced by the previous manifest too, so already-open players keep working.
 keep={t['src'] for t in results+old['tracks']}
 for path in MEDIA.glob('*.mp3'):
  if str(path.relative_to(ROOT)) not in keep:path.unlink()
 print('Audio manifest ready:',len(results),'tracks',flush=True)
if __name__=='__main__':main()

