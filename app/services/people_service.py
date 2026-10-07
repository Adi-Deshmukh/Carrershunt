from dataclasses import dataclass


@dataclass
class PersonCandidate:
    name: str
    role: str
    profile_url: str
    relevance_score: float
    rationale: str
    public_email: str | None = None


class PeopleDiscoveryProvider:
    async def search(self, company: str, role: str, skills: list[str]) -> list[PersonCandidate]:
        raise NotImplementedError


class ManualPeopleProvider(PeopleDiscoveryProvider):
    async def search(self, company: str, role: str, skills: list[str]) -> list[PersonCandidate]:
        # The first implementation intentionally requires a public profile URL supplied
        # by the user/provider rather than scraping restricted social networks.
        return []
