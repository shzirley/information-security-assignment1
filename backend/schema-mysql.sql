-- Reference only. Initialize with python manage.py migrate (also configures lock/key state).


CREATE TABLE kyc_key_state (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	kek_fingerprint VARCHAR(64) NOT NULL, 
	auth_fingerprint VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE kyc_rate_limits (
	bucket VARCHAR(64) NOT NULL, 
	`window` FLOAT NOT NULL, 
	count INTEGER NOT NULL, 
	PRIMARY KEY (bucket)
)

;


CREATE TABLE kyc_users (
	id VARCHAR(36) NOT NULL, 
	username VARCHAR(24) COLLATE utf8mb4_bin NOT NULL, 
	display_name VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(16) NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_role CHECK (role IN ('applicant','reviewer','admin','evaluator')), 
	UNIQUE (username)
)

;


CREATE TABLE lab_lock (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	owner VARCHAR(36), 
	expires_at FLOAT NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE security_events (
	id VARCHAR(36) NOT NULL, 
	at VARCHAR(40) NOT NULL, 
	actor_id VARCHAR(36), 
	action VARCHAR(40) NOT NULL, 
	resource_id VARCHAR(36), 
	PRIMARY KEY (id)
)

;


CREATE TABLE applications (
	id VARCHAR(36) NOT NULL, 
	reference VARCHAR(40) NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	version INTEGER NOT NULL, 
	synthetic_acknowledged BOOL NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	updated_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_status CHECK (status IN ('DRAFT','SUBMITTED','UNDER_REVIEW','NEEDS_REVISION','RESUBMITTED','ACCEPTED_DEMO','REJECTED_DEMO','WITHDRAWN')), 
	CONSTRAINT positive_case_version CHECK (version >= 1), 
	UNIQUE (reference), 
	FOREIGN KEY(owner_id) REFERENCES kyc_users (id)
)

;

CREATE INDEX ix_case_owner_updated ON applications (owner_id, updated_at);

CREATE INDEX ix_case_status_updated ON applications (status, updated_at);


CREATE TABLE kyc_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	created_at FLOAT NOT NULL, 
	expires_at FLOAT NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES kyc_users (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_kyc_sessions_expires_at ON kyc_sessions (expires_at);

CREATE INDEX ix_kyc_sessions_user_id ON kyc_sessions (user_id);


CREATE TABLE lab_runs (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	result LONGTEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES kyc_users (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_lab_runs_user_id ON lab_runs (user_id);


CREATE TABLE encrypted_objects (
	id VARCHAR(36) NOT NULL, 
	application_id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	category VARCHAR(16) NOT NULL, 
	payload_version INTEGER NOT NULL, 
	key_version INTEGER NOT NULL, 
	header TEXT NOT NULL, 
	ciphertext LONGBLOB NOT NULL, 
	wrapped_keys BLOB(72) NOT NULL, 
	wrap_nonce BINARY(12) NOT NULL, 
	wrap_tag BLOB(16) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_wrap_nonce UNIQUE (key_version, wrap_nonce), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(owner_id) REFERENCES kyc_users (id)
)

;

CREATE INDEX ix_encrypted_objects_application_id ON encrypted_objects (application_id);


CREATE TABLE reviewer_assignments (
	application_id VARCHAR(36) NOT NULL, 
	reviewer_id VARCHAR(36) NOT NULL, 
	assigned_by VARCHAR(36) NOT NULL, 
	assigned_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (application_id), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(reviewer_id) REFERENCES kyc_users (id), 
	FOREIGN KEY(assigned_by) REFERENCES kyc_users (id)
)

;

CREATE INDEX ix_reviewer_assignments_reviewer_id ON reviewer_assignments (reviewer_id);


CREATE TABLE case_events (
	id VARCHAR(36) NOT NULL, 
	application_id VARCHAR(36) NOT NULL, 
	actor_id VARCHAR(36) NOT NULL, 
	actor_role VARCHAR(16) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	at VARCHAR(40) NOT NULL, 
	case_version INTEGER NOT NULL, 
	note_object_id VARCHAR(36), 
	PRIMARY KEY (id), 
	CONSTRAINT unique_case_event_version UNIQUE (application_id, case_version), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_id) REFERENCES kyc_users (id), 
	FOREIGN KEY(note_object_id) REFERENCES encrypted_objects (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_case_events_application_id ON case_events (application_id);


CREATE TABLE evidence_versions (
	id VARCHAR(36) NOT NULL, 
	application_id VARCHAR(36) NOT NULL, 
	category VARCHAR(16) NOT NULL, 
	version INTEGER NOT NULL, 
	object_id VARCHAR(36) NOT NULL, 
	original_bytes INTEGER NOT NULL, 
	mime_type VARCHAR(100) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_category CHECK (category IN ('identity','document','video')), 
	CONSTRAINT unique_evidence_version UNIQUE (application_id, category, version), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	UNIQUE (object_id), 
	FOREIGN KEY(object_id) REFERENCES encrypted_objects (id) ON DELETE CASCADE
)

;


CREATE TABLE personal_data_versions (
	id VARCHAR(36) NOT NULL, 
	application_id VARCHAR(36) NOT NULL, 
	version INTEGER NOT NULL, 
	object_id VARCHAR(36) NOT NULL, 
	created_at VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_profile_version UNIQUE (application_id, version), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	UNIQUE (object_id), 
	FOREIGN KEY(object_id) REFERENCES encrypted_objects (id) ON DELETE CASCADE
)

;