--
-- PostgreSQL database dump
--

\restrict Iji8rJHV5vpHNBTIgaNGHIHjl3oCsPQuaZT1m6k2Sf84hcVunOH0qZFGYfFM1mh

-- Dumped from database version 14.20 (Homebrew)
-- Dumped by pg_dump version 14.20 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: item_status; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.item_status AS ENUM (
    'DRAFT',
    'NEEDS_REVIEW',
    'VERIFIED',
    'PUBLISHED',
    'OUTDATED',
    'ARCHIVED'
);


ALTER TYPE public.item_status OWNER TO ahmedali;

--
-- Name: item_type; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.item_type AS ENUM (
    'PROGRAM',
    'SCHOLARSHIP',
    'CONFERENCE',
    'EXCHANGE'
);


ALTER TYPE public.item_type OWNER TO ahmedali;

--
-- Name: job_status; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.job_status AS ENUM (
    'PENDING',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);


ALTER TYPE public.job_status OWNER TO ahmedali;

--
-- Name: priority_level; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.priority_level AS ENUM (
    'HIGH',
    'MEDIUM',
    'LOW'
);


ALTER TYPE public.priority_level OWNER TO ahmedali;

--
-- Name: relevance_status; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.relevance_status AS ENUM (
    'PENDING',
    'RELEVANT',
    'NOT_RELEVANT'
);


ALTER TYPE public.relevance_status OWNER TO ahmedali;

--
-- Name: source_type; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.source_type AS ENUM (
    'UNIVERSITY',
    'SCHOLARSHIP_ORG',
    'CONFERENCE_ORG',
    'EXCHANGE_ORG',
    'OTHER'
);


ALTER TYPE public.source_type OWNER TO ahmedali;

--
-- Name: url_status; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.url_status AS ENUM (
    'DISCOVERED',
    'CLASSIFIED',
    'SCRAPED',
    'EXTRACTED',
    'SKIPPED',
    'ERROR'
);


ALTER TYPE public.url_status OWNER TO ahmedali;

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: ahmedali
--

CREATE TYPE public.user_role AS ENUM (
    'ADMIN',
    'EDITOR',
    'VIEWER'
);


ALTER TYPE public.user_role OWNER TO ahmedali;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: ahmedali
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO ahmedali;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_logs; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.ai_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    task_type character varying(50) NOT NULL,
    model_used character varying(100) NOT NULL,
    provider character varying(50) NOT NULL,
    related_type character varying(50),
    related_id uuid,
    job_id uuid,
    input_tokens integer,
    output_tokens integer,
    cost_usd numeric(10,6),
    latency_ms integer,
    input_preview text,
    output_json jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.ai_logs OWNER TO ahmedali;

--
-- Name: discovered_urls; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.discovered_urls (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    source_id uuid,
    url character varying(2000) NOT NULL,
    url_path character varying(1000),
    relevance public.relevance_status DEFAULT 'PENDING'::public.relevance_status,
    relevance_score numeric(5,2),
    relevance_reason text,
    page_type character varying(100),
    detected_item_types public.item_type[],
    content_tags text[],
    priority public.priority_level DEFAULT 'MEDIUM'::public.priority_level,
    has_multiple_items boolean DEFAULT false,
    raw_markdown text,
    content_hash character varying(64),
    status public.url_status DEFAULT 'DISCOVERED'::public.url_status,
    error_message text,
    human_verified boolean DEFAULT false,
    human_notes text,
    verified_by uuid,
    verified_at timestamp with time zone,
    discovered_at timestamp with time zone DEFAULT now(),
    last_scraped_at timestamp with time zone,
    last_classified_at timestamp with time zone
);


ALTER TABLE public.discovered_urls OWNER TO ahmedali;

