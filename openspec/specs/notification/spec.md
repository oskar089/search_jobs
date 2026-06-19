# Notification Specification

## Purpose

Deliver application-related notifications via email and in-app channels, maintaining a complete notification history for users.

## Requirements

### Requirement: Email Delivery

The system MUST send email notifications for completed job applications.

#### Scenario: Application submitted email

- GIVEN an auto-application completes with status "submitted"
- WHEN the notification service runs
- THEN it sends an email to the user with company name, job title, and a summary

#### Scenario: Application failed email

- GIVEN an auto-application fails
- WHEN the notification service runs
- THEN it sends a failure notification email with the reason

#### Scenario: SMTP unavailable

- GIVEN the SMTP server is unreachable
- WHEN the notification service attempts to send an email
- THEN it retries up to 3 times with backoff
- AND stores the notification as "pending" if all retries fail

### Requirement: In-App Notification History

The system MUST store and display a persistent notification history accessible from the dashboard.

#### Scenario: Notification list

- GIVEN a user with multiple application events
- WHEN the user opens the notification panel
- THEN the system displays notifications sorted by timestamp (newest first)
- AND shows read/unread status

#### Scenario: Mark as read

- GIVEN an unread notification
- WHEN the user clicks it
- THEN the system marks it as read

### Requirement: Application Event Notifications

The system MUST generate a notification for every application lifecycle event: submitted, failed, and duplicate.

#### Scenario: Duplicate application blocked

- GIVEN a job posting that was already applied to
- WHEN the system detects a duplicate
- THEN it generates a notification warning the user about the duplicate

### Requirement: Notification Preferences

The system SHOULD allow users to configure which notification types they receive via email.

#### Scenario: Disable email notifications

- GIVEN an authenticated user with email notifications enabled
- WHEN the user disables email notifications for application failures
- THEN the system stops sending failure alerts via email but still stores in-app notifications
