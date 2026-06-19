# User Auth Specification

## Purpose

Handle user registration, authentication, session management, and password recovery for the job search application.

## Requirements

### Requirement: User Registration

The system MUST allow a new user to register with a valid email address and password.

#### Scenario: Successful registration

- GIVEN the user provides a valid email, password (min 8 chars, one uppercase, one number), and optional name
- WHEN the user submits the registration form
- THEN the system creates the account with a hashed password
- AND returns a confirmation to the user

#### Scenario: Duplicate email registration

- GIVEN a user with email "user@example.com" already exists
- WHEN another user attempts to register with the same email
- THEN the system MUST reject the registration with a clear error message

#### Scenario: Weak password

- GIVEN the user provides a password shorter than 8 characters or lacking required complexity
- WHEN the user submits the registration form
- THEN the system MUST reject with a password policy error

### Requirement: User Login

The system MUST authenticate users via email and password and issue a session token.

#### Scenario: Successful login

- GIVEN a registered user with valid credentials
- WHEN the user submits email and password
- THEN the system returns a session token with configurable expiry

#### Scenario: Invalid credentials

- GIVEN a registered user
- WHEN the user submits an incorrect password
- THEN the system MUST return a generic "invalid credentials" error without revealing which field is wrong

### Requirement: Session Management

The system MUST maintain authenticated sessions with token-based expiry and refresh support.

#### Scenario: Token expiry

- GIVEN an authenticated user with an expired session token
- WHEN the user makes an API request
- THEN the system MUST reject with a 401 status code

#### Scenario: Token refresh

- GIVEN an authenticated user with a valid refresh token
- WHEN the user requests a new access token
- THEN the system MUST issue a new token and invalidate the old one

### Requirement: Password Reset

The system SHOULD allow users to reset their password via email verification.

#### Scenario: Password reset flow

- GIVEN a registered user who forgot their password
- WHEN the user requests a password reset
- THEN the system sends a reset link to the user's email with a one-time code expiring in 15 minutes

#### Scenario: Expired reset token

- GIVEN a user with an expired password reset token
- WHEN the user attempts to use it
- THEN the system MUST reject and prompt for a new reset request
