# Product Requirements Document (PRD)
# VELTRIX — Encrypted Personal Data Vault

**Version:** 0.1 (Discussion Draft)  
**Project Type:** Web-Based Cryptography Application  
**Team Size:** 4 Members  
**Product Stage:** Academic MVP  
**Status:** Pending Team Review

---

## 1. Product Overview

### 1.1 Product Summary

Veltrix is a web-based personal data storage application that enables users to securely store, manage, encrypt, and retrieve sensitive personal information and digital files.

The platform implements three cryptographic algorithms—Advanced Encryption Standard (AES), Rivest Cipher 4 (RC4), and Data Encryption Standard (DES)—to demonstrate different encryption techniques and evaluate their computational performance.

In addition to encrypted storage, Veltrix includes a benchmarking module that compares encryption time, decryption time, ciphertext size, and algorithm characteristics.

Veltrix is developed as an educational cryptography project. RC4 and DES are included for academic comparison and must not be presented as secure choices for real-world protection of sensitive data.

### 1.2 Problem Statement

Personal information is frequently stored in digital systems, where inadequate protection can expose sensitive data to unauthorized access.

Users need mechanisms that limit access to their information, while software developers need practical understanding of how different cryptographic algorithms operate.

Veltrix addresses these objectives by developing a working encrypted storage application alongside an experimental environment for evaluating multiple encryption algorithms.

### 1.3 Product Goals

1. Develop a functional web application with user authentication.
2. Support encrypted storage of personal information, identity card images, documents, and video files.
3. Implement AES, RC4, and DES encryption and decryption.
4. Use non-ECB operation modes for block ciphers.
5. Ensure decrypted files match the original uploaded content.
6. Provide users with authenticated data retrieval.
7. Compare encryption and decryption performance using repeatable experiments.
8. Produce documented experimental findings and justified technical decisions.

### 1.4 Target Users

**Primary:** University students and lecturers evaluating cryptographic implementations.

**Secondary:** Demo users exploring the operation of encrypted digital storage.

**Important limitation:** The MVP uses fictional or synthetic personal information. It is not intended to store actual national identity cards or sensitive production data.

---

## 2. Product Scope

### 2.1 In Scope — MVP

- User registration, login, and logout
- Authenticated user dashboard
- Structured personal data storage
- Image upload for identity card demonstration
- Document uploads: PDF, DOC, DOCX, XLS, XLSX
- Video uploads: MP4
- Encryption with AES, RC4, and DES
- Securely managed encryption parameters and keys
- Storage of three encrypted representations of each data item
- Decryption and download of original content
- Basic file metadata and file management
- Algorithm performance comparison
- Repeated benchmarking experiments
- Error handling and automated testing
- Technical analysis report

### 2.2 Out of Scope — MVP

- Public file sharing
- Real-time collaboration
- Mobile native applications
- AI-based document processing
- File editing inside the browser
- Video transcoding or streaming previews
- Cloud synchronization across devices
- End-to-end encryption with user-controlled keys
- Enterprise compliance certification
- Commercial production deployment

---

## 3. Core Product Decisions

### PD-01: Encryption Strategy

**Proposed approach:** Every stored data item is encrypted independently using AES, RC4, and DES.

Example:

User uploads `identity.pdf`.

Veltrix creates:

- AES encrypted representation
- RC4 encrypted representation
- DES encrypted representation

All three versions are stored as encrypted bytes. The original unencrypted file is not retained in persistent application storage.

**Rationale:** This directly demonstrates the requirement to implement all three algorithms and makes comparisons possible using identical source data.

**Trade-off:** Encrypted storage consumption is approximately three times the original payload size, plus encryption metadata and overhead.

**Pending confirmation:** Verify whether the lecturer expects every item to be encrypted with all three algorithms or simply expects all algorithms to be available.

### PD-02: Block Cipher Mode

- AES: CBC mode with random IV
- DES: CBC mode with random IV
- RC4: Stream cipher; CBC/CFB/OFB/CTR block modes do not apply

AES and DES use appropriate padding and a separate HMAC mechanism for ciphertext integrity. RC4 uses independent, per-item derived keys and an integrity check.

**Security limitation:** These mechanisms do not eliminate the known weaknesses of DES or RC4.

### PD-03: Authentication

Passwords are processed using a password-hashing algorithm such as Argon2id rather than reversible encryption.

User access is restricted through authenticated server-side authorization checks.

### PD-04: Storage Architecture

Structured application data is stored in MySQL (team choice, 13 October 2026).

Encrypted binary files are stored in private filesystem storage, while MySQL maintains file metadata and references.

The backend handles authorized retrieval and decryption.

