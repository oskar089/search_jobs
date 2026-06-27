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

The system MUST handle scraping failures gracefully with exponential backoff, jitter, and stealth fallback without crashing the pipeline.
(Previously: Error handling with basic exponential backoff, no jitter or stealth fallback)

#### Scenario: Network timeout with backoff

- GIVEN a portal that is unreachable
- WHEN the scraper encounters a network timeout
- THEN it retries up to 5 times with exponential backoff and jitter (1s, 2s, 4s, 8s, 16s max)
- AND marks the portal as errored if all retries fail

#### Scenario: Stealth fallback on failure

- GIVEN a portal that blocks the scraper in stealth mode
- WHEN all stealth retries fail
- THEN the system falls back to non-stealth mode and retries once
- AND logs the stealth failure for monitoring

### Requirement: Playwright Stealth

The system MUST inject Playwright stealth scripts when scraping job portals to reduce bot detection risk.

#### Scenario: Stealth injection on job scrape

- GIVEN a configured job portal scrape
- WHEN the scraper initializes the browser context
- THEN it injects stealth scripts before navigating to the portal
- AND logs whether injection succeeded

#### Scenario: Stealth injection failure

- GIVEN a portal scrape
- WHEN the stealth script injection fails
- THEN the system logs the failure
- AND continues without stealth (scrape proceeds in normal mode)
