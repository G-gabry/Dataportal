-- Data Portal Database Schema
-- Version: 1.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ENUMS
CREATE TYPE source_type AS ENUM (
    'UNIVERSITY', 'SCHOLARSHIP_ORG', 'CONFERENCE_ORG', 'EXCHANGE_ORG', 'OTHER'
);

CREATE TYPE item_type AS ENUM (
    'PROGRAM', 'SCHOLARSHIP', 'CONFERENCE', 'EXCHANGE'
);

CREATE TYPE url_status AS ENUM (
    'DISCOVERED', 'CLASSIFIED', 'SCRAPED', 'EXTRACTED', 'SKIPPED', 'ERROR'
);

CREATE TYPE relevance_status AS ENUM (
    'PENDING', 'RELEVANT', 'NOT_RELEVANT'
);

CREATE TYPE priority_level AS ENUM (
    'HIGH', 'MEDIUM', 'LOW'
);

CREATE TYPE item_status AS ENUM (
    'DRAFT', 'NEEDS_REVIEW', 'VERIFIED', 'PUBLISHED', 'OUTDATED', 'ARCHIVED'
);

CREATE TYPE job_status AS ENUM (
    'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
);

CREATE TYPE user_role AS ENUM (
    'ADMIN', 'EDITOR', 'VIEWER'
);

-- TABLES

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role user_role DEFAULT 'EDITOR',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sources table (universities, organizations, etc.)
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type source_type NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    target_item_types item_type[] NOT NULL,

    -- Scraping config
    scrape_frequency VARCHAR(50) DEFAULT 'MONTHLY',
    is_important BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- URL filtering patterns
    include_patterns TEXT[] DEFAULT '{}',
    exclude_patterns TEXT[] DEFAULT '{}',

    -- Status
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    urls_discovered_count INTEGER DEFAULT 0,
    items_extracted_count INTEGER DEFAULT 0,

    -- Flexible extra data
    extra_data JSONB DEFAULT '{}',
    notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Discovered URLs table
CREATE TABLE discovered_urls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,

    url VARCHAR(2000) NOT NULL,
    url_path VARCHAR(1000),

    -- Classification Layer 1 (relevant or not)
    relevance relevance_status DEFAULT 'PENDING',
    relevance_score DECIMAL(5,2),
    relevance_reason TEXT,

    -- Classification Layer 2 (detailed classification for relevant URLs)
    page_type VARCHAR(100),
    detected_item_types item_type[],
    content_tags TEXT[],
    priority priority_level DEFAULT 'MEDIUM',
    has_multiple_items BOOLEAN DEFAULT false,

    -- Content
    raw_markdown TEXT,
    content_hash VARCHAR(64),

    -- Status tracking
    status url_status DEFAULT 'DISCOVERED',
    error_message TEXT,

    -- Human review
    human_verified BOOLEAN DEFAULT false,
    human_notes TEXT,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_scraped_at TIMESTAMP WITH TIME ZONE,
    last_classified_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(source_id, url)
);

-- Items table (extracted data)
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    discovered_url_id UUID REFERENCES discovered_urls(id) ON DELETE SET NULL,

    item_type item_type NOT NULL,

    -- The extracted data (schema varies by item_type)
    data JSONB NOT NULL DEFAULT '{}',

    -- Field-level status tracking
    field_status JSONB DEFAULT '{}',

    -- Custom fields added by humans
    custom_fields JSONB DEFAULT '{}',
    notes TEXT,
    admin_notes TEXT,
    tags TEXT[],

    -- Quality
    extraction_confidence DECIMAL(5,2),
    status item_status DEFAULT 'DRAFT',

    -- Human review
    human_edited BOOLEAN DEFAULT false,
    human_verified BOOLEAN DEFAULT false,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Item schemas table (defines extraction schema per item type)
CREATE TABLE item_schemas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_type item_type UNIQUE NOT NULL,

    -- Schema definition
    schema_json JSONB NOT NULL,

    -- AI prompts
    classification_prompt TEXT,
    extraction_prompt TEXT,

    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Scrape jobs table
