from pathlib import Path
import opentimelineio as otio

from typing import Union


def get_timeline(otio_file: Union[str, Path]) -> otio.schema.Timeline:
    if not isinstance(otio_file, Path):
        otio_file = Path(otio_file)
    if not otio_file.exists():
        raise FileNotFoundError(f"File not found: {otio_file}")
    return otio.adapters.read_from_file(f"{otio_file}")

def get_segment_speeds(keyframes: list[list[float]]) -> list[float]:
    """ Returns a list of speed ratios between keyframes in percentage """
    result = []
    for i, kf in enumerate(keyframes):
        next_kf = keyframes[i+1] if i+1 < len(keyframes) else None
        if not next_kf:
            break

        #? shall we convert to frames here to keep calculations coherent
        # general formula to calculate speed ratio between two keyframes 
        speed_ratio = (next_kf[1] - kf[1]) / (next_kf[0] - kf[0])
        result.append(speed_ratio)
    return result

def handle_keyframed_timewarp(clip, effect: otio.schema.Effect) -> otio.opentime.TimeRange:
    keyframes = effect.metadata["Resolve_OTIO"]["Key Frames"]   # keyframe timedata in seconds
    clip_fps: float = clip.source_range.start_time.rate

    # all these values are in frames
    f_clip_in: float = clip.source_range.start_time.value
    f_clip_duration: float = clip.source_range.duration.value
    f_src_in: float = clip.media_reference.available_range.start_time.value

    segment_speeds_fractions: list[float] = get_segment_speeds(keyframes)
    segment_speeds_percentage = [speed * 100 for speed in segment_speeds_fractions]

    #! first we need to lookup the speed change mapping to the source_media at clip start
    #! we define clip start helper keyframe as I
    if f_src_in != 0:   # calculate the clip_in if media source start timecode != 00:00:00:00
        f_clip_in = (f_clip_in - f_src_in) / clip_fps
    I0 = (f_clip_in / clip_fps) * segment_speeds_percentage[0]  #? why do i need to scale with percentage and not fraction
    I1 = keyframes[1][1] - ( segment_speeds_fractions[0] * (keyframes[1][0] - I0 ))

    #! now the same for source_media at clip end
    #! we define clip start helper keyframe as O (not 0)
    O0 = (I0 * clip_fps) + f_clip_duration
    O1 = ((((O0 / clip_fps) - keyframes[-2][0]) * clip_fps) * segment_speeds_fractions[-1]) + keyframes[-1][1]

    result_start = otio.opentime.RationalTime(I1 * clip_fps, clip_fps)
    result_duration = otio.opentime.RationalTime(O1 - I1, clip_fps)
    return otio.opentime.TimeRange(result_start, result_duration)

def get_timewarps(clip: otio.schema.Clip) -> dict[str, otio.schema.Effect]:
    #? is it even possible to have multiple timewarps in resolve or other NLEs
    result = {}
    for e in clip.effects:
        if e.schema_name() == "LinearTimeWarp":
            result.update({"linear": e})
        if e.schema_name() == "TimeEffect":
            result.update({"keyframed": e})
    return result

def get_clip_source_range(clip: otio.schema.Clip) -> otio.opentime.TimeRange:
    result: otio.opentime.TimeRange = clip.source_range
    duration: otio.opentime.RationalTime = clip.source_range.duration

    timewarps = get_timewarps(clip)
    if timewarps.get("linear"):
        #? could we use our calculations for keyframed timewarps here when it's stable
        scaled_duration = duration.value * timewarps["linear"].time_scalar
        duration = otio.opentime.RationalTime(scaled_duration, duration.rate)
        result = otio.opentime.TimeRange(
            clip.source_range.start_time,
            duration
        )
    if timewarps.get("keyframed"):
        result = handle_keyframed_timewarp(clip, timewarps["keyframed"])

    return result

def get_media_reference_usages(track: otio.schema.Track) -> int:
    raise NotImplementedError
    
    if not isinstance(track, otio.schema.TrackKind.Video):
        raise ValueError("Track is not a video track")
    for clip in track:
        pass
