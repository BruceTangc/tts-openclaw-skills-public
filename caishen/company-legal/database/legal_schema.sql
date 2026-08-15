-- Company Legal 数据库 schema v7.1

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,                          -- 销售/采购/服务/NDA/股东协议等
    party_a TEXT,
    party_b TEXT,
    amount REAL,
    currency TEXT DEFAULT 'CNY',
    sign_date DATE,
    expire_date DATE,
    status TEXT DEFAULT 'draft',        -- draft / reviewing / signed / expired / terminated
    version TEXT DEFAULT '1.0',
    risk_score INTEGER,
    risk_level TEXT,                    -- Low / Medium / High / Critical
    file_path TEXT,
    reviewer TEXT,
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER,
    category TEXT,                      -- payment / ip / liability / confidentiality ...
    content TEXT,
    risk TEXT,                          -- low / medium / high
    is_standard INTEGER DEFAULT 0,      -- 是否来自条款库
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

CREATE TABLE IF NOT EXISTS legal_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,                          -- 营业执照 / 章程 / 授权书 / 判决书 等
    location TEXT,
    related_contract_id INTEGER,
    created DATE,
    note TEXT
);

CREATE TABLE IF NOT EXISTS review_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER,
    score INTEGER,
    level TEXT,
    summary TEXT,
    reviewer TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);