--
-- Name: item_schemas; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.item_schemas (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    item_type public.item_type NOT NULL,
    schema_json jsonb NOT NULL,
    classification_prompt text,
    extraction_prompt text,
    version integer DEFAULT 1,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.item_schemas OWNER TO ahmedali;

--
-- Name: items; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    source_id uuid,
    discovered_url_id uuid,
    item_type public.item_type NOT NULL,
    data jsonb DEFAULT '{}'::jsonb NOT NULL,
    field_status jsonb DEFAULT '{}'::jsonb,
    custom_fields jsonb DEFAULT '{}'::jsonb,
    notes text,
    admin_notes text,
    tags text[],
    extraction_confidence numeric(5,2),
    status public.item_status DEFAULT 'DRAFT'::public.item_status,
    human_edited boolean DEFAULT false,
    human_verified boolean DEFAULT false,
    verified_by uuid,
    verified_at timestamp with time zone,
    extracted_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.items OWNER TO ahmedali;

--
-- Name: scrape_jobs; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.scrape_jobs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    source_id uuid,
    job_type character varying(50) NOT NULL,
    status public.job_status DEFAULT 'PENDING'::public.job_status,
    current_step character varying(100),
    progress_percent integer DEFAULT 0,
    urls_discovered integer DEFAULT 0,
    urls_relevant integer DEFAULT 0,
    urls_scraped integer DEFAULT 0,
    items_extracted integer DEFAULT 0,
    items_updated integer DEFAULT 0,
    ai_tokens_used integer DEFAULT 0,
    ai_cost_usd numeric(10,4) DEFAULT 0,
    firecrawl_calls integer DEFAULT 0,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_log text,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.scrape_jobs OWNER TO ahmedali;

--
-- Name: settings; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.settings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    key character varying(255) NOT NULL,
    value jsonb NOT NULL,
    description text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.settings OWNER TO ahmedali;

--
-- Name: sources; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.sources (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    type public.source_type NOT NULL,
    base_url character varying(500) NOT NULL,
    target_item_types public.item_type[] NOT NULL,
    scrape_frequency character varying(50) DEFAULT 'MONTHLY'::character varying,
    is_important boolean DEFAULT false,
    is_active boolean DEFAULT true,
    include_patterns text[] DEFAULT '{}'::text[],
    exclude_patterns text[] DEFAULT '{}'::text[],
    last_scraped_at timestamp with time zone,
    urls_discovered_count integer DEFAULT 0,
    items_extracted_count integer DEFAULT 0,
    extra_data jsonb DEFAULT '{}'::jsonb,
    notes text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.sources OWNER TO ahmedali;

--
-- Name: users; Type: TABLE; Schema: public; Owner: ahmedali
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    name character varying(255),
    role public.user_role DEFAULT 'EDITOR'::public.user_role,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.users OWNER TO ahmedali;

--
-- Name: ai_logs ai_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.ai_logs
    ADD CONSTRAINT ai_logs_pkey PRIMARY KEY (id);


--
-- Name: discovered_urls discovered_urls_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.discovered_urls
    ADD CONSTRAINT discovered_urls_pkey PRIMARY KEY (id);


--
-- Name: discovered_urls discovered_urls_source_id_url_key; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.discovered_urls
    ADD CONSTRAINT discovered_urls_source_id_url_key UNIQUE (source_id, url);


--
-- Name: item_schemas item_schemas_item_type_key; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.item_schemas
    ADD CONSTRAINT item_schemas_item_type_key UNIQUE (item_type);


--
-- Name: item_schemas item_schemas_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.item_schemas
    ADD CONSTRAINT item_schemas_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: scrape_jobs scrape_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.scrape_jobs
    ADD CONSTRAINT scrape_jobs_pkey PRIMARY KEY (id);


--
-- Name: settings settings_key_key; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_key_key UNIQUE (key);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_ai_logs_created; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_ai_logs_created ON public.ai_logs USING btree (created_at DESC);


--
-- Name: idx_ai_logs_job; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_ai_logs_job ON public.ai_logs USING btree (job_id);


--
-- Name: idx_ai_logs_task; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_ai_logs_task ON public.ai_logs USING btree (task_type);


--
-- Name: idx_items_data; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_items_data ON public.items USING gin (data);


--
-- Name: idx_items_source; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_items_source ON public.items USING btree (source_id);


--
-- Name: idx_items_status; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_items_status ON public.items USING btree (status);


--
-- Name: idx_items_tags; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_items_tags ON public.items USING gin (tags);


--
-- Name: idx_items_type; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_items_type ON public.items USING btree (item_type);


--
-- Name: idx_jobs_created; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_jobs_created ON public.scrape_jobs USING btree (created_at DESC);


--
-- Name: idx_jobs_source; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_jobs_source ON public.scrape_jobs USING btree (source_id);


--
-- Name: idx_jobs_status; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_jobs_status ON public.scrape_jobs USING btree (status);


--
-- Name: idx_sources_active; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_sources_active ON public.sources USING btree (is_active);


--
-- Name: idx_sources_important; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_sources_important ON public.sources USING btree (is_important);


--
-- Name: idx_sources_type; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_sources_type ON public.sources USING btree (type);


--
-- Name: idx_urls_page_type; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_urls_page_type ON public.discovered_urls USING btree (page_type);


--
-- Name: idx_urls_priority; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_urls_priority ON public.discovered_urls USING btree (priority);


--
-- Name: idx_urls_relevance; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_urls_relevance ON public.discovered_urls USING btree (relevance);


--
-- Name: idx_urls_source; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_urls_source ON public.discovered_urls USING btree (source_id);


--
-- Name: idx_urls_status; Type: INDEX; Schema: public; Owner: ahmedali
--

CREATE INDEX idx_urls_status ON public.discovered_urls USING btree (status);


--
-- Name: item_schemas update_item_schemas_updated_at; Type: TRIGGER; Schema: public; Owner: ahmedali
--

CREATE TRIGGER update_item_schemas_updated_at BEFORE UPDATE ON public.item_schemas FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: items update_items_updated_at; Type: TRIGGER; Schema: public; Owner: ahmedali
--

CREATE TRIGGER update_items_updated_at BEFORE UPDATE ON public.items FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: settings update_settings_updated_at; Type: TRIGGER; Schema: public; Owner: ahmedali
--

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON public.settings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: sources update_sources_updated_at; Type: TRIGGER; Schema: public; Owner: ahmedali
--

CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON public.sources FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: ahmedali
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: ai_logs ai_logs_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.ai_logs
    ADD CONSTRAINT ai_logs_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.scrape_jobs(id) ON DELETE SET NULL;


--
-- Name: discovered_urls discovered_urls_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.discovered_urls
    ADD CONSTRAINT discovered_urls_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: discovered_urls discovered_urls_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.discovered_urls
    ADD CONSTRAINT discovered_urls_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(id);


--
-- Name: items items_discovered_url_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_discovered_url_id_fkey FOREIGN KEY (discovered_url_id) REFERENCES public.discovered_urls(id) ON DELETE SET NULL;


--
-- Name: items items_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: items items_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(id);


--
-- Name: scrape_jobs scrape_jobs_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.scrape_jobs
    ADD CONSTRAINT scrape_jobs_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: scrape_jobs scrape_jobs_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: ahmedali
--

ALTER TABLE ONLY public.scrape_jobs
    ADD CONSTRAINT scrape_jobs_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON DELETE CASCADE;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: ahmedali
--

GRANT USAGE ON SCHEMA public TO dataportal;


--
-- Name: TABLE ai_logs; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.ai_logs TO dataportal;


--
-- Name: TABLE discovered_urls; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.discovered_urls TO dataportal;


--
-- Name: TABLE item_schemas; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.item_schemas TO dataportal;


--
-- Name: TABLE items; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.items TO dataportal;


--
-- Name: TABLE scrape_jobs; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.scrape_jobs TO dataportal;


--
-- Name: TABLE settings; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.settings TO dataportal;


--
-- Name: TABLE sources; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.sources TO dataportal;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: ahmedali
--

GRANT ALL ON TABLE public.users TO dataportal;


--
-- PostgreSQL database dump complete
--

\unrestrict Iji8rJHV5vpHNBTIgaNGHIHjl3oCsPQuaZT1m6k2Sf84hcVunOH0qZFGYfFM1mh

