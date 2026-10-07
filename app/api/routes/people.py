from fastapi import APIRouter
from app.services.people_search import SerperPeopleProvider

router = APIRouter(prefix="/people", tags=["people"])


@router.get("/search")
async def search_people(company: str, role: str, skills: str = ""):
    provider = SerperPeopleProvider()
    results = await provider.search(company, role, [s.strip() for s in skills.split(",") if s.strip()])
    return {"results": [r.__dict__ for r in results]}
