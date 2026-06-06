-- AI Fiction Studio database schema
-- Generated from backend/aifiction.db with: sqlite3 backend/aifiction.db .schema
-- This file contains schema only. It does not contain project, chapter, provider, user, or task data.

PRAGMA foreign_keys = ON;

CREATE TABLE users (
	email VARCHAR(255) NOT NULL,
	username VARCHAR(100) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	is_active BOOLEAN,
	last_login_at DATETIME,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (username)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE llm_providers (
	name VARCHAR(100) NOT NULL,
	provider_type VARCHAR(30) NOT NULL,
	api_key VARCHAR(500) NOT NULL,
	model VARCHAR(100) NOT NULL,
	base_url VARCHAR(500) NOT NULL,
	is_active BOOLEAN,
	sort_order INTEGER,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE projects (
	user_id VARCHAR(36) NOT NULL,
	title VARCHAR(200) NOT NULL,
	genre VARCHAR(50) NOT NULL,
	target_length VARCHAR(20),
	target_total_words INTEGER,
	word_count_breakdown JSON,
	story_brief VARCHAR(2000),
	writing_style JSON,
	core_theme VARCHAR(200),
	secondary_themes JSON,
	motifs JSON,
	narrative_lines JSON,
	wizard_step INTEGER,
	status VARCHAR(20),
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	planning_memory JSON,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_projects_user_id ON projects (user_id);

CREATE TABLE writing_style_skills (
	user_id VARCHAR(36) NOT NULL,
	name VARCHAR(120) NOT NULL,
	description VARCHAR(1000),
	source_type VARCHAR(30),
	source_note VARCHAR(500),
	sample_word_count INTEGER,
	style_profile JSON,
	prompt_fragment VARCHAR(4000),
	is_public BOOLEAN,
	is_active BOOLEAN,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_writing_style_skills_user_id ON writing_style_skills (user_id);

CREATE TABLE volumes (
	project_id VARCHAR(36) NOT NULL,
	volume_number INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	subtitle VARCHAR(200),
	summary VARCHAR(2000),
	outline VARCHAR(3000),
	theme VARCHAR(500),
	target_words INTEGER,
	default_chapter_words INTEGER,
	chapter_count INTEGER,
	tension_curve JSON,
	emotional_arc_description VARCHAR(500),
	chapter_range_start INTEGER NOT NULL,
	chapter_range_end INTEGER NOT NULL,
	narrative_line_distribution JSON,
	narrative_arcs JSON,
	sort_order INTEGER,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_project_volume UNIQUE (project_id, volume_number),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_volumes_project_id ON volumes (project_id);

CREATE TABLE factions (
	project_id VARCHAR(36) NOT NULL,
	name VARCHAR(200) NOT NULL,
	faction_type VARCHAR(30) NOT NULL,
	description VARCHAR(2000),
	headquarters VARCHAR(500),
	territory VARCHAR(1000),
	core_creed VARCHAR(1000),
	hierarchy JSON,
	notable_members JSON,
	faction_timeline JSON,
	emblem_description VARCHAR(1000),
	color_scheme VARCHAR(200),
	core_conflict_of_interest VARCHAR(2000),
	internal_faction_cracks VARCHAR(1000),
	reputation_and_reality VARCHAR(1000),
	strength_trajectory VARCHAR(500),
	sort_order INTEGER,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_factions_project_id ON factions (project_id);

CREATE TABLE outlines (
	project_id VARCHAR(36) NOT NULL,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (project_id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE world_settings (
	project_id VARCHAR(36) NOT NULL,
	geography JSON,
	social_structure JSON,
	power_system JSON,
	history JSON,
	culture JSON,
	special_rules JSON,
	world_logic JSON,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	hard_rules JSON,
	tone_rules JSON,
	constraints JSON,
	PRIMARY KEY (id),
	UNIQUE (project_id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE characters (
	project_id VARCHAR(36) NOT NULL,
	name VARCHAR(100) NOT NULL,
	role_type VARCHAR(30),
	personality VARCHAR(1000),
	background VARCHAR(2000),
	motivation VARCHAR(1000),
	behavior_pattern VARCHAR(1000),
	language_style VARCHAR(500),
	emotional_expression VARCHAR(500),
	appearance VARCHAR(1000),
	primary_faction_id VARCHAR(36),
	faction_rank VARCHAR(100),
	inner_conflict VARCHAR(1000),
	language_fingerprint VARCHAR(1000),
	relationship_dynamics JSON,
	faction_history JSON,
	growth_arc VARCHAR(2000),
	growth_arc_preset VARCHAR(2000),
	growth_stages JSON,
	relationships JSON,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	current_state JSON,
	first_appeared_chapter INTEGER,
	first_appeared_title VARCHAR(200),
	character_class VARCHAR(20),
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(primary_faction_id) REFERENCES factions (id) ON DELETE CASCADE
);

CREATE INDEX ix_characters_project_id ON characters (project_id);

CREATE TABLE faction_relations (
	project_id VARCHAR(36) NOT NULL,
	faction_a_id VARCHAR(36) NOT NULL,
	faction_b_id VARCHAR(36) NOT NULL,
	relation_type VARCHAR(30) NOT NULL,
	timeline_changes JSON,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(faction_a_id) REFERENCES factions (id) ON DELETE CASCADE,
	FOREIGN KEY(faction_b_id) REFERENCES factions (id) ON DELETE CASCADE
);

CREATE TABLE outline_nodes (
	outline_id VARCHAR(36) NOT NULL,
	volume_id VARCHAR(36) NOT NULL,
	parent_id VARCHAR(36),
	chapter_number INTEGER NOT NULL,
	volume_chapter_number INTEGER NOT NULL,
	title VARCHAR(300),
	summary VARCHAR(2000),
	key_events JSON,
	tension_level INTEGER,
	target_words INTEGER,
	narrative_line VARCHAR(50),
	featured_character_ids JSON,
	featured_faction_ids JSON,
	featured_location_ids JSON,
	emotional_arc VARCHAR(1000),
	is_key_chapter BOOLEAN,
	sort_order INTEGER,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(outline_id) REFERENCES outlines (id) ON DELETE CASCADE,
	FOREIGN KEY(volume_id) REFERENCES volumes (id) ON DELETE CASCADE,
	FOREIGN KEY(parent_id) REFERENCES outline_nodes (id) ON DELETE CASCADE
);

CREATE INDEX ix_outline_nodes_volume_id ON outline_nodes (volume_id);

CREATE TABLE foreshadowing_plans (
	project_id VARCHAR(36) NOT NULL,
	outline_node_id VARCHAR(36),
	name VARCHAR(300) NOT NULL,
	description VARCHAR(2000),
	plant_stage VARCHAR(500),
	reveal_stage VARCHAR(500),
	plant_chapter INTEGER,
	reveal_chapter INTEGER,
	status VARCHAR(20),
	parent_id VARCHAR(36),
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(outline_node_id) REFERENCES outline_nodes (id) ON DELETE CASCADE,
	FOREIGN KEY(parent_id) REFERENCES foreshadowing_plans (id) ON DELETE CASCADE
);

CREATE TABLE chapters (
	project_id VARCHAR(36) NOT NULL,
	outline_node_id VARCHAR(36),
	volume_id VARCHAR(36),
	chapter_number INTEGER NOT NULL,
	title VARCHAR(300),
	summary VARCHAR(2000),
	arc_name VARCHAR(100),
	connects_from VARCHAR(500),
	connects_to VARCHAR(500),
	hook VARCHAR(500),
	story_state_snapshot VARCHAR(3000),
	characters_in_chapter JSON,
	key_events JSON,
	minor_events JSON,
	scene_count INTEGER,
	content VARCHAR,
	word_count INTEGER,
	target_words INTEGER,
	status VARCHAR(20),
	narrative_line VARCHAR(50),
	quality_score INTEGER,
	tension_actual INTEGER,
	version INTEGER,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	blueprint JSON,
	continuity_checks JSON,
	causality_links JSON,
	foreshadowing_tasks JSON,
	rhythm_profile JSON,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(outline_node_id) REFERENCES outline_nodes (id) ON DELETE CASCADE,
	FOREIGN KEY(volume_id) REFERENCES volumes (id) ON DELETE CASCADE
);

CREATE INDEX ix_chapters_volume_id ON chapters (volume_id);
CREATE INDEX ix_chapters_project_id ON chapters (project_id);

CREATE TABLE character_state_snapshots (
	character_id VARCHAR(36) NOT NULL,
	project_id VARCHAR(36) NOT NULL,
	volume_id VARCHAR(36),
	chapter_id VARCHAR(36),
	chapter_number INTEGER NOT NULL,
	snapshot_label VARCHAR(200),
	position VARCHAR(500),
	ability_level VARCHAR(100),
	mental_state VARCHAR(500),
	physical_state VARCHAR(200),
	faction_id VARCHAR(36),
	faction_rank VARCHAR(100),
	important_items JSON,
	notes VARCHAR(1000),
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(character_id) REFERENCES characters (id) ON DELETE CASCADE,
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(volume_id) REFERENCES volumes (id) ON DELETE CASCADE,
	FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE,
	FOREIGN KEY(faction_id) REFERENCES factions (id) ON DELETE CASCADE
);

CREATE INDEX ix_character_state_snapshots_character_id ON character_state_snapshots (character_id);

CREATE TABLE generation_tasks (
	project_id VARCHAR(36) NOT NULL,
	chapter_id VARCHAR(36),
	task_type VARCHAR(50) NOT NULL,
	status VARCHAR(20),
	progress INTEGER,
	precision_config JSON,
	result_summary JSON,
	error_message VARCHAR,
	celery_task_id VARCHAR,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
);

CREATE TABLE relationship_events (
	project_id VARCHAR(36) NOT NULL,
	character_a_id VARCHAR(36) NOT NULL,
	character_b_id VARCHAR(36) NOT NULL,
	chapter_id VARCHAR(36),
	chapter_number INTEGER NOT NULL,
	old_relation VARCHAR(200) NOT NULL,
	new_relation VARCHAR(200) NOT NULL,
	trigger_event VARCHAR(1000) NOT NULL,
	description VARCHAR(2000),
	relation_type VARCHAR(50),
	intensity INTEGER,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(character_a_id) REFERENCES characters (id) ON DELETE CASCADE,
	FOREIGN KEY(character_b_id) REFERENCES characters (id) ON DELETE CASCADE,
	FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
);

CREATE TABLE timeline_events (
	project_id VARCHAR(36) NOT NULL,
	chapter_id VARCHAR(36),
	narrative_line VARCHAR(50),
	time_point VARCHAR(200) NOT NULL,
	absolute_day INTEGER,
	description VARCHAR(2000) NOT NULL,
	related_character_ids JSON,
	related_faction_ids JSON,
	related_location_ids JSON,
	is_major_event BOOLEAN,
	event_type VARCHAR(50),
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
);

CREATE TABLE story_state_trails (
	project_id VARCHAR(36) NOT NULL,
	chapter_id VARCHAR(36),
	chapter_number INTEGER NOT NULL,
	state_snapshot JSON,
	change_description VARCHAR(2000),
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
);

CREATE TABLE chapter_versions (
	project_id VARCHAR(36) NOT NULL,
	chapter_id VARCHAR(36) NOT NULL,
	version_number INTEGER NOT NULL,
	title VARCHAR(300),
	content VARCHAR,
	word_count INTEGER,
	source VARCHAR(50),
	note VARCHAR(500),
	generation_config JSON,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
	FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
);

CREATE INDEX ix_chapter_versions_project_id ON chapter_versions (project_id);
CREATE INDEX ix_chapter_versions_chapter_id ON chapter_versions (chapter_id);

CREATE TABLE project_plan_sessions (
	user_id VARCHAR(36) NOT NULL,
	messages JSON,
	selected_genres JSON,
	chat_input VARCHAR,
	current_draft JSON,
	suggestions JSON,
	selected_suggestion_index INTEGER,
	next_questions JSON,
	detail_options JSON,
	id VARCHAR(36) NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_project_plan_session_user UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_plan_sessions_user_id ON project_plan_sessions (user_id);