CREATE TABLE scrape_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,

    job_type VARCHAR(50) NOT NULL,
    status job_status DEFAULT 'PENDING',

    -- Progress tracking
    current_step VARCHAR(100),
    progress_percent INTEGER DEFAULT 0,

    -- Stats
    urls_discovered INTEGER DEFAULT 0,
    urls_relevant INTEGER DEFAULT 0,
    urls_scraped INTEGER DEFAULT 0,
    items_extracted INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,

    -- Cost tracking
    ai_tokens_used INTEGER DEFAULT 0,
    ai_cost_usd DECIMAL(10,4) DEFAULT 0,
    firecrawl_calls INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Errors
    error_log TEXT,

    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI logs table
CREATE TABLE ai_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    task_type VARCHAR(50) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,

    -- Related entity
    related_type VARCHAR(50),
    related_id UUID,
    job_id UUID REFERENCES scrape_jobs(id) ON DELETE SET NULL,

    -- Usage
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10,6),
    latency_ms INTEGER,

    -- Content (truncated for reference)
    input_preview TEXT,
    output_json JSONB,
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Settings table (for app configuration)
CREATE TABLE settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- INDEXES

-- Sources indexes
CREATE INDEX idx_sources_type ON sources(type);
CREATE INDEX idx_sources_active ON sources(is_active);
CREATE INDEX idx_sources_important ON sources(is_important);

-- Discovered URLs indexes
CREATE INDEX idx_urls_source ON discovered_urls(source_id);
CREATE INDEX idx_urls_relevance ON discovered_urls(relevance);
CREATE INDEX idx_urls_status ON discovered_urls(status);
CREATE INDEX idx_urls_priority ON discovered_urls(priority);
CREATE INDEX idx_urls_page_type ON discovered_urls(page_type);

-- Items indexes
CREATE INDEX idx_items_source ON items(source_id);
CREATE INDEX idx_items_type ON items(item_type);
CREATE INDEX idx_items_status ON items(status);
CREATE INDEX idx_items_data ON items USING GIN(data);
CREATE INDEX idx_items_tags ON items USING GIN(tags);

-- Jobs indexes
CREATE INDEX idx_jobs_source ON scrape_jobs(source_id);
CREATE INDEX idx_jobs_status ON scrape_jobs(status);
CREATE INDEX idx_jobs_created ON scrape_jobs(created_at DESC);

-- AI logs indexes
CREATE INDEX idx_ai_logs_job ON ai_logs(job_id);
CREATE INDEX idx_ai_logs_task ON ai_logs(task_type);
CREATE INDEX idx_ai_logs_created ON ai_logs(created_at DESC);

-- TRIGGERS

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_item_schemas_updated_at BEFORE UPDATE ON item_schemas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- INSERT DEFAULT DATA

-- Default admin user (password: admin123)
INSERT INTO users (email, password_hash, name, role) VALUES
('admin@dataportal.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYz0vpBKGKHi', 'Admin User', 'ADMIN');

-- Default AI settings
INSERT INTO settings (key, value, description) VALUES
('ai_config', '{
    "default_provider": "anthropic",
    "default_model": "claude-3-5-haiku-20241022",
    "providers": {
        "anthropic": {
            "models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
            "default_model": "claude-3-5-haiku-20241022"
        },
        "gemini": {
            "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "default_model": "gemini-1.5-flash"
        },
        "openai": {
            "models": ["gpt-4o-mini", "gpt-4o"],
            "default_model": "gpt-4o-mini"
        }
    },
    "task_config": {
        "url_classification": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "batch_size": 50},
        "content_classification": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
        "extraction": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"}
    }
}', 'AI provider configuration'),
('scraping_config', '{
    "default_exclude_patterns": [
        "/news/", "/blog/", "/events/", "/faculty/", "/staff/",
        "/about-us/", "/contact/", "/privacy/", "/terms/",
        "/login/", "/careers/", "/jobs/", "/sitemap",
        ".pdf$", ".jpg$", ".png$", ".gif$", ".css$", ".js$"
    ],
    "max_urls_per_source": 1000,
    "scrape_delay_ms": 1000
}', 'Scraping configuration');