### PD-05: Default File Limits

Proposed MVP limits:

- Maximum file size: 25 MB
- Maximum uploads per user: configurable
- Supported file formats: JPEG, PNG, PDF, DOC, DOCX, XLS, XLSX, MP4

These limits are preliminary and may be adjusted after performance testing.

---

## 4. Functional Requirements

### FR-01: User Registration

**Priority:** Must Have

Users must be able to create an account with a unique username and password.

**Acceptance Criteria:**

- System validates required fields.
- Duplicate usernames are rejected.
- Passwords are never stored in plaintext.
- New accounts can log in successfully.
- Validation errors are displayed clearly.

### FR-02: User Login and Logout

**Priority:** Must Have

Users can authenticate and access their private workspace.

**Acceptance Criteria:**

- Valid credentials grant access.
- Invalid credentials are rejected.
- Unauthenticated users cannot access protected endpoints.
- Logout invalidates the active session.
- Users cannot access another user's records through modified file IDs.

### FR-03: Personal Data Management

**Priority:** Must Have

Users can create and retrieve structured personal information.

**Proposed fields:**

- Full name
- Email address
- Telephone number
- Residential address
- Date of birth
- Optional dummy identity number

**Acceptance Criteria:**

- Personal data is encrypted before persistent storage.
- Each record has encrypted AES, RC4, and DES representations.
- Only the record owner can retrieve and decrypt it.
- Users can update and delete their records.
- No sensitive plaintext values are written to application logs.

### FR-04: File Upload

**Priority:** Must Have

Users can upload supported images, documents, and video files.

**Acceptance Criteria:**

- File types and size limits are validated.
- Supported files are accepted.
- Unsupported or oversized files return clear errors.
- File content is encrypted before permanent storage.
- The system records upload status and basic metadata.
- Partial failures do not leave orphaned database records or incomplete encrypted files.

### FR-05: Encryption Engine

**Priority:** Must Have

Veltrix must provide three algorithm implementations through a consistent backend interface.

**Required operations:**

- Encrypt AES
- Decrypt AES
- Encrypt RC4
- Decrypt RC4
- Encrypt DES
- Decrypt DES

**Acceptance Criteria:**

- All algorithms accept binary data.
- Encryption and decryption preserve the original content.
- Block cipher implementations use non-ECB modes.
- Fresh cryptographic parameters are generated for each encryption.
- Encryption parameters required for decryption are saved securely as metadata.
- Ciphertext modification is detected before plaintext is released.

### FR-06: Encrypted Storage

**Priority:** Must Have

The application stores encrypted payloads and associates them with the correct user and source item.

**Acceptance Criteria:**

- Each successful upload produces three encrypted versions.
- The original plaintext is not stored in the persistent file repository.
- Files are stored outside any public web directory.
- Users cannot access encrypted objects belonging to other users.
- Application errors do not reveal cryptographic keys.

### FR-07: File Retrieval and Decryption

**Priority:** Must Have

Users can retrieve their original information or files after authentication.

**Proposed flow:**

1. User selects a stored file.
2. User selects AES, RC4, or DES as the decryption source.
3. Backend verifies ownership.
4. Backend retrieves the selected encrypted representation.
5. Backend validates ciphertext integrity.
6. Backend decrypts the ciphertext.
7. User downloads the restored file.

**Acceptance Criteria:**

- Decrypted bytes are identical to original bytes.
- Original filename and MIME information are restored.
- Download succeeds for all supported categories.
- Corrupted ciphertext produces a controlled error.
- Download authorization is checked on every request.

### FR-08: File Management

**Priority:** Should Have

Users can view and manage their stored items.

**Functions:**

- View uploaded items
- Filter by category
- View file upload date
- View encrypted file size
- Delete an item and its three ciphertext versions

### FR-09: Encryption Benchmarking

**Priority:** Must Have

Veltrix provides repeatable performance measurements for AES, RC4, and DES.

**Measured metrics:**

- Encryption execution time
- Decryption execution time
- Ciphertext size
- Storage overhead
- Round-trip correctness
- End-to-end download time

**Acceptance Criteria:**

- Each algorithm processes the same original test data.
- Multiple repetitions are supported.
- Benchmark records identify algorithm, file size, and repetition.
- Results can be displayed in a comparison table or chart.
- The system distinguishes cryptographic execution time from network transfer and filesystem I/O.
- Results can be exported as CSV for academic reporting.

### FR-10: Error Handling

**Priority:** Must Have

The application displays meaningful errors without exposing sensitive implementation details.

**Examples:**

