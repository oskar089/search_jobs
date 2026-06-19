"""
Built-in selector configuration for Computrabajo Argentina.

NOTE: These CSS selectors target Computrabajo's job listing page structure at
the time of writing. Computrabajo may update its DOM layout — run a dry-run
to verify selectors if scraping returns empty or malformed results.

Test URL pattern:
    https://www.computrabajo.com.ar/trabajo-de-software-engineer
"""

# CSS selectors targeting Computrabajo search results page
COMPUTRABAJO_SELECTORS = {
    "job_card": "div.box",
    "title": "h2 a.js-o-link",
    "company": "span.datos_empresa",
    "location": "span.datos_ubicacion",
    "description": "div.descripcion small",
    "url": "h2 a.js-o-link",
    "salary": None,
    "posted_date": "span.datos_publicado",
    "apply_button": None,
}
