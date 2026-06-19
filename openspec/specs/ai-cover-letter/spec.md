# AI Cover Letter Specification

## Purpose

Dynamically generate personalized cover letters for job applications using an LLM API, matching the posting's language and maintaining a formal professional tone.

## Requirements

### Requirement: Cover Letter Generation

The system MUST generate a cover letter given the user's profile and a job posting.

#### Scenario: Generate cover letter

- GIVEN a user profile (name, experience, tech stack) and a job posting (title, company, description)
- WHEN the system calls the LLM API
- THEN it returns a complete cover letter in formal tone

#### Scenario: LLM API failure

- GIVEN the LLM API is unavailable or returns an error
- WHEN the system attempts to generate
- THEN it MUST retry once after 5 seconds
- AND fail with an error if the second attempt also fails

### Requirement: Language Matching

The system MUST detect the job posting's language and generate the cover letter in that same language.

#### Scenario: Spanish job posting

- GIVEN a job posting written in Spanish
- WHEN the cover letter is generated
- THEN the output is written in formal Spanish

#### Scenario: English job posting

- GIVEN a job posting written in English
- WHEN the cover letter is generated
- THEN the output is written in formal English

### Requirement: Formal Tone Enforcement

The system MUST instruct the LLM to produce a formal, professional cover letter suitable for corporate job applications.

#### Scenario: Tone consistency

- GIVEN any job posting in any supported language
- WHEN the cover letter is generated
- THEN the tone MUST be formal — no slang, casual phrases, or humor

### Requirement: Token Cost Management

The system SHOULD limit prompt size and implement caching to manage LLM API costs.

#### Scenario: Duplicate posting generation

- GIVEN a cover letter was already generated for a specific user+posting combination
- WHEN the system requests generation again
- THEN it SHOULD return the cached version instead of calling the API
