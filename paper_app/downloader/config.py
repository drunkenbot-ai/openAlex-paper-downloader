"""Configuration for the OpenAlex paper downloader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SEARCH_TERMS: tuple[str, ...] = (
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "large language models",
    "natural language processing",
    "computer vision",
    "reinforcement learning",
    "neural networks",
    "transformers",
    "robotics",
    "mathematics",
    "statistics",
    "optimization",
    "probability theory",
    "linear algebra",
    "numerical analysis",
    "physics",
    "quantum physics",
    "quantum mechanics",
    "astrophysics",
    "particle physics",
    "condensed matter physics",
    "biology",
    "molecular biology",
    "genetics",
    "genomics",
    "cell biology",
    "evolutionary biology",
    "chemistry",
    "organic chemistry",
    "inorganic chemistry",
    "physical chemistry",
    "materials science",
    "electrical engineering",
    "mechanical engineering",
    "civil engineering",
    "chemical engineering",
    "computer engineering",
    "medicine",
    "clinical medicine",
    "public health",
    "epidemiology",
    "biomedical research",
    "economics",
    "finance",
    "psychology",
    "sociology",
    "political science",
)

DEFAULT_ALLOWED_LICENSES: tuple[str, ...] = (
    "cc-by",
    "cc-by-sa",
    "cc0",
    "public-domain",
)


@dataclass
class DownloadConfig:
    """User-tunable settings for one corpus-download run.

    Attributes:
        api_key: OpenAlex API key.
        output_dir: Root folder papers/metadata/state are written into.
        search_terms: Search queries to run against the OpenAlex API.
        min_year: Earliest publication year to accept.
        min_citations: Minimum citation count to accept.
        max_papers_per_term: Maximum candidate papers kept per search term.
        max_downloads_per_day: Daily PDF-download ceiling.
        download_workers: Number of parallel download threads.
        request_timeout: HTTP request timeout, in seconds.
        max_retries: Retry attempts for transient (5xx/network) failures.
        allowed_licenses: Licenses that are accepted; empty means "any".
        user_agent: User-Agent header sent with every HTTP request.
    """

    api_key: str = ""
    output_dir: Path = field(default_factory=lambda: Path("research-corpus"))
    search_terms: tuple[str, ...] = DEFAULT_SEARCH_TERMS
    min_year: int = 2015
    min_citations: int = 10
    max_papers_per_term: int = 100
    max_downloads_per_day: int = 100
    download_workers: int = 6
    request_timeout: int = 60
    max_retries: int = 2
    allowed_licenses: tuple[str, ...] = DEFAULT_ALLOWED_LICENSES
    user_agent: str = (
        "TinyLLMResearchCorpus/1.0 (open-access research corpus builder)"
    )

    @property
    def papers_dir(self) -> Path:
        """Return the folder downloaded PDFs are stored in."""
        return self.output_dir / "papers"

    @property
    def metadata_dir(self) -> Path:
        """Return the folder per-paper metadata JSON files are stored in."""
        return self.output_dir / "metadata"

    @property
    def state_dir(self) -> Path:
        """Return the folder the daily download-counter state lives in."""
        return self.output_dir / "state"

    @property
    def manifest_file(self) -> Path:
        """Return the path of the successful-downloads manifest."""
        return self.output_dir / "manifest.jsonl"

    @property
    def failed_file(self) -> Path:
        """Return the path of the failed-downloads log."""
        return self.output_dir / "failed.jsonl"

    @property
    def state_file(self) -> Path:
        """Return the path of the daily download-counter state file."""
        return self.state_dir / "download_state.json"

    def ensure_directories(self) -> None:
        """Create the papers/metadata/state folders if missing."""
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
