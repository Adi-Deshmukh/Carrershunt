from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, CandidateEvidence, CandidateProfile
from app.services.evidence import EvidenceInput, retrieve_evidence, upsert_evidence


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_upsert_evidence_is_idempotent():
    db = make_db()
    candidate = CandidateProfile(name="Test", resume_text="Python developer")
    db.add(candidate)
    db.flush()

    item = EvidenceInput(
        source="github",
        source_key="repo:test/demo",
        title="Demo",
        content="Python FastAPI PostgreSQL",
        skills=["Python", "FastAPI"],
    )
    first = upsert_evidence(db, candidate.id, item)
    db.flush()
    second = upsert_evidence(db, candidate.id, item)
    db.commit()

    assert first.id == second.id
    assert len(db.scalars(select(CandidateEvidence)).all()) == 1


def test_retrieval_ranks_relevant_evidence():
    db = make_db()
    candidate = CandidateProfile(name="Test", resume_text="Python developer")
    db.add(candidate)
    db.flush()

    upsert_evidence(
        db,
        candidate.id,
        EvidenceInput(
            source="github",
            source_key="repo:one",
            title="Fleet backend",
            content="FastAPI PostgreSQL machine learning pipeline",
            skills=["Python", "FastAPI", "PostgreSQL"],
        ),
    )
    upsert_evidence(
        db,
        candidate.id,
        EvidenceInput(
            source="github",
            source_key="repo:two",
            title="Frontend",
            content="React CSS UI components",
            skills=["React"],
        ),
    )
    db.commit()

    results = retrieve_evidence(db, candidate.id, "Python FastAPI PostgreSQL", limit=2)

    assert results[0]["source_key"] == "repo:one"
    assert results[0]["score"] > results[1]["score"]


def test_retrieval_respects_candidate_boundary():
    db = make_db()
    first = CandidateProfile(name="One", resume_text="Python")
    second = CandidateProfile(name="Two", resume_text="Java")
    db.add_all([first, second])
    db.flush()

    upsert_evidence(
        db,
        second.id,
        EvidenceInput(
            source="github",
            source_key="repo:shared",
            title="Shared",
            content="Python FastAPI",
        ),
    )
    db.commit()

    assert retrieve_evidence(db, first.id, "Python") == []