- Wrong password
- Unauthorized request
- Unsupported file format
- File exceeds size limit
- Failed encryption
- Missing encrypted file
- Corrupted ciphertext
- Storage unavailable
- Network interruption

---

## 5. User Experience and Screens

### Brand Direction

The frontend follows `Veltrix Secure Brand Identity Board.png` and `VELTRIX_GSM_v0.1.md`: Midnight Blue (#0B132B), Royal Blue (#2563EB), Indigo (#6366F1), Cyan (#22D3EE), Cloud (#F1F5F9), and Charcoal (#1F2937). Montserrat is used for logo/headings and Inter for body/UI text. The tagline is “YOUR DATA. YOUR CONTROL.”. Web SVG assets are documented reconstructions of the supplied raster board, not original design masters. Demo and legacy-algorithm labeling remain part of the interface.

### Screen 01: Landing Page

Purpose: Introduce Veltrix and its functionality.

Components:

- Product logo and tagline
- Short product introduction
- Encryption technology overview
- Login and registration navigation

### Screen 02: Login and Registration

Purpose: Authenticate users.

Components:

- Username input
- Password input
- Registration action
- Login action
- Validation feedback

### Screen 03: Dashboard

Purpose: Provide an overview of stored information.

Components:

- Total number of stored items
- Personal data section
- Uploaded documents and images
- Uploaded video files
- Recent uploads
- Encryption summary
- Navigation to benchmarking

### Screen 04: Personal Data

Purpose: Manage structured private information.

Components:

- Personal data input form
- Save and update actions
- Encrypted status
- Authorized view/decrypt action
- Delete action

### Screen 05: File Vault

Purpose: Upload and retrieve files.

Components:

- File upload input or drag-and-drop area
- Supported format information
- File list
- File type and encrypted size
- Encryption processing status
- Decryption algorithm selector
- Download button
- Delete button

### Screen 06: Cryptography Lab

Purpose: Explain and compare algorithm behavior.

Components:

- AES / RC4 / DES algorithm overview
- Selected sample file
- Encryption/decryption timing table
- Ciphertext size comparison
- Limited hexadecimal ciphertext samples
- Benchmark repetition settings
- Run benchmark action
- Download results as CSV

**Note:** Hexadecimal ciphertext samples must never include secret keys or plaintext.

---

## 6. Main User Stories

**US-01 — Registration**

As a new user, I want to register with a username and password so that I can access my private workspace.

**US-02 — Personal Information**

As an authenticated user, I want to save personal information so that it can be stored in encrypted form.

**US-03 — File Upload**

As a user, I want to upload my documents, images, and videos so that they are encrypted and stored privately.

**US-04 — File Retrieval**

As a user, I want to download my original files after decryption so that I can use them without data corruption.

**US-05 — Algorithm Comparison**

As a student, I want to compare AES, RC4, and DES using identical inputs so that I can evaluate encryption characteristics.

**US-06 — Security Validation**

As a user, I want the system to prevent unauthorized access so that other users cannot retrieve my information.

---

## 7. Technical Architecture

### 7.1 Proposed Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python FastAPI |
| Database | MySQL, SQLAlchemy, PyMySQL, Alembic |
| Encrypted File Storage | Private local filesystem |
| Cryptography | PyCryptodome |
| Password Hashing | Argon2id |
| Benchmarking | Python perf_counter_ns |
| Testing | Pytest, API integration tests |
| Version Control | GitHub |

### 7.2 System Components

**Frontend Application**

Responsible for user interface, navigation, form validation, upload feedback, and result visualizations.

**Backend API**

Responsible for authentication, access control, business rules, and coordinating storage operations.

**Cryptography Engine**

Responsible for encryption, decryption, cryptographic parameter generation, and integrity validation.

**Database**

Stores user accounts, personal data ciphertext, encrypted object metadata, and benchmarking records.

**Encrypted File Storage**

Stores binary ciphertext with randomly assigned storage identifiers.

### 7.3 Encryption Flow

1. Receive an authenticated request.
2. Validate the input, ownership, file format, and size.
3. Read data into controlled server memory.
4. Generate independent encryption parameters for each algorithm.
5. Encrypt the same input using AES, RC4, and DES.
6. Generate ciphertext authentication tags.
7. Persist encrypted outputs and metadata.
8. Return a successful upload response.

The MVP does not intentionally persist plaintext upload copies.

### 7.4 Key Management

- Master secrets are loaded from protected runtime configuration.
- Keys are never committed to Git.
- Separate derived encryption keys are used across algorithms and encrypted objects.
- CBC IVs are generated randomly for each encryption.
- RC4 uses fresh per-item key derivation inputs.
- Authentication/MAC keys are separate from encryption keys.
- Key material is never returned to users or exposed in application logs.
- The design is server-side encryption, not zero-knowledge storage.

---

## 8. Proposed Database Design

### Table: users

- id (UUID, primary key)
- username (unique)
- password_hash
- created_at
- updated_at

The username and password hash are operational authentication records. Password hashes are not reversible ciphertext.

### Table: vault_items

- id (UUID, primary key)
- user_id (foreign key)
- item_type (personal_data / image / document / video)
- encrypted item metadata
- original_size_bytes
- created_at
- updated_at

### Table: encrypted_versions

- id (UUID, primary key)
- vault_item_id (foreign key)
- algorithm (AES / RC4 / DES)
- mode (CBC / STREAM)
- ciphertext_storage_reference or encrypted database payload
- encryption_parameters
- authentication_tag
- ciphertext_size_bytes
- encryption_time_ns
- created_at

### Table: benchmark_runs

- id
- user_id
- input_size_bytes
- input_category
- repetition_count
- environment_description
- created_at

### Table: benchmark_results

- id
- benchmark_run_id
- algorithm
- repetition_index
- encryption_time_ns
- decryption_time_ns
- download_time_ns
- ciphertext_size_bytes
- round_trip_success

**Data confidentiality:** Sensitive metadata such as filenames and personal profile contents must be encrypted. Non-sensitive operational identifiers may remain available for indexing and authorization.

---

## 9. Proposed API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /auth/register | Create account |
| POST | /auth/login | Authenticate user |
| POST | /auth/logout | End session |
| GET | /auth/me | Current user |
| POST | /vault/personal-data | Save encrypted information |
| GET | /vault/personal-data | Retrieve authorized information |
| PUT | /vault/personal-data/{id} | Update information |
| POST | /vault/files | Upload and encrypt file |
| GET | /vault/files | List user's files |
| GET | /vault/files/{id} | File metadata |
| GET | /vault/files/{id}/download | Decrypt and download selected version |
| DELETE | /vault/files/{id} | Delete all encrypted versions |
| POST | /benchmarks | Execute benchmark |
| GET | /benchmarks/{id} | Get benchmark results |
| GET | /benchmarks/{id}/export | Export CSV |

All relevant endpoints require authentication and resource-ownership validation. Benchmark input sizes and repetition counts must be bounded.

---

## 10. Non-Functional Requirements

### NFR-01: Security

- Use Argon2id for password hashing.
- Use secure, HttpOnly authentication cookies.
- Protect state-changing requests against CSRF.
- Enforce authorization checks on all private resources.
- Use secure random generation for keys, salts, and IVs.
- Prevent plaintext logging.
- Protect encryption secrets outside source control.
- Reject corrupted or unauthenticated ciphertext.
- Avoid public exposure of encrypted storage directories.

### NFR-02: Reliability

- Upload operations handle unexpected failure safely.
- Errors must not result in falsely marked successful uploads.
- File deletion removes all associated encrypted versions.
- Database and filesystem operations must be reconciled after interruptions.

### NFR-03: Performance

- Record cryptographic execution time with a high-resolution timer.
- Support repeated experiments.
- Limit memory consumption and concurrent uploads.
- Provide a visible loading/progress state.
- Do not make an unsupported fixed-speed performance guarantee before benchmarking.

### NFR-04: Data Privacy

- Use synthetic identity data for all demos.
- Define the categories of personal information being processed.
- Minimize collection of unnecessary personal data.
- Make retained information visible and deletable.
- Avoid transmitting test data to third-party analytics.
- Reference GDPR and Indonesia's UU PDP as relevant privacy frameworks, without claiming full legal compliance.

### NFR-05: Usability

- Responsive interface for desktop and mobile browsers.
- Clear navigation and simple data upload flow.
- Understandable encryption status.
- Helpful error messages and file limits.

---

## 11. Benchmark and Testing Plan

### 11.1 Experiment Dataset

Proposed dataset:

| Test | Data Type | Size |
|---|---|---|
| T01 | Personal text | 1 KB |
| T02 | Identity image | 500 KB |
| T03 | PDF | 2 MB |
| T04 | Spreadsheet/document | 5 MB |
| T05 | Video | 20 MB |

All test files must contain non-sensitive data.

### 11.2 Experimental Method

1. Prepare identical input data for all three algorithms.
2. Record the test machine and software environment.
3. Perform warm-up executions where appropriate.
4. Execute encryption and decryption repeatedly.
5. Perform at least 10 recorded repetitions per algorithm and dataset.
6. Record elapsed time and ciphertext size.
7. Verify that decrypted data exactly matches the original bytes.
8. Conduct repeated download tests separately.
9. Calculate summary statistics and generate charts.
10. Discuss measurement variability, overhead, and algorithm limitations.

### 11.3 Analysis Metrics

- Mean encryption time
- Median encryption time
- Standard deviation
- Mean decryption time
- End-to-end download duration
- Ciphertext byte length
- Storage expansion ratio
- Successful decryption rate

Ciphertext should also be examined qualitatively. Different ciphertext bytes alone do not establish that one algorithm is more secure than another.

### 11.4 Required Tests

**Functional Tests**

- Successful registration/login/logout
- Save personal data
- Upload supported file
- Encrypt with all algorithms
- Decrypt all encrypted versions
- Download restored file
- Delete item

**Security Tests**

- Reject invalid login
- Reject unauthorized user access
- Reject unsafe file uploads
- Reject tampered ciphertext
- Confirm plaintext and secrets are not exposed in logs

**Cryptography Tests**

- AES round-trip matches original bytes
- RC4 round-trip matches original bytes
- DES round-trip matches original bytes
- Empty and binary input handling
- Correct CBC padding behavior
- Valid IV/nonce handling
- Invalid authentication tag rejection

**Performance Tests**

- Different file sizes
- Different file categories
- Repeated runs under comparable conditions
- Benchmark CSV export

---

## 12. Team Responsibilities

**Member 1 — Frontend & UI/UX**

- Application layouts
- Authentication interfaces
- Vault dashboard
- File upload/download UI
- Benchmark visualization
- Frontend integration

**Member 2 — Backend & Database**

- FastAPI development
- User authentication
- Database design and migration
- Storage management
- Authorization
- API integration

**Member 3 — Cryptography**

- AES, RC4, and DES implementation
- CBC mode configuration
- Key/IV/nonce handling
- Encryption and decryption APIs
- Cryptographic unit testing
- Security review

**Member 4 — Benchmark, QA & Documentation**

- Experimental dataset
- Benchmarking implementation
- Automated integration tests
- Performance comparison
- Graphs and reporting
- Final technical documentation

All members participate in integration testing and final demonstration.

---

## 13. Definition of Done

The MVP is considered complete when:

- [ ] User registration and login work correctly.
- [ ] Each user can only access their own data.
- [ ] Personal information can be encrypted and retrieved.
- [ ] Images, documents, and videos can be uploaded.
- [ ] AES, RC4, and DES are all implemented.
- [ ] AES and DES do not use ECB mode.
- [ ] Three encrypted representations can be stored per item.
- [ ] Every encrypted representation can be decrypted successfully.
- [ ] Decrypted data is byte-identical to original input.
- [ ] Corrupted ciphertext is detected.
- [ ] No plaintext upload copy remains in persistent storage.
- [ ] Benchmarking runs multiple repetitions.
- [ ] Results include execution times and ciphertext analysis.
- [ ] Critical integration tests pass.
- [ ] A short analysis report is completed.
- [ ] Technical decisions are documented and justified.
- [ ] The application can be demonstrated end-to-end.

---

## 14. Risks and Mitigation

| Risk | Mitigation |
|---|---|
| Ambiguity about all algorithms | Confirm interpretation with lecturer |
| DES and RC4 are insecure | Academic-only use with dummy data |
| Storage grows approximately 3x | File limits and local storage quotas |
| Large files increase memory use | Bounded uploads and concurrency |
| Encryption/decryption implementation bugs | Known-answer tests and round-trip tests |
| Timing results fluctuate | Repeated experiments and controlled environment |
| Integration delays | Define API contracts and test fixtures early |
| Secret/key exposure | Runtime secrets, key separation, no sensitive logging |
| Unauthorized data access | Owner-scoped queries and authorization tests |

---

## 15. Pending Product Decisions

**D-01 — Encryption model:** Store three independent encrypted representations per item, or allow the user to select one encryption algorithm?

**D-02 — Product interface:** Storage-first dashboard, or security-learning dashboard with prominent algorithm experimentation?

**D-03 — File limits:** Is a 25 MB per-file limit adequate for the required video demonstration?

**D-04 — Technology stack:** Next.js + FastAPI + MySQL selected for the MVP. SQLAlchemy and PyMySQL connect the backend to MySQL.

**D-05 — Scope:** Should benchmarking be visible inside the app, or only executed by test scripts and presented in the final report?

**D-06 — Deployment:** Local development demonstration or publicly hosted application?

**D-07 — Academic constraints:** Confirm deadline, report format, expected experimental dataset, and any lecturer-specific implementation restrictions.

---

**PRD Status:** Version 0.1 — Ready for discussion, technical validation, and scope refinement.
