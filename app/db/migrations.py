from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply small additive migrations for existing local/dev databases.

    Fresh databases get the same columns from SQLAlchemy metadata. This helper
    adds them when an older Carrershunt database already exists.
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "candidate_profiles" in tables:
        columns = {column["name"] for column in inspector.get_columns("candidate_profiles")}
        if "supabase_user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE candidate_profiles ADD COLUMN supabase_user_id VARCHAR(36)"))
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_candidate_profiles_supabase_user_id "
                "ON candidate_profiles (supabase_user_id)"
            ))
    if "jobs" in tables and "companies" in tables:
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE jobs SET status = 'stale' WHERE "
                "length(trim(coalesce(description, ''))) < 100 OR "
                "job_url = (SELECT careers_url FROM companies WHERE companies.id = jobs.company_id)"
            ))
    if "resume_versions" in tables:
        columns = {column["name"] for column in inspector.get_columns("resume_versions")}
        if "candidate_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE resume_versions ADD COLUMN candidate_id INTEGER REFERENCES candidate_profiles(id)"))
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_resume_versions_candidate_id "
                "ON resume_versions (candidate_id)"
            ))
