// Enums
export type SourceType = 'UNIVERSITY' | 'SCHOLARSHIP_ORG' | 'CONFERENCE_ORG' | 'EXCHANGE_ORG' | 'OTHER';
export type ItemType = 'PROGRAM' | 'SCHOLARSHIP' | 'CONFERENCE' | 'EXCHANGE';
export type URLStatus = 'DISCOVERED' | 'CLASSIFIED' | 'SCRAPED' | 'EXTRACTED' | 'SKIPPED' | 'ERROR';
export type RelevanceStatus = 'PENDING' | 'RELEVANT' | 'NOT_RELEVANT';
export type PriorityLevel = 'HIGH' | 'MEDIUM' | 'LOW';
export type ItemStatus = 'DRAFT' | 'NEEDS_REVIEW' | 'VERIFIED' | 'PUBLISHED' | 'OUTDATED' | 'ARCHIVED';
export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type UserRole = 'ADMIN' | 'EDITOR' | 'VIEWER';

// User
export interface User {
  id: string;
  email: string;
  name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Source
export interface Source {
  id: string;
  name: string;
  type: SourceType;
  base_url: string;
  target_item_types: ItemType[];
  scrape_frequency: string;
  is_important: boolean;
  is_active: boolean;
  include_patterns: string[];
  exclude_patterns: string[];
  metadata: Record<string, any>;
  notes: string | null;
  last_scraped_at: string | null;
  urls_discovered_count: number;
  items_extracted_count: number;
  created_at: string;
  updated_at: string;
}

// Discovered URL
export interface DiscoveredURL {
  id: string;
  source_id: string;
  url: string;
  url_path: string | null;
  relevance: RelevanceStatus;
  relevance_score: number | null;
  relevance_reason: string | null;
  page_type: string | null;
  detected_item_types: ItemType[] | null;
  content_tags: string[] | null;
  priority: PriorityLevel;
  has_multiple_items: boolean;
  raw_markdown: string | null;
  content_hash: string | null;
  status: URLStatus;
  error_message: string | null;
  human_verified: boolean;
  human_notes: string | null;
  verified_by: string | null;
  verified_at: string | null;
  discovered_at: string | null;
  last_scraped_at: string | null;
  last_classified_at: string | null;
}

// Item
export interface Item {
  id: string;
  source_id: string;
  discovered_url_id: string | null;
  item_type: ItemType;
  data: Record<string, any>;
  field_status: Record<string, string>;
  custom_fields: Record<string, any>;
  notes: string | null;
  admin_notes: string | null;
  tags: string[] | null;
  extraction_confidence: number | null;
  status: ItemStatus;
  human_edited: boolean;
  human_verified: boolean;
  verified_by: string | null;
  verified_at: string | null;
  extracted_at: string | null;
  created_at: string;
  updated_at: string;
}

// Scrape Job
export interface ScrapeJob {
  id: string;
  source_id: string | null;
  job_type: string;
  status: JobStatus;
  current_step: string | null;
  progress_percent: number;
  urls_discovered: number;
  urls_relevant: number;
  urls_scraped: number;
  items_extracted: number;
  items_updated: number;
  ai_tokens_used: number;
  ai_cost_usd: number;
  firecrawl_calls: number;
  started_at: string | null;
  completed_at: string | null;
  error_log: string | null;
  created_by: string | null;
  created_at: string;
}

// Paginated Response
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Auth
export interface LoginRequest {
  email: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

// AI Config
export interface AIConfig {
  default_provider: string;
  default_model: string;
  providers: Record<string, { models: string[]; default_model: string }>;
  task_config: Record<string, { provider: string; model: string; batch_size?: number }>;
}
