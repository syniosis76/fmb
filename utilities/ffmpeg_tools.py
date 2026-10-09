import ffpyplayer # Sets path for ffpyplayer ffmpeg binaries
import ffmpeg
import datetime
from fractions import Fraction

def trim(source_file, target_file, start_seconds, end_seconds):
    start_time = str(datetime.timedelta(seconds=start_seconds))
    end_time = str(datetime.timedelta(seconds=end_seconds))

    ffmpeg.input(source_file, ss=(start_time), to=(end_time), **{'noaccurate_seek': None}).output(target_file, **{'c:v': 'copy'}, **{'c:a': 'copy'}, **{'avoid_negative_ts': '1'}).run()    

#trim('source.mp4', 'target.mp4', 20, 50)

def read_duration(path):
    probe = ffmpeg.probe(path)
    return float(probe['format']['duration'])

def read_avg_fps(path):
    probe = ffmpeg.probe(path)
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    return float(Fraction(stream['avg_frame_rate']))

def extract_frame(source_file, proxy_file, target_file, position_seconds):    
    proxy_duration = read_duration(proxy_file)
    original_duration = read_duration(source_file)
    time_ratio = original_duration / proxy_duration
    original_pts = position_seconds * time_ratio

    seek_time = max(original_pts - 0.5, 0)

    (
        ffmpeg               
        .input(source_file, ss=seek_time, copyts=None)
        .filter('select', f'gte(t,{original_pts})')
        .output(target_file, **{'frames:v': 1, 'q:v': 2})
        .run()
    )

#C:\Tools\Python310\share\ffpyplayer\ffmpeg\bin\ffmpeg -i source.mp4 -ss 00:00:10 -to 00:00:20 -c:v copy -c:a copy target.mp4

def generate_thumbnail(source_file, target_file, target_width, target_height):
    probe = ffmpeg.probe(source_file)
    duration = float(probe['streams'][0]['duration'])
    frame_seconds = 3
    if duration < 3:
        frame_seconds = duration / 2    
    
    start_time = str(datetime.timedelta(seconds=frame_seconds))    
    try:
        (
            ffmpeg
            .input(source_file, ss=start_time)
            .filter('scale', target_width, -1)
            .output(target_file, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr.decode())
        raise e

# Testing - Uncomment and Run this file directly
def test():
    source_file = 'D:\\Pictures\\2026-02-08 Wairoa Jules Katie Phil Nikora\\DJI_20260208114747_0013_D.MP4'
    proxy_file = 'D:\\Pictures\\2026-02-08 Wairoa Jules Katie Phil Nikora\\DJI_20260208114747_0013_D.LRF'
    target_file = 'D:\\Pictures\\2026-02-08 Wairoa Jules Katie Phil Nikora\\DJI_20260208114747_0013_D 4.jpg'
    position_seconds = 15.080354999983683
    extract_frame(source_file, proxy_file, target_file, position_seconds)

#test()