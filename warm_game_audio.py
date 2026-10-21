"""Synthesize one deterministic eighth of the paragraphs for parallel free CI jobs."""
import os
from build_game_audio_nemo import get_tracks, CACHE
from game_narration import pcm, shard_for

def main():
    shard=int(os.environ['GAME_AUDIO_WARM_SHARD'])
    if not 0 <= shard < 8: raise ValueError('Invalid audio shard')
    lines = dict.fromkeys(line for t in get_tracks() for c in t['chapters'] for line in c['lines'])
    lines = [line for line in lines if shard_for(line)==shard]
    for i,line in enumerate(lines,1):
        pcm(line,CACHE)
        if i%10==0 or i==len(lines):print(f'Shard {shard}: {i}/{len(lines)} paragraphs ready',flush=True)

if __name__=='__main__': main()