-- Default item schemas
INSERT INTO item_schemas (item_type, schema_json, classification_prompt, extraction_prompt) VALUES
('PROGRAM', '{
    "fields": {
        "program_name": {"type": "string", "required": true, "description": "Name of the program"},
        "degree_type": {"type": "enum", "options": ["BSC", "MSC", "PHD", "CERTIFICATE", "DIPLOMA"], "description": "Type of degree"},
        "field": {"type": "string", "description": "Field of study"},
        "field_category": {"type": "enum", "options": ["STEM", "BUSINESS", "ARTS", "MEDICINE", "LAW", "SOCIAL_SCIENCES", "OTHER"]},
        "university_name": {"type": "string", "description": "Name of the university"},
        "department": {"type": "string"},
        "country": {"type": "string"},
        "city": {"type": "string"},
        "duration_months": {"type": "number"},
        "format": {"type": "enum", "options": ["FULL_TIME", "PART_TIME", "ONLINE", "HYBRID"]},
        "language": {"type": "string"},
        "gpa_requirement": {"type": "number", "description": "Minimum GPA on 4.0 scale"},
        "gre_required": {"type": "boolean"},
        "gre_minimum": {"type": "number"},
        "toefl_minimum": {"type": "number"},
        "ielts_minimum": {"type": "number"},
        "other_requirements": {"type": "array", "items": "string"},
        "tuition_total_usd": {"type": "number"},
        "tuition_per_year_usd": {"type": "number"},
        "application_fee_usd": {"type": "number"},
        "has_funding": {"type": "boolean"},
        "funding_details": {"type": "string"},
        "fall_deadline": {"type": "date"},
        "spring_deadline": {"type": "date"},
        "rolling_admission": {"type": "boolean"},
        "application_url": {"type": "url"},
        "program_url": {"type": "url"},
        "description": {"type": "text"}
    }
}',
'Determine if this URL is about an academic program (MSc, PhD, BSc, etc.). Look for keywords like admission, program, degree, master, doctoral, graduate, curriculum, requirements.',
'Extract all program information from this page. For each field, extract the value if available, use "N/A" if explicitly not applicable, or "UNKNOWN" if the information is not found on the page.'),

('SCHOLARSHIP', '{
    "fields": {
        "scholarship_name": {"type": "string", "required": true},
        "provider": {"type": "string", "description": "Organization providing the scholarship"},
        "provider_type": {"type": "enum", "options": ["GOVERNMENT", "UNIVERSITY", "PRIVATE", "NGO", "OTHER"]},
        "eligible_countries": {"type": "array", "items": "string"},
        "eligible_fields": {"type": "array", "items": "string"},
        "eligible_degree_levels": {"type": "array", "items": "string"},
        "gpa_minimum": {"type": "number"},
        "age_limit": {"type": "number"},
        "other_eligibility": {"type": "array", "items": "string"},
        "covers_tuition": {"type": "boolean"},
        "tuition_percentage": {"type": "number"},
        "monthly_stipend_usd": {"type": "number"},
        "travel_allowance": {"type": "boolean"},
        "health_insurance": {"type": "boolean"},
        "other_benefits": {"type": "array", "items": "string"},
        "funding_amount_usd": {"type": "number"},
        "duration_months": {"type": "number"},
        "is_renewable": {"type": "boolean"},
        "deadline": {"type": "date"},
        "application_url": {"type": "url"},
        "documents_required": {"type": "array", "items": "string"},
        "has_interview": {"type": "boolean"},
        "host_countries": {"type": "array", "items": "string"},
        "host_universities": {"type": "array", "items": "string"},
        "description": {"type": "text"}
    }
}',
'Determine if this URL is about a scholarship, fellowship, grant, or funding opportunity for students. Look for keywords like scholarship, fellowship, grant, funding, financial aid, award.',
'Extract all scholarship information from this page. Include eligibility criteria, benefits, deadlines, and application requirements.'),

