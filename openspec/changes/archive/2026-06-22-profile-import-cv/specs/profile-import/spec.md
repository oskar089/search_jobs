# Profile Import Specification

## Purpose

Import professional profile data from external platforms (LinkedIn, Infojobs) into an editable preview, then merge with the user's existing profile without data loss.

## Requirements

### Requirement: LinkedIn URL Import

The system MUST accept a LinkedIn profile URL and return parsed profile data via a third-party API (ProxyCurl / Scrapin.io).

#### Scenario: Successful LinkedIn import

- GIVEN an authenticated user
- WHEN the user submits a valid LinkedIn profile URL
- THEN the system returns parsed fields: headline, summary, skills, education, and work_experience

#### Scenario: LinkedIn profile not found

- GIVEN an authenticated user
- WHEN the LinkedIn API returns no data for the given URL
- THEN the system MUST reject with a descriptive error message

### Requirement: Infojobs URL Import

The system MUST accept an Infojobs public profile URL and return parsed profile data via scraping.

#### Scenario: Successful Infojobs import

- GIVEN an authenticated user
- WHEN the user submits a valid Infojobs public profile URL
- THEN the system returns available parsed fields: headline, summary, skills, and work_experience

#### Scenario: Scraping failure on layout change

- GIVEN an authenticated user
- WHEN the Infojobs page layout has changed and scraping fails
- THEN the system MUST return an error and log the failure for monitoring

### Requirement: Editable Preview

The system MUST present imported data as an editable preview before persisting anything.

#### Scenario: Preview before save

- GIVEN an authenticated user who has imported profile data
- WHEN the preview is displayed
- THEN the user MAY edit any field before confirming
- AND no data has been persisted yet

### Requirement: Merge-Save Flow

The system MUST merge imported data with the user's existing profile using an additive strategy. Imported data MUST NOT overwrite existing non-empty fields.

#### Scenario: Merge with existing profile

- GIVEN an authenticated user with a populated profile
- WHEN the user confirms the import preview
- THEN the system fills empty fields and appends new entries without overwriting populated fields

#### Scenario: Full import to empty profile

- GIVEN an authenticated user with no existing profile data
- WHEN the user confirms the import preview
- THEN the system saves all imported fields as the profile

### Requirement: Error Handling

The system MUST handle invalid URLs, unavailable profiles, and third-party failures gracefully.

#### Scenario: Invalid URL format

- GIVEN an authenticated user
- WHEN the user submits a malformed or unsupported URL
- THEN the system MUST reject with a validation error

#### Scenario: Third-party API timeout

- GIVEN an authenticated user
- WHEN the third-party API times out or returns an error
- THEN the system MUST return a timeout error to the user
- AND a retry MAY be attempted automatically
