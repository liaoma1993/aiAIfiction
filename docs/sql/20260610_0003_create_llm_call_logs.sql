-- 20260610_0003_create_llm_call_logs.sql
-- Purpose: create the LLM execution log table used to audit model calls.
-- Safe to run multiple times on SQLite / PostgreSQL-style databases that support IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS llm_call_logs (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NULL,
    project_name VARCHAR(200) NOT NULL DEFAULT '',
    task_id VARCHAR(36) NOT NULL DEFAULT '',
    function_name VARCHAR(100) NOT NULL DEFAULT '',
    provider_id VARCHAR(36) NOT NULL DEFAULT '',
    provider_name VARCHAR(100) NOT NULL DEFAULT '',
    provider_type VARCHAR(30) NOT NULL DEFAULT '',
    model_name VARCHAR(120) NOT NULL DEFAULT '',
    request_type VARCHAR(30) NOT NULL DEFAULT 'chat',
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    system_prompt TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    response_content TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    temperature VARCHAR(20) NOT NULL DEFAULT '',
    max_tokens INTEGER NOT NULL DEFAULT 0,
    request_payload JSON,
    response_metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_llm_call_logs_project_id ON llm_call_logs (project_id);
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_project_name ON llm_call_logs (project_name);
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_task_id ON llm_call_logs (task_id);
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_function_name ON llm_call_logs (function_name);
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_model_name ON llm_call_logs (model_name);
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_status ON llm_call_logs (status);
CREATE INDEX IF NOT EXISTS ix_llm_call_logs_created_at ON llm_call_logs (created_at);
