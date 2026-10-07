from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.people_service import ManualPeopleProvider

router = APIRouter(prefix="/people", tags=["people"])


@router.get("/search")
async def search_people(company: str, role: str, db: Session = Depends(get_db)):
    del db
    provider = ManualPeopleProvider()
    results = await provider.search(company, role, [])
    return {"results": [r.__dict__ for r in results]}
