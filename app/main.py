from fastapi import FastAPI, HTTPException, Query

from app.models import Episode, EpisodePage, Podcast, Stats
from app.store import get_catalogue

app = FastAPI(
    title="Podcast API",
    description="Browse and search a snapshot of real podcast episodes, with links to Apple Podcasts.",
    version="1.0.0",
)


def find_podcast(podcast_id: str) -> Podcast:
    podcast = get_catalogue().podcasts.get(podcast_id)
    if podcast is None:
        raise HTTPException(status_code=404, detail=f"Podcast '{podcast_id}' not found")
    return podcast


def find_episode(episode_id: str) -> Episode:
    episode = get_catalogue().episodes.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail=f"Episode '{episode_id}' not found")
    return episode


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/podcasts", response_model=list[Podcast])
def list_podcasts(genre: str | None = None) -> list[Podcast]:
    podcasts = get_catalogue().podcasts.values()
    return [p for p in podcasts if genre is None or p.genre == genre.lower()]


@app.get("/podcasts/{podcast_id}", response_model=Podcast)
def read_podcast(podcast_id: str) -> Podcast:
    return find_podcast(podcast_id)


@app.get("/podcasts/{podcast_id}/episodes", response_model=list[Episode])
def read_podcast_episodes(podcast_id: str) -> list[Episode]:
    find_podcast(podcast_id)
    return get_catalogue().filter_episodes(podcast_id=podcast_id)


@app.get("/episodes", response_model=EpisodePage)
def list_episodes(
    podcast_id: str | None = None,
    genre: str | None = None,
    max_minutes: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> EpisodePage:
    episodes = get_catalogue().filter_episodes(podcast_id, genre, max_minutes)
    start = (page - 1) * page_size
    return EpisodePage(items=episodes[start : start + page_size], total=len(episodes), page=page, page_size=page_size)


@app.get("/episodes/{episode_id}", response_model=Episode)
def read_episode(episode_id: str) -> Episode:
    return find_episode(episode_id)


@app.get("/episodes/{episode_id}/similar", response_model=list[Episode])
def read_similar(episode_id: str, limit: int = Query(default=3, ge=1, le=10)) -> list[Episode]:
    return get_catalogue().similar(find_episode(episode_id), limit)


@app.get("/search", response_model=list[Episode])
def search(q: str = Query(min_length=2)) -> list[Episode]:
    return get_catalogue().search(q)


@app.get("/stats", response_model=Stats)
def stats() -> Stats:
    return get_catalogue().stats()
