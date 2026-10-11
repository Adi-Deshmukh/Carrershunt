from app.services.job_sources.generic import _looks_like_job


def test_atlassian_career_resources_are_not_job_postings():
    non_jobs = [
        "https://www.atlassian.com/company/careers/resources/interviewing",
        "https://www.atlassian.com/company/careers/resources/career-growth",
        "https://www.atlassian.com/company/careers/engineering",
        "https://www.atlassian.com/company/careers/all-jobs",
        "https://www.atlassian.com/software/guard",
        "https://www.atlassian.com/company/careers/employee-awards",
    ]
    for url in non_jobs:
        assert not _looks_like_job("Engineering at Atlassian", url), url


def test_atlassian_talent_community_job_detail_is_accepted():
    assert _looks_like_job(
        "Backend Software Engineer, II",
        "https://join.atlassian.com/atlassian-talent-community/jobs/25540",
    )

def test_job_detail_under_a_department_category_is_accepted():
    assert _looks_like_job(
        "Software Engineer",
        "https://example.com/company/careers/engineering/jobs/12345",
    )


def test_supported_ats_job_details_are_accepted_but_board_indexes_are_not():
    assert _looks_like_job("Software Engineer", "https://boards.greenhouse.io/example/jobs/12345")
    assert not _looks_like_job("Jobs", "https://boards.greenhouse.io/example")
    assert _looks_like_job("Backend Engineer", "https://jobs.lever.co/example/backend-engineer-123")
    assert not _looks_like_job("Careers", "https://jobs.lever.co/example")
    assert _looks_like_job("Data Scientist", "https://jobs.ashbyhq.com/example/abc123")
    assert not _looks_like_job("Jobs", "https://jobs.ashbyhq.com/example")
