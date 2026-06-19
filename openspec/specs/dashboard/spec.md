# Dashboard Specification

## Purpose

Provide the main user interface for viewing application history, statistics, and managing configuration settings.

## Requirements

### Requirement: Application History View

The system MUST display a paginated list of all job applications with status, date, company, and job title.

#### Scenario: View application history

- GIVEN an authenticated user with submitted applications
- WHEN the user navigates to the history page
- THEN the system displays applications sorted by date (newest first) with status badges

#### Scenario: Empty history

- GIVEN a newly registered user with no applications
- WHEN the user navigates to the history page
- THEN the system displays an empty state message with a guide to get started

### Requirement: Application Details

The system MUST show detailed information for each application including the generated cover letter.

#### Scenario: View application detail

- GIVEN an application in the history list
- WHEN the user clicks on it
- THEN the system shows company info, job title, match score, cover letter content, and application status timeline

### Requirement: Statistics and Analytics

The system MUST display aggregate statistics about the user's job search activity.

#### Scenario: Dashboard stats view

- GIVEN a user with application history
- WHEN the user views the dashboard
- THEN the system shows total applications, success rate, applications per portal, and average match score

#### Scenario: Stats with no data

- GIVEN a user with no applications
- WHEN the user views the dashboard
- THEN the system shows zero values for all stats with a prompt to configure scraping

### Requirement: Configuration UI Access

The system MUST provide navigation and UI entry points to all configuration sections (profile, portals, notifications, thresholds).

#### Scenario: Navigate to settings

- GIVEN an authenticated user on the dashboard
- WHEN the user clicks a settings link
- THEN the system navigates to the corresponding configuration page

### Requirement: Search and Filter

The system SHOULD allow users to search and filter application history by date range, portal, status, and job title.

#### Scenario: Filter by portal

- GIVEN an application history with entries from multiple portals
- WHEN the user selects a specific portal filter
- THEN the system shows only applications from that portal
