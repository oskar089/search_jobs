"""
Built-in selector configuration for LinkedIn job listings.

NOTE: These CSS selectors are approximate and based on LinkedIn's common job
listing page structure at the time of writing. LinkedIn frequently changes
its DOM layout, so these WILL likely need updates over time.

If the scraper returns empty or malformed results for LinkedIn, the selectors
are the first thing to check. Run a dry-run to verify before debugging further.
"""

# CSS selectors targeting LinkedIn's job search results page
# Test URL pattern: https://www.linkedin.com/jobs/search/?keywords=software-engineer&location=Argentina
LINKEDIN_SELECTORS = {
    "job_card": "li.jobs-search-results__list-item",
    "title": "a.job-card-list__title span",
    "company": "a.job-card-list__company-name",
    "location": "li.job-card-container__metadata-item",
    "description": None,  # Requires navigating to detail pane; fetched on card click
    "url": "a.job-card-list__title",
    "salary": None,
    "posted_date": "time",
    "apply_button": None,
}

# Note on description scraping:
# LinkedIn does not show the full description in the search results list.
# To get the description, you would need to click each job card and wait for
# the detail pane to load, then extract from `.jobs-description-content__text`.
# This is intentionally left as None for now — description extraction will
# require per-card navigation in a future enhancement.
