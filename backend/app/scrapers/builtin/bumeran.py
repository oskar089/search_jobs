"""
Built-in selector configuration for Bumeran Argentina.

NOTE: These CSS selectors target Bumeran's job listing page structure at the
time of writing. Bumeran uses CSS-modules class names that change between
deploys, making selectors inherently fragile. The selectors below target
semantic data attributes when available and stable structural elements as
fallback.

If scraping returns empty results, inspect the current DOM and update these
selectors. Run a dry-run to verify before debugging further.

Test URL pattern:
    https://www.bumeran.com.ar/empleos/software-engineer.html
"""

# CSS selectors targeting Bumeran search results page
# Prefer data-* attributes over class names due to CSS-modules hash rotation
BUMERAN_SELECTORS = {
    "job_card": "[data-testid=job-card]",
    "title": "[data-testid=job-title] a",
    "company": "[data-testid=company-name]",
    "location": "[data-testid=location]",
    "description": "[data-testid=description]",
    "url": "[data-testid=job-title] a",
    "salary": "[data-testid=salary]",
    "posted_date": "[data-testid=posted-date]",
    "apply_button": None,
}
