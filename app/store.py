import json
import os
from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.models import Episode, GenreStats, Podcast, Stats

DEFAULT_DATA_DIR = Path(__file__).parent / "data"


class Catalogue:
    """Podcast and episode snapshot loaded from JSON files."""

    def __init__(self, data_dir: Path) -> None:
        podcasts_file = json.loads((data_dir / "podcasts.json").read_text())
        episodes_file = json.loads((data_dir / "episodes.json").read_text())
        self.source: str = podcasts_file["source"]
        self.fetched_at = date.fromisoformat(podcasts_file["fetched_at"])
        self.podcasts = {p["id"]: Podcast(**p) for p in podcasts_file["podcasts"]}
        self.episodes = {e["id"]: Episode(**e) for e in episodes_file["episodes"]}

    def newest_first(self, episodes: list[Episode]) -> list[Episode]:
        return sorted(episodes, key=lambda e: (e.release_date, e.id), reverse=True)

    def filter_episodes(
        self, podcast_id: str | None = None, genre: str | None = None, max_minutes: int | None = None
    ) -> list[Episode]:
        return self.newest_first(
            [
                e
                for e in self.episodes.values()
                if (podcast_id is None or e.podcast_id == podcast_id)
                and (genre is None or self.podcasts[e.podcast_id].genre == genre.lower())
                and (max_minutes is None or e.duration_minutes <= max_minutes)
            ]
        )

    def search(self, query: str) -> list[Episode]:
        """Case-insensitive search: episode title matches rank above podcast name or publisher matches."""
        q = query.lower()
        ranked = []
        for e in self.episodes.values():
            podcast = self.podcasts[e.podcast_id]
            if q in e.title.lower():
                ranked.append((0, e))
            elif q in podcast.name.lower() or q in podcast.publisher.lower():
                ranked.append((1, e))
        ranked.sort(key=lambda item: (item[0], -item[1].release_date.toordinal(), item[1].id))
        return [e for _, e in ranked]

    def similar(self, episode: Episode, limit: int = 3) -> list[Episode]:
        """Episodes from other podcasts with the closest duration."""
        candidate_ids = {e.id for e in self.episodes.values() if e.podcast_id != episode.podcast_id}
        candidates = [self.episodes[candidate_id] for candidate_id in candidate_ids]
        candidates.sort(key=lambda e: abs(e.duration_minutes - episode.duration_minutes))
        return candidates[:limit]

    def stats(self) -> Stats:
        by_genre: dict[str, list[Episode]] = defaultdict(list)
        for e in self.episodes.values():
            by_genre[self.podcasts[e.podcast_id].genre].append(e)

        genres = []
        for genre, episodes in sorted(by_genre.items()):
            minutes = sum(e.duration_minutes for e in episodes)
            genres.append(
                GenreStats(
                    genre=genre,
                    podcasts=len({e.podcast_id for e in episodes}),
                    episodes=len(episodes),
                    total_minutes=minutes,
                    total_readable=format_duration(minutes),
                    average_minutes=round(minutes / len(episodes), 1),
                )
            )

        total = sum(e.duration_minutes for e in self.episodes.values())
        return Stats(
            source=self.source,
            fetched_at=self.fetched_at,
            total_episodes=len(self.episodes),
            total_readable=format_duration(total),
            genres=genres,
        )


def format_duration(minutes: int) -> str:
    """Format minutes as '45m' or '1h 5m'."""
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if hours else f"{mins}m"


@lru_cache
def get_catalogue() -> Catalogue:
    return Catalogue(Path(os.environ.get("PODCAST_DATA_DIR", DEFAULT_DATA_DIR)))
