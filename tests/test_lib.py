import yaml
import pytest
import opentimelineio as otio
import otio_tools.lib as lib
from pathlib import Path

test_otio_data = None
with Path("tests/expected_data.yaml").open("r") as config:
    test_otio_data = yaml.safe_load(config)


@pytest.mark.parametrize("test_otio", test_otio_data)
def test_get_timeline(test_otio: dict):
    timeline = lib.get_timeline(test_otio["file"])
    assert isinstance(timeline, otio.schema.Timeline)

@pytest.mark.parametrize("test_otio", test_otio_data)
def test_get_clip_source_range(test_otio: dict):
    timeline: otio.schema.Timeline = lib.get_timeline(test_otio["file"])
    
    ti = 0
    for track in timeline.video_tracks():
        if not track.enabled:
            continue
        test_track = test_otio["video_tracks"][ti]
        assert track.name == test_track["name"]

        ci = 0
        for clip in track:
            if isinstance(clip, otio.schema.Gap):
                continue
            test_clip = test_track["clips"][ci]
            assert clip.name == test_clip["name"]
            
            src_range = lib.get_clip_source_range(clip)
            assert round(src_range.start_time.value) == test_clip["src_in"]
            assert round(src_range.duration.value) == test_clip["duration"]
            assert src_range.start_time.rate == test_clip["fps"]

            ci = ci + 1
        ti = ti + 1
