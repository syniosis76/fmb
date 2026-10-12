import os
import shutil
import subprocess
import sys

from kivy.logger import Logger

import ffpyplayer  # noqa: F401  # adds the bundled ffmpeg/ffprobe binaries to PATH

# If the nearest keyframe is further than this before the requested start, a
# stream copy would include too much extra footage, so re-encode instead.
COPY_START_TOLERANCE = 1.0

_ffmpeg_path = None
_ffprobe_path = None
_nvenc = None


def _find_binary(name):
    path = shutil.which(name)
    if path:
        return path

    base = os.path.join(sys.prefix, 'share', 'ffpyplayer', 'ffmpeg', 'bin')
    for candidate in (os.path.join(base, name), os.path.join(base, name + '.exe')):
        if os.path.exists(candidate):
            return candidate

    return name


def ffmpeg_binary():
    global _ffmpeg_path
    if _ffmpeg_path is None:
        _ffmpeg_path = _find_binary('ffmpeg')
    return _ffmpeg_path


def ffprobe_binary():
    global _ffprobe_path
    if _ffprobe_path is None:
        _ffprobe_path = _find_binary('ffprobe')
    return _ffprobe_path


def _run(args):
    Logger.debug('ffmpeg_tools: ' + ' '.join(args))
    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', 'replace')
        Logger.error(f'ffmpeg_tools: command failed ({result.returncode}):\n{stderr}')
        return False
    return True


def duration(path):
    if not path or not os.path.exists(path):
        return 0.0

    result = subprocess.run(
        [ffprobe_binary(), '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=nw=1:nk=1', path],
        capture_output=True, text=True)

    try:
        return float(result.stdout.strip())
    except (TypeError, ValueError):
        return 0.0


def keyframe_before(path, start_seconds):
    """Timestamp of the last video keyframe at or before start_seconds."""
    result = subprocess.run(
        [ffprobe_binary(), '-v', 'error', '-select_streams', 'v:0', '-skip_frame', 'nokey',
         '-show_entries', 'frame=pts_time', '-of', 'csv=p=0', path],
        capture_output=True, text=True)

    keyframe = 0.0
    for line in result.stdout.splitlines():
        try:
            pts = float(line.strip())
        except ValueError:
            continue
        if pts <= start_seconds + 0.001:
            keyframe = pts
        else:
            break

    return keyframe


def has_nvenc():
    global _nvenc
    if _nvenc is None:
        result = subprocess.run([ffmpeg_binary(), '-hide_banner', '-encoders'],
                                capture_output=True, text=True)
        _nvenc = 'h264_nvenc' in result.stdout
        Logger.debug(f'ffmpeg_tools: nvenc available = {_nvenc}')
    return _nvenc


def _output_format(target):
    # Proxies (.lrf / .lrv) are MP4 based but ffmpeg does not know the extension.
    if os.path.splitext(target)[1].lower() in ('.lrf', '.lrv'):
        return ['-f', 'mp4']
    return []


def trim(source, target, start_seconds, end_seconds):
    start_seconds = max(start_seconds, 0.0)
    end_seconds = max(end_seconds, start_seconds + 0.1)

    lead_in = start_seconds - keyframe_before(source, start_seconds)

    if lead_in > COPY_START_TOLERANCE:
        Logger.info(f'ffmpeg_tools: re-encoding trim (nearest keyframe is {lead_in:.2f}s before start)')
        return _trim_encode(source, target, start_seconds, end_seconds - start_seconds)

    Logger.info(f'ffmpeg_tools: stream copy trim (keyframe is {lead_in:.2f}s before start)')
    return _trim_copy(source, target, start_seconds, end_seconds)


def _trim_copy(source, target, start_seconds, end_seconds):
    return _run([
        ffmpeg_binary(), '-y', '-hide_banner',
        '-ss', f'{start_seconds:.3f}', '-to', f'{end_seconds:.3f}', '-i', source,
        '-c', 'copy', '-avoid_negative_ts', 'make_zero',
    ] + _output_format(target) + [target])


def _trim_encode(source, target, start_seconds, duration_seconds):
    if has_nvenc():
        video_args = ['-c:v', 'h264_nvenc', '-cq', '23']
    else:
        video_args = ['-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast']

    return _run([
        ffmpeg_binary(), '-y', '-hide_banner',
        '-ss', f'{start_seconds:.3f}', '-i', source,
        '-t', f'{duration_seconds:.3f}',
    ] + video_args + ['-c:a', 'copy'] + _output_format(target) + [target])


def extract_frame(source_file, target_file, position_seconds):
    position_seconds = max(position_seconds, 0.0)
    seek_time = max(position_seconds - 0.5, 0.0)

    return _run([
        ffmpeg_binary(), '-y', '-hide_banner',
        '-copyts', '-ss', f'{seek_time:.3f}', '-i', source_file,
        '-vf', f"select='gte(t,{position_seconds:.3f})'",
        '-frames:v', '1', '-q:v', '2', target_file])
