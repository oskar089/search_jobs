# Job Matching Specification

## Purpose

Score job postings against user profiles and trigger automated applications when a configurable threshold is met.

## Requirements

### Requirement: Match Scoring

The system MUST compute a match score for each scraped job posting against each user's profile.

#### Scenario: Score a job posting

- GIVEN a user profile with tech stack, target roles, and preferences
- WHEN a new job posting is scraped
- THEN the system computes a score (0-100) based on role match, tech stack overlap, location, and experience fit

#### Scenario: No matching criteria

- GIVEN a user profile with no tech stack or target roles defined
- WHEN a job posting is scored
- THEN the system assigns a score of 0 and does NOT trigger auto-apply

### Requirement: Scoring Criteria

The system MUST weight multiple criteria in the match score: role title, tech stack, experience level, location/remote, and salary range.

#### Scenario: Role title match weight

- GIVEN a user targeting "Senior Frontend Developer"
- WHEN a posting title contains "Frontend Developer"
- THEN the role match component contributes proportionally to the total score

#### Scenario: Location mismatch

- GIVEN a user with on-site preference in "Buenos Aires"
- WHEN a posting is in "Madrid" with no remote option
- THEN the location component reduces the total score significantly

### Requirement: Auto-Apply Trigger

The system MUST trigger auto-application for postings exceeding the user's configured threshold.

#### Scenario: Score exceeds threshold

- GIVEN a user with threshold set to 75
- WHEN a job posting scores 82
- THEN the system queues an auto-application job

#### Scenario: Score below threshold

- GIVEN a user with threshold set to 75
- WHEN a job posting scores 60
- THEN the system stores the match but does NOT trigger auto-apply

### Requirement: Threshold Configuration

The system SHOULD allow users to set a custom match threshold per profile.

#### Scenario: Custom threshold

- GIVEN an authenticated user
- WHEN the user sets a match threshold between 0 and 100
- THEN the system uses that value for auto-apply decisions
