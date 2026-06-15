PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS record_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS test_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_item_code TEXT NOT NULL UNIQUE,
    test_item_name TEXT,
    description TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS instrument_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_alias TEXT NOT NULL UNIQUE,
    instrument_type TEXT,
    protocol TEXT,
    payload_format TEXT,
    proxy_host TEXT,
    proxy_port INTEGER,
    real_host TEXT,
    real_port INTEGER,
    visa_resource TEXT,
    enabled INTEGER DEFAULT 1,
    config_json TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS interaction_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    process_station TEXT,
    product_code TEXT,
    tu_name TEXT,
    profile_name TEXT NOT NULL,
    test_item_code TEXT,
    instrument_alias TEXT NOT NULL,
    instrument_type TEXT,
    protocol TEXT,
    payload_format TEXT,
    variant_name TEXT DEFAULT 'normal',
    replay_strategy TEXT DEFAULT 'BY_CALL_INDEX',
    request_text TEXT,
    normalized_request TEXT,
    request_hex TEXT,
    request_hash TEXT,
    response_text TEXT,
    normalized_response TEXT,
    response_hex TEXT,
    response_hash TEXT,
    request_bytes BLOB,
    response_bytes BLOB,
    call_index INTEGER DEFAULT 1,
    timeout_ms INTEGER DEFAULT 0,
    delay_ms INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,
    error_type TEXT,
    error_message TEXT,
    source TEXT DEFAULT 'RECORDED',
    remark TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS stream_frame (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interaction_id INTEGER,
    product_name TEXT,
    process_station TEXT,
    product_code TEXT,
    tu_name TEXT,
    profile_name TEXT,
    test_item_code TEXT,
    instrument_alias TEXT NOT NULL,
    direction TEXT NOT NULL,
    protocol TEXT,
    payload_format TEXT,
    data_text TEXT,
    data_hex TEXT,
    data_blob BLOB,
    data_length INTEGER,
    timestamp TEXT,
    FOREIGN KEY(interaction_id) REFERENCES interaction_record(id)
);

CREATE INDEX IF NOT EXISTS idx_interaction_replay_hash
ON interaction_record(profile_name, test_item_code, instrument_alias, request_hash, call_index);

CREATE INDEX IF NOT EXISTS idx_interaction_scene_hash
ON interaction_record(product_name, process_station, product_code, tu_name, instrument_alias, request_hash, call_index);

CREATE INDEX IF NOT EXISTS idx_interaction_scene_no_tu
ON interaction_record(product_name, process_station, product_code, instrument_alias, request_hash);

CREATE INDEX IF NOT EXISTS idx_interaction_no_item
ON interaction_record(profile_name, instrument_alias, request_hash);

CREATE INDEX IF NOT EXISTS idx_interaction_variant
ON interaction_record(profile_name, test_item_code, instrument_alias, request_hash, variant_name);

CREATE INDEX IF NOT EXISTS idx_interaction_item
ON interaction_record(test_item_code, instrument_alias);
