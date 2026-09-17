from app.store import format_duration


def test_list_episodes_is_paginated_newest_first(client):
    body = client.get("/episodes", params={"page": 2, "page_size": 5}).json()
    assert body["total"] == 15
    assert [e["id"] for e in body["items"]] == [
        "1000788665542",
        "1000788290606",
        "1000787894585",
        "1000787401197",
        "1000786537699",
    ]


def test_filters_combine(client):
    body = client.get("/episodes", params={"genre": "music", "max_minutes": 24}).json()
    assert [e["id"] for e in body["items"]] == ["1000784371953", "1000780103162", "1000777886394"]


def test_invalid_page_size_is_rejected(client):
    assert client.get("/episodes", params={"page_size": 500}).status_code == 422


def test_get_episode(client):
    episode = client.get("/episodes/1000788665542").json()
    assert episode["title"] == "1037: WebMCP is here (and you should care)"
    assert episode["duration_minutes"] == 56
    assert episode["url"].startswith("https://podcasts.apple.com/")


def test_unknown_episode_returns_404(client):
    assert client.get("/episodes/123").status_code == 404


def test_similar_episodes_come_from_other_podcasts(client):
    # The WebMCP episode is 56 minutes; the nearest durations are the 52-minute Rick Steves episodes
    episodes = client.get("/episodes/1000788665542/similar", params={"limit": 4}).json()
    assert {e["podcast_id"] for e in episodes} == {"travel-with-rick-steves"}
    assert "1000783349562" in [e["id"] for e in episodes]


def test_search_ranks_title_matches_first(client):
    # "web" is in one episode title and in the Syntax publisher name
    results = client.get("/search", params={"q": "web"}).json()
    assert results[0]["title"] == "1037: WebMCP is here (and you should care)"
    assert len(results) == 5


def test_search_is_case_insensitive(client):
    titles = [e["title"] for e in client.get("/search", params={"q": "AMERICA"}).json()]
    assert titles == [
        "838 Music Lover's Guide to North America; Loving the Opera",
        "837 America Obscura; This Land Is Your Land",
        "Mitski - Your Best American Girl",
    ]


def test_search_query_too_short(client):
    assert client.get("/search", params={"q": "a"}).status_code == 422


def test_stats_per_genre(client):
    body = client.get("/stats").json()
    assert body["total_episodes"] == 15
    assert body["total_readable"] == "11h 16m"
    assert body["genres"][1] == {
        "genre": "technology",
        "podcasts": 1,
        "episodes": 5,
        "total_minutes": 301,
        "total_readable": "5h 1m",
        "average_minutes": 60.2,
    }


def test_format_duration():
    assert format_duration(45) == "45m"
    assert format_duration(60) == "1h 0m"
    assert format_duration(131) == "2h 11m"
