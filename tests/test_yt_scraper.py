import pytest
from yt_scraper import fetch_videos_from_channel, is_educational, get_transcript, calculate_engagement
from trusted_channels import trusted_channels

def test_fetch_videos_from_channel():
    channel_id = trusted_channels[0]  # Use the first channel in the list
    videos = fetch_videos_from_channel(channel_id, max_results=2)
    assert isinstance(videos, list)
    assert len(videos) > 0
    assert "video_id" in videos[0]
    assert "title" in videos[0]

def test_is_educational():
    assert is_educational("Python tutorial for beginners")
    assert not is_educational("Funny cat video")

def test_get_transcript():
    transcript = get_transcript("dQw4w9WgXcQ")  # Rickroll video ID (may not have a transcript)
    assert isinstance(transcript, str)

def test_calculate_engagement():
    score = calculate_engagement(1000, 50, 20)
    assert score > 0

if __name__ == "__main__":
    pytest.main()
