# Secrets Management Specification

## Purpose

Securely manage application secrets and configuration via environment variables and Docker secrets, ensuring no hardcoded credentials exist in the repository.

## Requirements

### Requirement: Environment-Based Configuration

All secrets MUST be loaded from environment variables at startup. The system MUST NOT default to real or production credentials.

#### Scenario: Load secrets from env

- GIVEN a running backend service
- WHEN the application starts
- THEN all secrets (JWT_SECRET, DATABASE_URL, etc.) are loaded from environment variables

#### Scenario: Missing required variable

- GIVEN the application is starting
- WHEN a required secret is not set
- THEN the system MUST fail with a clear error naming the missing variable

### Requirement: JWT Secret Validation

The system MUST validate JWT_SECRET at startup. It MUST be at least 32 characters and MUST NOT be a placeholder or known default value.

#### Scenario: Valid secret accepted

- GIVEN JWT_SECRET is at least 32 characters
- WHEN the application starts
- THEN startup proceeds normally

#### Scenario: Short or default secret rejected

- GIVEN JWT_SECRET is shorter than 32 characters or a known default
- WHEN the application starts
- THEN the system MUST reject with a security startup error

### Requirement: Database URL Required

The system MUST require DATABASE_URL at startup. No default value is acceptable.

#### Scenario: Missing DATABASE_URL

- GIVEN the application is starting
- WHEN DATABASE_URL is not set
- THEN the system MUST fail immediately with a startup error

#### Scenario: DATABASE_URL present

- GIVEN DATABASE_URL is set in the environment
- WHEN the application starts
- THEN the connection string is accepted and used

### Requirement: Docker Secrets Support

The system MUST support reading secrets from Docker secrets files in production.

#### Scenario: Docker secret file loading

- GIVEN a container with Docker secrets mounted at /run/secrets/
- WHEN the application starts and an env var is not set
- THEN it reads the corresponding /run/secrets/<name> file as fallback

### Requirement: Startup Configuration Validation

The system MUST validate all required configuration at startup before accepting requests.

#### Scenario: All configs valid

- GIVEN the application is starting
- WHEN all required config passes validation
- THEN the system logs each validated setting and starts serving requests

#### Scenario: Startup validation failure

- GIVEN a missing or invalid required config
- WHEN the application starts
- THEN the system reports all failures and exits before binding to any port

### Requirement: Environment Example Documentation

The system MUST ship a .env.example file documenting all required variables with descriptions and placeholder values.

#### Scenario: .env.example present

- GIVEN the project repository
- WHEN a developer checks the repository root
- THEN .env.example exists with all required variables documented
- AND placeholder values are clearly marked as invalid for production
