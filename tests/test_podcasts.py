def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_podcasts(client):
    podcasts = client.get("/podcasts").json()
    assert [p["id"] for p in podcasts] == ["syntax", "song-exploder", "travel-with-rick-steves"]


def test_podcasts_filter_by_genre(client):
    podcasts = client.get("/podcasts", params={"genre": "TRAVEL"}).json()
    assert [p["id"] for p in podcasts] == ["travel-with-rick-steves"]


def test_podcast_has_apple_podcasts_url(client):
    podcast = client.get("/podcasts/syntax").json()
    assert podcast["url"] == "https://podcasts.apple.com/us/podcast/syntax-tasty-web-development-treats/id1253186678"


def test_unknown_podcast_returns_404(client):
    assert client.get("/podcasts/not-a-podcast").status_code == 404


def test_podcast_episodes_newest_first(client):
    episodes = client.get("/podcasts/syntax/episodes").json()
    assert len(episodes) == 5
    assert episodes[0]["title"] == "1039: Should You Quit Your Job?"
    assert episodes[-1]["title"] == "1035: Why everyone is moving to Stylex?"


def test_episodes_for_unknown_podcast_returns_404(client):
    assert client.get("/podcasts/not-a-podcast/episodes").status_code == 404
