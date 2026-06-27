# Infrastructure Hardening Specification

## Purpose

Define infrastructure stability, resource management, and security requirements for Docker-based deployment.

## Requirements

### Requirement: Docker Resource Limits

All services MUST have CPU and memory limits defined in Docker Compose.

#### Scenario: Backend resource limited

- GIVEN the backend service in docker-compose.yml
- WHEN the container starts
- THEN it MUST have configured CPU and memory limits
- AND MUST NOT exceed the allocated resources

#### Scenario: All services bounded

- GIVEN every service in docker-compose.yml
- WHEN inspected
- THEN each service MUST define deploy.resources.limits

### Requirement: Docker Health Checks

All services MUST include health check configurations in Docker Compose.

#### Scenario: Health probe configured

- GIVEN a service running in Docker
- WHEN the health check interval elapses
- THEN Docker probes the service endpoint
- AND marks the container unhealthy if the probe fails

#### Scenario: Unhealthy container logged

- GIVEN a service fails its health check
- WHEN Docker detects the failure
- THEN the container is marked unhealthy in Docker logs

### Requirement: Multi-Stage Docker Build

The backend Dockerfile MUST use multi-stage builds to minimize the final image size.

#### Scenario: Builder and runtime stages

- GIVEN the backend Dockerfile
- WHEN built
- THEN it uses a builder stage for dependencies and compilation
- AND a separate runtime stage with only required artifacts

### Requirement: Redis Authentication

Redis MUST require password authentication and MUST NOT accept unauthenticated connections.

#### Scenario: Redis connection with password

- GIVEN the Redis service is configured with a password
- WHEN a client connects
- THEN it MUST provide the configured password
- AND the connection succeeds

#### Scenario: Unauthenticated Redis rejected

- GIVEN a client connects to Redis without a password
- WHEN authentication is required
- THEN the connection MUST be rejected

### Requirement: Internal Network Isolation

Database and Redis ports MUST NOT be exposed externally. Only the backend and frontend SHOULD expose ports.

#### Scenario: Internal ports not published

- GIVEN the Docker Compose network
- WHEN inspected
- THEN PostgreSQL and Redis containers MUST NOT publish ports to the host
- AND only backend (API) and frontend (HTTP) ports are reachable

### Requirement: SMTP Security

The system MUST enforce STARTTLS for SMTP connections and MUST verify connectivity at startup.

#### Scenario: STARTTLS enforced

- GIVEN SMTP is configured
- WHEN the application sends an email
- THEN it MUST use STARTTLS
- AND fail if the server does not support it

#### Scenario: SMTP startup check

- GIVEN SMTP is configured
- WHEN the application starts
- THEN it MUST perform a connectivity check
- AND log a warning if the SMTP server is unreachable