('CONFERENCE', '{
    "fields": {
        "conference_name": {"type": "string", "required": true},
        "acronym": {"type": "string"},
        "edition": {"type": "string"},
        "field": {"type": "string"},
        "field_category": {"type": "enum", "options": ["STEM", "BUSINESS", "ARTS", "MEDICINE", "LAW", "SOCIAL_SCIENCES", "OTHER"]},
        "topics": {"type": "array", "items": "string"},
        "start_date": {"type": "date"},
        "end_date": {"type": "date"},
        "submission_deadline": {"type": "date"},
        "notification_date": {"type": "date"},
        "camera_ready_deadline": {"type": "date"},
        "venue": {"type": "string"},
        "city": {"type": "string"},
        "country": {"type": "string"},
        "is_virtual": {"type": "boolean"},
        "is_hybrid": {"type": "boolean"},
        "registration_fee_usd": {"type": "number"},
        "student_fee_usd": {"type": "number"},
        "early_bird_fee_usd": {"type": "number"},
        "organizer": {"type": "string"},
        "website_url": {"type": "url"},
        "submission_url": {"type": "url"},
        "description": {"type": "text"}
    }
}',
'Determine if this URL is about an academic or professional conference, symposium, or workshop. Look for keywords like conference, symposium, workshop, call for papers, submission, proceedings.',
'Extract all conference information including dates, location, fees, and submission deadlines.'),

('EXCHANGE', '{
    "fields": {
        "program_name": {"type": "string", "required": true},
        "program_type": {"type": "enum", "options": ["ERASMUS", "BILATERAL", "SUMMER", "SEMESTER", "YEAR", "OTHER"]},
        "host_university": {"type": "string"},
        "host_country": {"type": "string"},
        "host_city": {"type": "string"},
        "eligible_home_universities": {"type": "array", "items": "string"},
        "eligible_fields": {"type": "array", "items": "string"},
        "gpa_minimum": {"type": "number"},
        "language_requirements": {"type": "string"},
        "duration_months": {"type": "number"},
        "duration_semesters": {"type": "number"},
        "tuition_waiver": {"type": "boolean"},
        "stipend_usd": {"type": "number"},
        "travel_grant": {"type": "boolean"},
        "housing_provided": {"type": "boolean"},
        "other_benefits": {"type": "array", "items": "string"},
        "deadline": {"type": "date"},
        "application_url": {"type": "url"},
        "documents_required": {"type": "array", "items": "string"},
        "description": {"type": "text"}
    }
}',
'Determine if this URL is about a student exchange program, study abroad opportunity, or international mobility program. Look for keywords like exchange, study abroad, mobility, Erasmus, bilateral agreement.',
'Extract all exchange program information including eligibility, benefits, and application details.');

-- Sample sources for testing
INSERT INTO sources (name, type, base_url, target_item_types, is_important, notes) VALUES
('Massachusetts Institute of Technology', 'UNIVERSITY', 'https://mit.edu', ARRAY['PROGRAM']::item_type[], true, 'Top US university - priority scraping'),
('Stanford University', 'UNIVERSITY', 'https://stanford.edu', ARRAY['PROGRAM']::item_type[], true, 'Top US university'),
('Fulbright Program', 'SCHOLARSHIP_ORG', 'https://fulbrightprogram.org', ARRAY['SCHOLARSHIP']::item_type[], true, 'Major scholarship provider'),
('DAAD', 'SCHOLARSHIP_ORG', 'https://daad.de', ARRAY['SCHOLARSHIP', 'EXCHANGE']::item_type[], true, 'German Academic Exchange Service'),
('IEEE', 'CONFERENCE_ORG', 'https://ieee.org', ARRAY['CONFERENCE']::item_type[], false, 'Engineering conferences'),
('Erasmus+', 'EXCHANGE_ORG', 'https://erasmus-plus.ec.europa.eu', ARRAY['EXCHANGE']::item_type[], true, 'European exchange program');

COMMIT;
