# Delta for Profile Management

## ADDED Requirements

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

## MODIFIED Requirements

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
