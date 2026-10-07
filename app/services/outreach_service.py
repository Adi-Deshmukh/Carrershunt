from app.db.models import Job, Person, CandidateProfile


def generate_outreach(candidate: CandidateProfile, job: Job, person: Person | None = None) -> dict[str, str]:
    recipient = person.name if person else "there"
    team = person.role if person and person.role else "your team"

    subject = f"Interested in {job.title} at {job.company.name if job.company else 'your company'}"
    body = (
        f"Hi {recipient},\n\n"
        f"I'm {candidate.name}, a candidate interested in the {job.title} opportunity. "
        f"My background includes the projects and skills described in my application materials, "
        f"particularly work relevant to {team}.\n\n"
        f"I'd appreciate any advice you can share about the role or team. "
        f"If you feel my background is a fit, I would also be grateful if you would consider referring me.\n\n"
        f"Best,\n{candidate.name}"
    )
    return {"subject": subject, "body": body}
