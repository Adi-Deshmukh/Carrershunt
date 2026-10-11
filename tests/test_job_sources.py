from app.services.job_sources.generic import _looks_like_job, _posting_to_record


def test_json_ld_posting_without_its_own_url_is_not_given_careers_index_url():
    record = _posting_to_record(
        {"@type": "JobPosting", "title": "Data Engineer", "description": "x" * 200},
        "https://example.com/careers",
    )
    assert record is None


def test_json_ld_posting_resolves_real_relative_job_url():
    record = _posting_to_record(
        {
            "@type": "JobPosting",
            "title": "Data Engineer",
            "url": "/jobs/123",
            "description": "<p>Build data pipelines and maintain production systems.</p>",
        },
        "https://example.com/careers",
    )
    assert record is not None
    assert record.job_url == "https://example.com/jobs/123"
    assert record.title == "Data Engineer"
    assert "Build data pipelines" in record.description


def test_job_link_detector_rejects_careers_index_but_accepts_detail_page():
    assert not _looks_like_job("Careers", "https://example.com/careers")
    assert _looks_like_job("Data Engineer", "https://example.com/jobs/12345")
