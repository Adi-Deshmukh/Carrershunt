from urllib.parse import urlparse

from app.services.job_sources.ashby import AshbySource
from app.services.job_sources.base import JobSource
from app.services.job_sources.generic import GenericSource
from app.services.job_sources.greenhouse import GreenhouseSource
from app.services.job_sources.lever import LeverSource


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "greenhouse" in host:
        return "greenhouse"
    if "lever" in host:
        return "lever"
    if "ashby" in host:
        return "ashby"
    return "generic"


def get_source(platform: str) -> JobSource:
    return {
        "greenhouse": GreenhouseSource(),
        "lever": LeverSource(),
        "ashby": AshbySource(),
        "generic": GenericSource(),
    }.get(platform, GenericSource())
