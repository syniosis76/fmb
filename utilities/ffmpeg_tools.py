import ffpyplayer # Sets path for ffpyplayer ffmpeg binaries
import ffmpeg
import datetime

def trim(source_file, target_file, start_seconds, end_seconds):
    start_time = str(datetime.timedelta(seconds=start_seconds))
    end_time = str(datetime.timedelta(seconds=end_seconds))

    ffmpeg.input(source_file, ss=(start_time), to=(end_time), **{'noaccurate_seek': None}).output(target_file, **{'c:v': 'copy'}, **{'c:a': 'copy'}, **{'avoid_negative_ts': '1'}).run()    

#trim('source.mp4', 'target.mp4', 20, 50)

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