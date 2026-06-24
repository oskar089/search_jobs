# Profile Management Specification

## Purpose

Manage user professional profiles including tech stack, experience level, preferences, and target roles for job matching.

## Requirements

### Requirement: Profile Creation and Update

The system MUST allow authenticated users to create and update their professional profile. The system MUST accept the following additional fields from imports and CV parsing: headline, summary, skills (with proficiency level), education, work_experience, linkedin_url, infojobs_url, and cv_file_url.
(Previously: Profile creation and update accepted tech stack, experience level, preferences, and target roles only)

#### Scenario: Create full profile

- GIVEN an authenticated user with no existing profile
- WHEN the user submits all profile fields including import/CV fields (headline, summary, skills, education, work_experience, linkedin_url, infojobs_url, cv_file_url)
- THEN the system creates the profile and confirms success

#### Scenario: Update existing profile

- GIVEN an authenticated user with an existing profile
- WHEN the user modifies any profile field (including new import/CV fields)
- THEN the system updates and persists the changes

#### Scenario: Merge imported data into existing profile

- GIVEN an authenticated user with an existing profile that has populated fields
- WHEN the user confirms import or CV preview data
- THEN the system merges imported data using additive strategy — empty fields are filled, new entries are appended, populated fields are never overwritten

### Requirement: Import Preview

The system MUST expose an endpoint that accepts imported or parsed profile data and returns a preview before the user confirms the merge.

#### Scenario: Preview imported data before merge

- GIVEN an authenticated user who has imported data from LinkedIn, Infojobs, or CV parsing
- WHEN the user requests a preview of the data
- THEN the system returns the parsed fields for user review
- AND no data is persisted

#### Scenario: Preview from empty import

- GIVEN an authenticated user
- WHEN the imported data is empty or incomplete
- THEN the system SHOULD still show the preview with available fields and indicate missing fields

### Requirement: Tech Stack Specification

The system MUST allow users to specify their technology stack with skill levels.

#### Scenario: Add technologies

- GIVEN the user is editing their profile
- WHEN the user adds technologies with proficiency levels (beginner, intermediate, advanced, expert)
- THEN the system stores them for match scoring

#### Scenario: Empty tech stack

- GIVEN an authenticated user
- WHEN the user submits a profile without a tech stack
- THEN the system SHOULD warn but accept, with an empty tech stack

### Requirement: Target Roles and Preferences

The system MUST allow users to define target job roles and search preferences.

#### Scenario: Set target roles

- GIVEN the user is editing preferences
- WHEN the user adds one or more target job titles
- THEN the system stores them as primary match criteria

#### Scenario: Set search radius and job type

- GIVEN the user is editing preferences
- WHEN the user sets location, max distance, remote preference, and salary range
- THEN the system stores these for filtering job matches

### Requirement: Experience Level

The system SHOULD allow users to specify years of experience and seniority level.

#### Scenario: Set experience

- GIVEN the user is editing their profile
- WHEN the user selects total years of experience and seniority level (junior, mid, senior, lead)
- THEN the system stores the selection

### Requirement: Profile Validation

The system MUST validate all profile data before persisting.

#### Scenario: Invalid salary range

- GIVEN the user entering salary preferences
- WHEN the user sets a minimum salary higher than maximum
- THEN the system MUST reject with a validation error
