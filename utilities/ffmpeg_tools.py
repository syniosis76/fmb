import ffpyplayer # Sets path for ffpyplayer ffmpeg binaries
import ffmpeg
import os
import datetime

def trim(source_file, target_file, start_seconds, end_seconds):
    start_time = str(datetime.timedelta(seconds=start_seconds))
    end_time = str(datetime.timedelta(seconds=end_seconds))

    ffmpeg.input(source_file, ss=(start_time), to=(end_time)).output(target_file, **{'c:v': 'copy'}, **{'c:a': 'copy'}).run()

#trim('source.mp4', 'target.mp4', 20, 50)

#C:\Tools\Python310\share\ffpyplayer\ffmpeg\bin\ffmpeg -i source.mp4 -ss 00:00:10 -to 00:00:20 -c:v copy -c:a copy target.mp4