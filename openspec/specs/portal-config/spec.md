# Portal Configuration Specification

## Purpose

Provide a UI for users to add, edit, enable, disable, and test portal configurations with custom CSS/XPath selectors.

## Requirements

### Requirement: Portal CRUD

The system MUST allow authenticated users to create, read, update, and delete portal configurations.

#### Scenario: Add new portal

- GIVEN an authenticated user on the portal config page
- WHEN the user enters portal name, base URL, search URL template, and selectors
- THEN the system saves the portal configuration

#### Scenario: Delete portal

- GIVEN a user-owned portal configuration
- WHEN the user deletes it
- THEN the system removes the config and disables future scrapes

### Requirement: Selector Configuration

The system MUST support CSS and XPath selectors for each scraping field (title, company, description, location, date posted, application link).

#### Scenario: Configure selectors

- GIVEN the user is editing a portal
- WHEN the user provides CSS or XPath selectors for all required fields
- THEN the system validates selector syntax and saves them

#### Scenario: Missing required selector

- GIVEN the user attempting to save a portal config
- WHEN one or more required field selectors are missing
- THEN the system MUST reject with a validation error listing missing fields

### Requirement: Dry-Run Mode

The system MUST allow users to test a portal configuration without persisting results.

#### Scenario: Dry-run success

- GIVEN the user has configured selectors for a portal
- WHEN the user triggers a dry-run
- THEN the system scrapes a single page and returns preview results
- AND marks the config as valid

#### Scenario: Dry-run failure

- GIVEN the user has configured selectors
- WHEN the dry-run finds zero results
- THEN the system returns an error and does NOT enable the portal

### Requirement: Enable/Disable Portal

The system MUST allow users to enable or disable portals to control which are scraped.

#### Scenario: Toggle portal state

- GIVEN an existing portal configuration
- WHEN the user toggles it from disabled to enabled
- THEN the system includes it in the next scrape cycle
