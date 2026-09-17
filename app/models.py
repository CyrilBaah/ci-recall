from datetime import date

from pydantic import BaseModel, Field


class Podcast(BaseModel):
    id: str
    name: str
    publisher: str
    genre: str
    url: str
    feed_url: str | None = None


class Episode(BaseModel):
    id: str
    podcast_id: str
    title: str
    duration_minutes: int = Field(gt=0)
    release_date: date
    url: str


class EpisodePage(BaseModel):
    items: list[Episode]
    total: int
    page: int
    page_size: int


class GenreStats(BaseModel):
    genre: str
    podcasts: int
    episodes: int
    total_minutes: int
    total_readable: str
    average_minutes: float


class Stats(BaseModel):
    source: str
    fetched_at: date
    total_episodes: int
    total_readable: str
    genres: list[GenreStats]
