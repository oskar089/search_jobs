# API Security Specification

## Purpose

Define security controls for file uploads, CORS policy, HTTP security headers, debug mode, and health monitoring endpoints.

## Requirements

### Requirement: File Upload Validation

The system MUST validate file uploads by content-type, file extension, and magic bytes before accepting them.

#### Scenario: Valid PDF upload

- GIVEN a file with .pdf extension, application/pdf content-type, and %PDF- magic bytes
- WHEN the user uploads the file
- THEN the system accepts the upload

#### Scenario: Mismatched extension and content

- GIVEN a file claiming to be PDF
- WHEN the extension is .pdf but magic bytes do not start with %PDF-
- THEN the system MUST reject with a validation error

#### Scenario: Disallowed file type

- GIVEN a file with .exe or .html extension
- WHEN the user uploads it
- THEN the system MUST reject regardless of magic bytes

### Requirement: Path Traversal Prevention

The system MUST prevent path traversal attacks on CV download endpoints.

#### Scenario: Traversal attempt rejected

- GIVEN a CV download request
- WHEN the filename contains ../ or absolute path components
- THEN the system MUST reject with a 400 Bad Request
- AND MUST NOT leak file system structure in the response

### Requirement: CORS Policy

The system MUST enforce a strict CORS policy with a single allowed origin in production, configurable via environment variable.

#### Scenario: Allowed origin request

- GIVEN a request from the configured CORS origin
- WHEN it makes a cross-origin API request
- THEN the response includes the appropriate CORS headers

#### Scenario: Disallowed origin rejected

- GIVEN a request from an unlisted origin
- WHEN it makes a cross-origin request
- THEN the system MUST respond without CORS headers

### Requirement: Security Headers

All responses behind the nginx proxy MUST include security headers: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, and Strict-Transport-Security.

#### Scenario: Security headers present

- GIVEN any HTTP response from the nginx proxy
- WHEN inspected
- THEN it includes X-Frame-Options: DENY, X-Content-Type-Options: nosniff, and HSTS with a minimum 1-year max-age
- AND a restrictive Content-Security-Policy header

### Requirement: Debug Mode Protection

The system MUST disable debug mode by default when APP_ENV is not set to development.

#### Scenario: Debug off in production

- GIVEN APP_ENV is set to production or is unset
- WHEN the application starts
- THEN debug mode MUST be disabled
- AND detailed error traces MUST NOT be returned to clients

#### Scenario: Debug on in development

- GIVEN APP_ENV is set to development
- WHEN the application starts
- THEN debug mode MAY be enabled

### Requirement: Health Check Endpoint

The system MUST expose a /health endpoint that reports database, Redis, and Celery worker status.

#### Scenario: All services healthy

- GIVEN all infrastructure services are running
- WHEN a client requests GET /health
- THEN the response returns 200 with db, redis, and celery all showing healthy

#### Scenario: Service unhealthy

- GIVEN PostgreSQL, Redis, or Celery is unreachable
- WHEN a client requests GET /health
- THEN the response returns 503 with the failing component(s) shown as unhealthy
