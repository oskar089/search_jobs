"""
Built-in selector configuration for Infojobs Argentina.

NOTE: These CSS selectors target Infojobs' job listing page structure at the
time of writing. Infojobs may update its DOM layout — run a dry-run to verify
selectors if scraping returns empty or malformed results.

Test URL pattern:
    https://www.infojobs.com.ar/ofertas-trabajo/software-engineer
"""

# CSS selectors targeting Infojobs search results page
INFOJOBS_SELECTORS = {
    "job_card": "article.ij-OfferCard",
    "title": "h2.ij-OfferCard__title a",
    "company": "span.ij-OfferCard__company-name",
    "location": "span.ij-OfferCard__location",
    "description": "p.ij-OfferCard__description",
    "url": "h2.ij-OfferCard__title a",
    "salary": "span.ij-OfferCard__salary",
    "posted_date": "span.ij-OfferCard__date",
    "apply_button": None,
}
