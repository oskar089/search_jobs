# CV Management Specification

## Purpose

Allow users to upload CV/resume PDFs, parse them via OpenAI to extract profile fields, and manage the stored files (download, delete) linked to their profile.

## Requirements

### Requirement: PDF Upload and Parsing

The system MUST accept a PDF file upload, parse its content via OpenAI, and return extracted fields for preview.

#### Scenario: Successful PDF upload and parse

- GIVEN an authenticated user
- WHEN the user uploads a valid PDF file
- THEN the system parses the PDF via OpenAI and returns extracted fields: headline, summary, skills, education, and work_experience

#### Scenario: Upload non-PDF file

- GIVEN an authenticated user
- WHEN the user uploads a file that is not a PDF
- THEN the system MUST reject with a format validation error

### Requirement: File Storage

The system MUST store uploaded CV PDFs persistently on the local filesystem or S3-compatible storage.

#### Scenario: Store uploaded file

- GIVEN an authenticated user who uploaded a CV
- WHEN the file is successfully parsed
- THEN the system persists the original PDF to the configured storage backend

### Requirement: File Download

The system MUST allow users to download their uploaded CV PDF.

#### Scenario: Download existing CV

- GIVEN an authenticated user with an uploaded CV
- WHEN the user requests to download the CV file
- THEN the system serves the original PDF file

#### Scenario: Download non-existent CV

- GIVEN an authenticated user
- WHEN the user requests a CV file that does not exist
- THEN the system MUST return a 404 error

### Requirement: File Delete

The system MUST allow users to delete their uploaded CV PDF.

#### Scenario: Delete existing CV

- GIVEN an authenticated user with an uploaded CV
- WHEN the user deletes the CV
- THEN the system removes the file from storage and clears the profile reference

#### Scenario: Delete non-existent CV

- GIVEN an authenticated user
- WHEN the user attempts to delete a CV that does not exist
- THEN the system MUST return a 404 error

### Requirement: Size Limits

The system MUST enforce file size limits on CV uploads.

#### Scenario: File exceeds size limit

- GIVEN an authenticated user
- WHEN the user uploads a PDF larger than the configured maximum (default 10 MB)
- THEN the system MUST reject with a size validation error

### Requirement: Preview Before Save

The system MUST show parsed CV fields in a preview for user review before persisting any extracted data to the profile.

#### Scenario: Preview parsed CV data

- GIVEN an authenticated user who uploaded and parsed a CV
- WHEN the parsed fields are displayed
- THEN the user MAY edit or discard fields before confirming
- AND no extracted data is saved to the profile until confirmed
