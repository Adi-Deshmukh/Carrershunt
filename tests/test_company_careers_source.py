from app.services.job_sources.company_careers import _detail_candidate, _site
from app.services.job_sources.factory import detect_platform, get_source
from app.services.job_sources.company_careers import CompanyCareersSource


def test_known_careers_domains_use_company_adapter():
    urls = {
        "https://www.atlassian.com/company/careers/all-jobs": "atlassian",
        "https://www.google.com/about/careers/applications/jobs": "google",
        "https://jobs.careers.microsoft.com/global/en/search": "microsoft",
    }
    for url, expected in urls.items():
        assert detect_platform(url) == expected
        assert isinstance(get_source(expected), CompanyCareersSource)


def test_google_job_detail_link_is_detected():
    assert _site("https://www.google.com/about/careers/applications/jobs/results/131817929036440262-software-engineer")
    assert _detail_candidate(
        "google",
        "https://www.google.com/about/careers/applications/jobs/results/131817929036440262-software-engineer",
    )
    assert not _detail_candidate(
        "google",
        "https://www.google.com/about/careers/applications/jobs",
    )


def test_atlassian_job_detail_link_is_detected_but_index_is_not():
    assert _detail_candidate(
        "atlassian",
        "https://www.atlassian.com/company/careers/details/123456",
    )
    assert not _detail_candidate(
        "atlassian",
        "https://www.atlassian.com/company/careers/all-jobs",
    )


def test_microsoft_job_detail_link_is_detected():
    assert _detail_candidate(
        "microsoft",
        "https://jobs.careers.microsoft.com/global/en/job/123456/software-engineer",
    )
    assert not _detail_candidate(
        "microsoft",
        "https://jobs.careers.microsoft.com/global/en/search",
    )
