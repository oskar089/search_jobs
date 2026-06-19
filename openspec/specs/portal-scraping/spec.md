# Portal Scraping Specification

## Purpose

Provide a pluggable scraping engine that extracts job postings from configured portals using Playwright browser automation.

## Requirements

### Requirement: Built-in Portal Selectors

The system MUST include built-in selector configurations for LinkedIn, Infojobs, Computrabajo, and Bumeran.

#### Scenario: Scrape LinkedIn successfully

- GIVEN a configured LinkedIn search URL and valid selector config
- WHEN the scraper runs
- THEN it returns structured job postings (title, company, description, location, date, URL)

#### Scenario: Portal layout changes

- GIVEN a built-in portal whose selectors no longer match the page structure
- WHEN the scraper runs and returns zero or malformed results
- THEN the system MUST log the failure and alert the user

### Requirement: Pluggable Scraping Architecture

The system MUST support loading per-portal selector configurations dynamically from the database.

#### Scenario: Plug in custom portal config

- GIVEN a user has configured a custom portal with valid selectors
- WHEN the scraping engine loads it
- THEN it uses the stored selectors without code changes

### Requirement: Scrape Execution

The system MUST execute scrapes asynchronously with configurable concurrency limits.

#### Scenario: Single portal scrape

- GIVEN an enabled portal with valid selectors
- WHEN the system triggers a scrape
- THEN it navigates the browser, extracts postings, and stores them in the database

#### Scenario: Concurrent scrapes

- GIVEN multiple enabled portals
- WHEN the system triggers a batch scrape
- THEN it runs scrapes concurrently within the configured concurrency limit

### Requirement: Scrape Error Handling

The system SHOULD handle scraping failures gracefully without crashing the pipeline.

#### Scenario: Network timeout

- GIVEN a portal that is unreachable
- WHEN the scraper encounters a timeout
- THEN the system retries up to 3 times with exponential backoff
- AND marks the portal as errored if all retries fail
