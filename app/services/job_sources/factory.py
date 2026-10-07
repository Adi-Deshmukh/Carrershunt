from urllib.parse import urlparse

from app.services.job_sources.ashby import AshbySource
from app.services.job_sources.base import JobSource
from app.services.job_sources.generic import GenericSource
from app.services.job_sources.greenhouse import GreenhouseSource
from app.services.job_sources.lever import LeverSource


def detect_platform(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if "greenhouse" in host or "greenhouse.io" in path:
        return "greenhouse"
    if "lever" in host or "lever.co" in path:
        return "lever"
    if "ashby" in host or "ashbyhq" in path:
        return "ashby"
    return "generic"


def get_source(platform: str) -> JobSource:
    return {
        "greenhouse": GreenhouseSource(),
        "lever": LeverSource(),
        "ashby": AshbySource(),
        "generic": GenericSource(),
    }.get(platform, GenericSource())
