# User Auth Specification

## Purpose

Handle user registration, authentication, session management, and password recovery for the job search application.

## Requirements

### Requirement: User Registration

The system MUST allow a new user to register with a valid email address and password. The system MUST rate-limit registration requests to 10 per minute per IP.
(Previously: User registration without rate limiting)

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

#### Scenario: Rate-limited registration

- GIVEN an IP that has made 10 or more registration attempts in the last minute
- WHEN the user submits another registration from the same IP
- THEN the system MUST return a 429 Too Many Requests response

### Requirement: User Login

The system MUST authenticate users via email and password and issue a session token delivered as an httpOnly, Secure, SameSite cookie. The system MUST rate-limit login requests to 5 per minute per IP.
(Previously: Login returned a token without cookie delivery or rate limiting)

#### Scenario: Successful login

- GIVEN a registered user with valid credentials
- WHEN the user submits email and password
- THEN the system sets an httpOnly, Secure, SameSite cookie with the JWT access token
- AND returns the refresh token in the response body

#### Scenario: Invalid credentials

- GIVEN a registered user
- WHEN the user submits an incorrect password
- THEN the system MUST return a generic "invalid credentials" error without revealing which field is wrong

#### Scenario: Rate-limited login

- GIVEN an IP that has made 5 or more failed login attempts in the last minute
- WHEN the user submits another login from the same IP
- THEN the system MUST return a 429 Too Many Requests response

### Requirement: Session Management

The system MUST maintain authenticated sessions with JWT-based expiry, refresh rotation, and token blacklisting. Access tokens MUST expire after 15 minutes. Refresh tokens MUST expire after 7 days.
(Previously: Session management with configurable expiry and refresh support without rotation)

#### Scenario: Access token expiry

- GIVEN an authenticated user with an expired access token
- WHEN the user makes an API request
- THEN the system MUST reject with a 401 status code

#### Scenario: Token refresh with rotation

- GIVEN an authenticated user with a valid refresh token
- WHEN the user requests a new access token
- THEN the system MUST issue a new access token and a new refresh token
- AND blacklist the previous refresh token

#### Scenario: Reused refresh token detected

- GIVEN a refresh token that was already rotated (blacklisted)
- WHEN a client attempts to use it
- THEN the system MUST reject with a 401 status code
- AND invalidate all refresh tokens for that user (potential token theft)

#### Scenario: Logout invalidates refresh token

- GIVEN an authenticated user with a valid refresh token
- WHEN the user calls the logout endpoint
- THEN the system MUST blacklist the refresh token immediately

### Requirement: Account Lockout

The system MUST lock an account for 15 minutes after 5 consecutive failed login attempts.

#### Scenario: Account locked after failures

- GIVEN an email with 5 consecutive failed login attempts
- WHEN the user submits correct credentials
- THEN the system rejects with an account-locked error
- AND includes the remaining lockout time

#### Scenario: Lockout expires

- GIVEN a locked account that has waited 15 minutes
- WHEN the user submits correct credentials
- THEN the system allows login and resets the failure counter

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
