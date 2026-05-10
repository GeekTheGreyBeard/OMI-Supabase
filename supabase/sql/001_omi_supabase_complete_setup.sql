-- OMI-Supabase complete setup SQL
-- Generated from personalMemoryHub PMH migrations 001-006.
-- Apply to a fresh Supabase/Postgres database before importing n8n workflows or starting the website.
-- Safe to re-run for additive objects where migrations use IF NOT EXISTS; constraints are refreshed by later sections.

create extension if not exists pgcrypto;


-- ============================================================================
-- Source migration: 001_personal_memory_hub_lifecycle.sql
-- ============================================================================
-- personalMemoryHub migration draft 001
-- Purpose: Add source-agnostic lifecycle/sync/review tables around existing Supabase schemas.
-- Status: DRAFT — review before applying to production.
-- Note: Cross-schema foreign keys to existing mem/core/omi tables are intentionally avoided
-- because those tables are owned by Supabase-managed roles; relationships are enforced
-- by workflow/application logic plus audit records.
-- Target: Supabase postgres database currently containing schemas omi/core/mem.

create schema if not exists pmh;

-- External systems/devices/apps that can provide personal-memory evidence.
create table if not exists pmh.source_systems (
  source_system_id uuid primary key default gen_random_uuid(),
  source_key text not null unique, -- e.g. omi, nocodb_memory, n8n_chat_memory, web_scrape, manual
  display_name text not null,
  source_type text not null check (source_type in ('api','webhook','mcp','database','web_scrape','manual','file_import','other')),
  canonical_direction text not null default 'ingest_only' check (canonical_direction in ('ingest_only','bidirectional','export_only')),
  supports_update boolean not null default false,
  supports_delete boolean not null default false,
  supports_webhook boolean not null default false,
  base_url text,
  credential_ref text, -- Vaultwarden item name or credential alias only; never raw secret
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Raw immutable-ish source events. Keep raw payloads here, but control access tightly.
create table if not exists pmh.raw_events (
  raw_event_id uuid primary key default gen_random_uuid(),
  source_system_id uuid not null references pmh.source_systems(source_system_id),
  tenant_id uuid,
  persona_id uuid,
  device_id uuid,
  external_user_id text,
  external_event_id text,
  external_conversation_id text,
  external_memory_id text,
  event_type text not null,
  received_at timestamptz not null default now(),
  event_timestamp timestamptz,
  idempotency_key text,
  payload_hash text not null,
  payload jsonb not null,
  headers jsonb,
  ingest_status text not null default 'received' check (ingest_status in ('received','normalized','candidate_created','ignored','error')),
  error_message text,
  notes text,
  unique(source_system_id, idempotency_key),
  unique(source_system_id, payload_hash)
);

-- Source-agnostic cross-reference for local records and provider records.
create table if not exists pmh.external_refs (
  external_ref_id uuid primary key default gen_random_uuid(),
  source_system_id uuid not null references pmh.source_systems(source_system_id),
  local_record_type text not null check (local_record_type in ('raw_event','conversation','transcript_segment','memory_candidate','memory_object','analysis','asset')),
  local_record_id uuid not null,
  external_id text not null,
  external_parent_id text,
  external_url text,
  content_hash text,
  last_seen_at timestamptz not null default now(),
  last_synced_at timestamptz,
  sync_status text not null default 'seen' check (sync_status in ('seen','pending','synced','drifted','conflict','deleted_remote','deleted_local','error')),
  meta jsonb,
  unique(source_system_id, local_record_type, local_record_id, external_id)
);

-- Candidate memories that need review before durable recall and/or provider sync.
create table if not exists pmh.memory_candidates (
  candidate_id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  persona_id uuid,
  source_system_id uuid not null references pmh.source_systems(source_system_id),
  raw_event_id uuid references pmh.raw_events(raw_event_id),
  conversation_id uuid,
  proposed_title text,
  proposed_content text not null,
  proposed_category text,
  proposed_tags text[] not null default '{}',
  confidence numeric(4,3),
  sensitivity text not null default 'normal' check (sensitivity in ('low','normal','sensitive','restricted')),
  review_status text not null default 'new' check (review_status in ('new','needs_review','approved','rejected','corrected','expired','merged','ignored')),
  recall_eligible boolean not null default false,
  sync_to_source boolean not null default false,
  evidence jsonb, -- snippets, transcript refs, source URLs, confidence reasons
  contradiction_flags jsonb,
  reviewer_notes text,
  rejection_reason text,
  expires_at timestamptz,
  review_after timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text
);

-- Lifecycle overlay for approved canonical memories. This avoids overloading mem.memory_objects.
create table if not exists pmh.memory_lifecycle (
  memory_object_id uuid primary key, -- references mem.memory_objects(memory_object_id); no FK because existing mem schema is owned by supabase_admin
  lifecycle_status text not null default 'active' check (lifecycle_status in ('active','suppressed','expired','archived','deleted','legal_hold')),
  sensitivity text not null default 'normal' check (sensitivity in ('low','normal','sensitive','restricted')),
  recall_eligible boolean not null default true,
  source_of_truth text not null default 'personal_memory_hub',
  retention_policy text not null default 'review_before_delete',
  review_after timestamptz,
  expires_at timestamptz,
  expired_at timestamptz,
  expiration_action text check (expiration_action in ('suppress_recall','archive','delete_local','delete_remote','review_queue')),
  expiration_reason text,
  superseded_by uuid,
  created_from_candidate_id uuid references pmh.memory_candidates(candidate_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Bidirectional sync queue. n8n workers should consume this deterministically.
create table if not exists pmh.sync_jobs (
  sync_job_id uuid primary key default gen_random_uuid(),
  source_system_id uuid not null references pmh.source_systems(source_system_id),
  local_record_type text not null,
  local_record_id uuid not null,
  external_id text,
  action text not null check (action in ('create','update','delete','expire','reconcile','noop')),
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','blocked','cancelled')),
  priority integer not null default 100,
  requested_by text,
  request_payload jsonb,
  response_payload jsonb,
  error_message text,
  attempts integer not null default 0,
  max_attempts integer not null default 5,
  not_before timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Immutable audit log for review, edits, expiration, sync, and destructive actions.
create table if not exists pmh.audit_log (
  audit_id uuid primary key default gen_random_uuid(),
  occurred_at timestamptz not null default now(),
  actor text not null default 'system',
  action text not null,
  target_type text not null,
  target_id uuid,
  source_system_id uuid references pmh.source_systems(source_system_id),
  before_state jsonb,
  after_state jsonb,
  reason text,
  request_id text,
  meta jsonb
);

create index if not exists raw_events_source_received_idx on pmh.raw_events(source_system_id, received_at desc);
create index if not exists raw_events_external_ids_idx on pmh.raw_events(source_system_id, external_conversation_id, external_memory_id);
create index if not exists memory_candidates_review_idx on pmh.memory_candidates(review_status, created_at desc);
create index if not exists memory_candidates_source_idx on pmh.memory_candidates(source_system_id, raw_event_id);
create index if not exists sync_jobs_status_idx on pmh.sync_jobs(status, priority, not_before);
create index if not exists audit_log_target_idx on pmh.audit_log(target_type, target_id, occurred_at desc);

insert into pmh.source_systems (source_key, display_name, source_type, canonical_direction, supports_update, supports_delete, supports_webhook, base_url, credential_ref, notes)
values
  ('omi', 'Omi Developer API / Webhooks', 'webhook', 'bidirectional', true, true, true, 'https://api.omi.me/v1/dev', 'PatriciAI / Omi Developer API Key', 'Primary source for pendant conversations/memories. Treat as evidence, not truth.'),
  ('nocodb_memory', 'NocoDB Memory table', 'database', 'ingest_only', false, false, false, null, null, 'Existing manual memory table with 18 rows; review/import source only.'),
  ('n8n_chat_memory', 'n8n chat memory', 'database', 'ingest_only', false, false, false, null, null, 'Mongo n8n_general_chat_memory; not Omi-specific.'),
  ('manual', 'Manual Personal Memory Hub entry', 'manual', 'export_only', false, false, false, null, null, 'Memories created directly in review UI.'),
  ('web_scrape', 'Web scrape/import source', 'web_scrape', 'ingest_only', false, false, false, null, null, 'Future source type for web profiles/pages/articles.')
on conflict (source_key) do update set
  display_name=excluded.display_name,
  source_type=excluded.source_type,
  canonical_direction=excluded.canonical_direction,
  supports_update=excluded.supports_update,
  supports_delete=excluded.supports_delete,
  supports_webhook=excluded.supports_webhook,
  base_url=excluded.base_url,
  credential_ref=excluded.credential_ref,
  notes=excluded.notes,
  updated_at=now();


-- ============================================================================
-- Source migration: 002_audio_transcription_pipeline.sql
-- ============================================================================
-- personalMemoryHub migration draft 002
-- Purpose: Add optional audio segment metadata and transcription job tracking for Omi Audio Bytes.
-- Status: DRAFT — review before applying to production.
-- Notes:
-- - Raw audio should not be stored directly in Postgres.
-- - If audio retention is enabled later, store bytes in durable object storage and keep only refs/hashes here.
-- - Preferred STT service: Speaches OpenAI-compatible endpoint at http://speaches.splat-i.io/v1/audio/transcriptions.

create table if not exists pmh.audio_segments (
  audio_segment_id uuid primary key default gen_random_uuid(),
  source_system_id uuid not null references pmh.source_systems(source_system_id),
  raw_event_id uuid references pmh.raw_events(raw_event_id),
  external_user_id text,
  external_conversation_id text,
  external_event_id text,
  sample_rate integer,
  segment_seconds numeric(8,3),
  content_type text,
  encoding text default 'pcm16le',
  size_bytes bigint,
  storage_provider text, -- e.g. minio, s3, local_ephemeral; null means metadata-only/no retained audio
  storage_bucket text,
  storage_key text,
  sha256 text,
  retention_policy text not null default 'metadata_only',
  received_at timestamptz not null default now(),
  meta jsonb
);

create table if not exists pmh.transcription_jobs (
  transcription_job_id uuid primary key default gen_random_uuid(),
  audio_segment_id uuid references pmh.audio_segments(audio_segment_id),
  raw_event_id uuid references pmh.raw_events(raw_event_id),
  provider text not null default 'speaches',
  endpoint_ref text not null default 'http://speaches.splat-i.io/v1/audio/transcriptions',
  model text not null default 'whisper-1',
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed','blocked','cancelled')),
  transcript_text text,
  language text,
  confidence numeric(4,3),
  request_meta jsonb,
  response_meta jsonb,
  error_message text,
  attempts integer not null default 0,
  max_attempts integer not null default 3,
  not_before timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists audio_segments_source_received_idx on pmh.audio_segments(source_system_id, received_at desc);
create index if not exists audio_segments_conversation_idx on pmh.audio_segments(external_conversation_id, received_at);
create index if not exists transcription_jobs_status_idx on pmh.transcription_jobs(status, not_before, created_at);


-- ============================================================================
-- Source migration: 003_review_lifecycle.sql
-- ============================================================================
-- personalMemoryHub migration 003
-- Purpose: Memory-first review lifecycle primitives.
-- Status: additive; no destructive changes.
-- Notes:
-- - Approved memories live in pmh.approved_memories for the POC to avoid relying on Supabase-managed mem.* ownership.
-- - Later, approved memories can be mirrored into mem.memory_objects and/or pgvector after review policy is stable.

create table if not exists pmh.approved_memories (
  approved_memory_id uuid primary key default gen_random_uuid(),
  candidate_id uuid references pmh.memory_candidates(candidate_id),
  source_system_id uuid references pmh.source_systems(source_system_id),
  tenant_id uuid,
  persona_id uuid,
  title text,
  content text not null,
  category text,
  tags text[] not null default '{}',
  confidence numeric(4,3),
  sensitivity text not null default 'normal' check (sensitivity in ('low','normal','sensitive','restricted')),
  recall_eligible boolean not null default true,
  lifecycle_status text not null default 'active' check (lifecycle_status in ('active','suppressed','expired','archived','deleted','legal_hold')),
  source_of_truth text not null default 'personal_memory_hub',
  retention_policy text not null default 'review_before_delete',
  evidence jsonb,
  review_notes text,
  approved_by text not null default 'system',
  approved_at timestamptz not null default now(),
  review_after timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pmh.review_actions (
  review_action_id uuid primary key default gen_random_uuid(),
  candidate_id uuid references pmh.memory_candidates(candidate_id),
  approved_memory_id uuid references pmh.approved_memories(approved_memory_id),
  action text not null check (action in ('approve','correct_and_approve','reject','expire','mark_sensitive','mark_restricted','suppress_recall')),
  actor text not null default 'system',
  notes text,
  before_state jsonb,
  after_state jsonb,
  created_at timestamptz not null default now()
);

create or replace view pmh.review_queue as
select
  c.candidate_id,
  c.created_at,
  c.review_status,
  c.sensitivity,
  c.confidence,
  ss.source_key,
  ss.display_name as source_display_name,
  c.proposed_title,
  left(c.proposed_content, 500) as proposed_content_preview,
  length(c.proposed_content) as proposed_content_length,
  c.proposed_category,
  c.proposed_tags,
  c.recall_eligible,
  c.sync_to_source,
  c.raw_event_id,
  c.evidence,
  c.review_after,
  c.expires_at
from pmh.memory_candidates c
join pmh.source_systems ss on ss.source_system_id = c.source_system_id
where c.review_status in ('new','needs_review')
order by c.created_at asc;

create or replace view pmh.memory_status_summary as
select 'candidate_' || review_status as bucket, count(*)::bigint as count
from pmh.memory_candidates
group by review_status
union all
select 'approved_' || lifecycle_status as bucket, count(*)::bigint as count
from pmh.approved_memories
group by lifecycle_status
union all
select 'sync_' || status as bucket, count(*)::bigint as count
from pmh.sync_jobs
group by status;

create or replace function pmh.apply_candidate_review(
  p_candidate_id uuid,
  p_action text,
  p_actor text default 'system',
  p_title text default null,
  p_content text default null,
  p_category text default null,
  p_tags text[] default null,
  p_sensitivity text default null,
  p_recall_eligible boolean default null,
  p_notes text default null,
  p_rejection_reason text default null,
  p_review_after timestamptz default null,
  p_expires_at timestamptz default null,
  p_sync_to_source boolean default false
) returns jsonb
language plpgsql
as $$
declare
  c pmh.memory_candidates%rowtype;
  before_candidate jsonb;
  approved_id uuid;
  final_title text;
  final_content text;
  final_category text;
  final_tags text[];
  final_sensitivity text;
  final_recall boolean;
  final_status text;
  result jsonb;
begin
  select * into c
  from pmh.memory_candidates
  where candidate_id = p_candidate_id
  for update;

  if not found then
    raise exception 'candidate % not found', p_candidate_id using errcode = 'P0002';
  end if;

  before_candidate := to_jsonb(c);

  if c.review_status not in ('new','needs_review') then
    raise exception 'candidate % is not reviewable; current status=%', p_candidate_id, c.review_status using errcode = 'P0001';
  end if;

  if p_action not in ('approve','correct_and_approve','reject','expire','mark_sensitive','mark_restricted','suppress_recall') then
    raise exception 'unsupported review action %', p_action using errcode = '22023';
  end if;

  final_title := coalesce(nullif(trim(p_title), ''), c.proposed_title);
  final_content := coalesce(nullif(trim(p_content), ''), c.proposed_content);
  final_category := coalesce(nullif(trim(p_category), ''), c.proposed_category);
  final_tags := coalesce(p_tags, c.proposed_tags, '{}');
  final_sensitivity := coalesce(nullif(trim(p_sensitivity), ''), c.sensitivity, 'normal');
  final_recall := coalesce(p_recall_eligible, true);

  if p_action in ('approve','correct_and_approve') then
    if nullif(trim(final_content), '') is null then
      raise exception 'approved memory content cannot be empty' using errcode = '23514';
    end if;

    if final_sensitivity in ('sensitive','restricted') and final_recall = true then
      final_recall := false;
    end if;

    insert into pmh.approved_memories (
      candidate_id, source_system_id, tenant_id, persona_id,
      title, content, category, tags, confidence, sensitivity,
      recall_eligible, evidence, review_notes, approved_by,
      review_after, expires_at
    ) values (
      c.candidate_id, c.source_system_id, c.tenant_id, c.persona_id,
      final_title, final_content, final_category, final_tags, c.confidence, final_sensitivity,
      final_recall, c.evidence, p_notes, p_actor,
      p_review_after, p_expires_at
    ) returning approved_memory_id into approved_id;

    final_status := case when p_action = 'correct_and_approve' then 'corrected' else 'approved' end;

    update pmh.memory_candidates
    set review_status = final_status,
        proposed_title = final_title,
        proposed_content = final_content,
        proposed_category = final_category,
        proposed_tags = final_tags,
        sensitivity = final_sensitivity,
        recall_eligible = final_recall,
        sync_to_source = coalesce(p_sync_to_source, false),
        reviewer_notes = p_notes,
        reviewed_at = now(),
        reviewed_by = p_actor,
        updated_at = now(),
        review_after = p_review_after,
        expires_at = p_expires_at
    where candidate_id = p_candidate_id;

    if coalesce(p_sync_to_source, false) then
      insert into pmh.sync_jobs (source_system_id, local_record_type, local_record_id, action, requested_by, request_payload)
      values (c.source_system_id, 'approved_memory', approved_id, 'update', p_actor, jsonb_build_object('candidate_id', c.candidate_id, 'reason', 'review_approved_sync'));
    end if;

  elsif p_action = 'reject' then
    update pmh.memory_candidates
    set review_status = 'rejected',
        reviewer_notes = p_notes,
        rejection_reason = p_rejection_reason,
        reviewed_at = now(),
        reviewed_by = p_actor,
        updated_at = now(),
        recall_eligible = false,
        sync_to_source = false
    where candidate_id = p_candidate_id;

  elsif p_action = 'expire' then
    update pmh.memory_candidates
    set review_status = 'expired',
        reviewer_notes = p_notes,
        reviewed_at = now(),
        reviewed_by = p_actor,
        updated_at = now(),
        recall_eligible = false,
        sync_to_source = false,
        expires_at = coalesce(p_expires_at, now())
    where candidate_id = p_candidate_id;

  elsif p_action in ('mark_sensitive','mark_restricted','suppress_recall') then
    update pmh.memory_candidates
    set sensitivity = case
          when p_action = 'mark_restricted' then 'restricted'
          when p_action = 'mark_sensitive' then 'sensitive'
          else sensitivity
        end,
        recall_eligible = false,
        reviewer_notes = p_notes,
        updated_at = now()
    where candidate_id = p_candidate_id;
  end if;

  insert into pmh.review_actions (candidate_id, approved_memory_id, action, actor, notes, before_state, after_state)
  select p_candidate_id, approved_id, p_action, p_actor, p_notes, before_candidate, to_jsonb(c2)
  from pmh.memory_candidates c2
  where c2.candidate_id = p_candidate_id;

  insert into pmh.audit_log (actor, action, target_type, target_id, source_system_id, before_state, after_state, reason, meta)
  select p_actor, 'candidate_review_' || p_action, 'memory_candidate', p_candidate_id, c.source_system_id,
         before_candidate, to_jsonb(c2), p_notes, jsonb_build_object('approved_memory_id', approved_id)
  from pmh.memory_candidates c2
  where c2.candidate_id = p_candidate_id;

  result := jsonb_build_object(
    'candidate_id', p_candidate_id,
    'action', p_action,
    'approved_memory_id', approved_id,
    'status', (select review_status from pmh.memory_candidates where candidate_id = p_candidate_id)
  );

  return result;
end;
$$;

create index if not exists approved_memories_recall_idx on pmh.approved_memories(recall_eligible, lifecycle_status, sensitivity);
create index if not exists approved_memories_candidate_idx on pmh.approved_memories(candidate_id);
create index if not exists review_actions_candidate_idx on pmh.review_actions(candidate_id, created_at desc);


-- ============================================================================
-- Source migration: 004_ui_omi_submit_actions.sql
-- ============================================================================
-- PMH UI Omi submit/audit support
-- Applied to private POC on 2026-05-10.

alter table pmh.review_actions drop constraint if exists review_actions_action_check;

alter table pmh.review_actions add constraint review_actions_action_check check (
  action = any (array[
    'approve',
    'correct_and_approve',
    'reject',
    'expire',
    'mark_sensitive',
    'mark_restricted',
    'suppress_recall',
    'quick_update',
    'edit_approved_memory',
    'submit_to_omi'
  ]::text[])
);


-- ============================================================================
-- Source migration: 005_tags_and_omi_replace_submit.sql
-- ============================================================================
-- PMH tag registry and replace-style Omi submit support
-- Applied to private POC on 2026-05-10.

create table if not exists pmh.tag_registry (
  tag text primary key,
  normalized_tag text generated always as (lower(tag)) stored unique,
  active boolean not null default true,
  created_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint tag_registry_tag_not_blank check (length(trim(tag)) > 0),
  constraint tag_registry_tag_length check (length(tag) <= 64)
);

insert into pmh.tag_registry(tag, created_by)
select distinct tag, 'migration:existing_pmh_tags'
from (
  select unnest(tags) tag from pmh.approved_memories where tags is not null
  union
  select unnest(proposed_tags) tag from pmh.memory_candidates where proposed_tags is not null
) t
where nullif(trim(tag),'') is not null
on conflict do nothing;

alter table pmh.approved_memories
  add column if not exists omi_visibility text not null default 'private';

alter table pmh.approved_memories drop constraint if exists approved_memories_omi_visibility_check;
alter table pmh.approved_memories add constraint approved_memories_omi_visibility_check check (omi_visibility in ('private','public'));

alter table pmh.sync_jobs drop constraint if exists sync_jobs_action_check;
alter table pmh.sync_jobs add constraint sync_jobs_action_check check (
  action = any (array['create','update','delete','expire','reconcile','noop','replace']::text[])
);

alter table pmh.review_actions drop constraint if exists review_actions_action_check;
alter table pmh.review_actions add constraint review_actions_action_check check (
  action = any (array[
    'approve','correct_and_approve','reject','expire','mark_sensitive','mark_restricted','suppress_recall',
    'quick_update','edit_approved_memory','submit_to_omi'
  ]::text[])
);


-- ============================================================================
-- Source migration: 006_trash_lifecycle_actions.sql
-- ============================================================================
-- PMH trash lifecycle actions for soft-delete/restore audit
-- Applied to private POC on 2026-05-10.

alter table pmh.review_actions drop constraint if exists review_actions_action_check;
alter table pmh.review_actions add constraint review_actions_action_check check (
  action = any (array[
    'approve','correct_and_approve','reject','expire','mark_sensitive','mark_restricted','suppress_recall',
    'quick_update','edit_approved_memory','submit_to_omi','delete','restore'
  ]::text[])
);

