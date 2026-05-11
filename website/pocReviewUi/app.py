import os, html, secrets, json, urllib.request, urllib.error, hashlib
from typing import Optional, List
from uuid import UUID

import psycopg
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

DATABASE_URL = os.environ["DATABASE_URL"]
UI_USER = os.environ.get("PMH_UI_USER", "rodney")
UI_PASSWORD = os.environ["PMH_UI_PASSWORD"]
APP_TITLE = "Personal Memory Hub"
OMI_API_KEY = os.environ.get("OMI_API_KEY")
OMI_API_BASE = os.environ.get("OMI_API_BASE", "https://api.omi.me").rstrip("/")

# Omi Developer API memory categories documented by Omi: interesting, system, manual.
CATEGORY_OPTIONS = ["interesting", "system", "manual"]
# Omi currently exposes memory visibility rather than sensitivity. PMH keeps a local
# sensitivity gate so sensitive/restricted memories can be excluded from recall/sync by default.
SENSITIVITY_OPTIONS = ["low", "normal", "sensitive", "restricted"]
OMI_VISIBILITY_OPTIONS = ["private", "public"]
PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 250]

app = FastAPI(title=APP_TITLE)
security = HTTPBasic()


def auth(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username, UI_USER)
    ok_pass = secrets.compare_digest(creds.password, UI_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Basic"})
    return creds.username


def q(sql, params=None):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, params or {})
            return cur.fetchall()


def one(sql, params=None):
    rows = q(sql, params)
    return rows[0] if rows else None


def exec_one(sql, params=None):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, params or {})
            row = cur.fetchone()
            conn.commit()
            return row


def esc(v):
    return html.escape("" if v is None else str(v))


def clamp_limit(limit: int):
    return limit if limit in PAGE_SIZE_OPTIONS else 50


def selected(v, cur):
    return " selected" if (v or "") == (cur or "") else ""


def checked(v):
    return " checked" if v else ""


def options(values, current):
    return "".join([f"<option value='{esc(v)}'{selected(v, current)}>{esc(v)}</option>" for v in values])


def hidden(name, value):
    if isinstance(value, list):
        return "".join(hidden(name, v) for v in value)
    return f"<input type='hidden' name='{esc(name)}' value='{esc(value)}'>"


def clean_tag(tag):
    return " ".join((tag or "").strip().split())[:64]


def unique_keep_order(values):
    out = []
    seen = set()
    for v in values:
        if v and v.lower() not in seen:
            out.append(v)
            seen.add(v.lower())
    return out


def tag_list(tags: Optional[str]):
    return unique_keep_order([clean_tag(t) for t in (tags or '').split(',') if clean_tag(t)]) or None


def get_available_tags():
    rows = q("select tag from pmh.tag_registry where active = true order by lower(tag) limit 256")
    return [r['tag'] for r in rows]


def stable_hash(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode('utf-8')).hexdigest()


def get_source_system_id(cur, source_key='omi'):
    cur.execute('select source_system_id from pmh.source_systems where source_key=%s', (source_key,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f'source system {source_key} not found')
    return row['source_system_id']


def sensitivity_for_content(content):
    text = (content or '').lower()
    sensitive_terms = ['health', 'medical', 'doctor', 'treatment', 'cancer', 'tumor', 'diagnosis', 'medication', 'password', 'credential', 'financial', 'legal']
    return 'sensitive' if any(t in text for t in sensitive_terms) else 'normal'


def tag_editor(selected_tags):
    selected_tags = selected_tags or []
    selected_lower = {t.lower() for t in selected_tags}
    available = get_available_tags()
    for t in selected_tags:
        if t and t.lower() not in {a.lower() for a in available}:
            available.append(t)
    checks = ''.join([f"<label style='margin:6px 10px 6px 0; display:inline-flex; gap:6px; align-items:center'><input type='checkbox' name='tags' value='{esc(t)}'{' checked' if t.lower() in selected_lower else ''}> {esc(t)}</label>" for t in available]) or "<p class='muted'>No tags registered yet. Add up to five new tags below.</p>"
    new_inputs = ''.join([f"<input name='new_tag_{i}' placeholder='New tag {i}' maxlength='64'>" for i in range(1,6)])
    return f"""<details class='card' style='margin-top:16px'><summary><strong>Tags</strong> <span class='muted'>choose up to 32; add up to 5 new tags</span></summary><div class='badges' style='margin-top:12px'>{checks}</div><div class='grid'>{new_inputs}</div></details>"""


def parse_tags_from_form(form):
    selected = [clean_tag(t) for t in form.getlist('tags') if clean_tag(t)]
    new_tags = [clean_tag(form.get(f'new_tag_{i}', '')) for i in range(1, 6)]
    new_tags = [t for t in new_tags if t]
    if len(new_tags) > 5:
        raise HTTPException(400, 'A maximum of 5 new tags may be added per edit')
    tags = unique_keep_order(selected + new_tags)
    if len(tags) > 32:
        raise HTTPException(400, 'A maximum of 32 tags may be attached to one memory')
    return tags


def ensure_tags_registered(tags, actor):
    tags = tags or []
    if not tags:
        return
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute('select count(*) as c from pmh.tag_registry where active = true')
            current = cur.fetchone()['c']
            cur.execute('select lower(tag) as normalized_tag from pmh.tag_registry where active = true')
            existing = {r['normalized_tag'] for r in cur.fetchall()}
            new = [t for t in tags if t.lower() not in existing]
            if current + len(new) > 256:
                raise HTTPException(400, 'Global tag limit of 256 would be exceeded')
            for t in new:
                cur.execute('insert into pmh.tag_registry(tag, created_by) values (%s,%s) on conflict (normalized_tag) do nothing', (t, actor))
            conn.commit()

def get_omi_external_id(cur, memory):
    """Find the original Omi memory id for an approved memory without exposing raw payloads."""
    omi_source_id = get_source_system_id(cur, 'omi')
    cur.execute("""
      select external_id
      from pmh.external_refs
      where source_system_id = %s
        and local_record_type in ('memory_object','approved_memory')
        and local_record_id = %s
        and sync_status <> 'deleted_remote'
      order by last_synced_at desc nulls last, last_seen_at desc
      limit 1
    """, (omi_source_id, memory.get('approved_memory_id')))
    row = cur.fetchone()
    if row and row.get('external_id'):
        return row['external_id']
    evidence = memory.get('evidence') or {}
    if isinstance(evidence, dict) and evidence.get('external_memory_id'):
        return evidence.get('external_memory_id')
    if memory.get('candidate_id'):
        cur.execute("select evidence, raw_event_id from pmh.memory_candidates where candidate_id=%s", (memory.get('candidate_id'),))
        c = cur.fetchone()
        if c:
            ce = c.get('evidence') or {}
            if isinstance(ce, dict) and ce.get('external_memory_id'):
                return ce.get('external_memory_id')
            if c.get('raw_event_id'):
                cur.execute("select external_memory_id, payload from pmh.raw_events where raw_event_id=%s", (c.get('raw_event_id'),))
                re = cur.fetchone()
                if re:
                    if re.get('external_memory_id'):
                        return re.get('external_memory_id')
                    payload = re.get('payload') or {}
                    if isinstance(payload, dict) and payload.get('id'):
                        return payload.get('id')
    return None


def omi_request(method, path, payload=None):
    if not OMI_API_KEY:
        raise RuntimeError('OMI_API_KEY is not configured for this UI service')
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        OMI_API_BASE + path,
        data=data,
        method=method,
        headers={
            'Authorization': f'Bearer {OMI_API_KEY}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(body) if body else {}
        except Exception:
            parsed = {'raw': body[:1000]}
        raise RuntimeError(f'Omi API returned HTTP {e.code}: {parsed}')


def submit_memory_to_omi(memory_id, actor):
    """Replace the Omi-side memory with the PMH-approved version.

    Omi POST accepts content/category/visibility/tags, while PATCH only documents
    content/visibility. For fidelity, create the replacement first, verify Omi
    returned an ID, then delete the superseded original so stale Omi memories do
    not linger.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("select * from pmh.approved_memories where approved_memory_id=%s for update", (str(memory_id),))
            mem = cur.fetchone()
            if not mem:
                raise HTTPException(404, 'memory not found')
            omi_source_id = get_source_system_id(cur, 'omi')
            old_external_id = get_omi_external_id(cur, mem)
            sync_action = 'replace' if old_external_id else 'create'
            visibility = mem.get('omi_visibility') or 'private'
            create_payload = {
                'content': mem['content'],
                'category': mem.get('category') or 'system',
                'visibility': visibility,
                'tags': list(mem.get('tags') or []),
            }
            status, create_response = omi_request('POST', '/v1/dev/user/memories', create_payload)
            new_external_id = create_response.get('id')
            if not new_external_id:
                raise RuntimeError(f'Omi create did not return a replacement memory id: {create_response}')

            delete_status = None
            delete_response = None
            if old_external_id and old_external_id != new_external_id:
                try:
                    delete_status, delete_response = omi_request('DELETE', f'/v1/dev/user/memories/{old_external_id}')
                except Exception as e:
                    # The new memory exists, so keep the local record marked as conflict for follow-up.
                    cur.execute("""
                      insert into pmh.sync_jobs(source_system_id, local_record_type, local_record_id, external_id, action, status, requested_by, request_payload, response_payload, error_message, attempts, started_at, finished_at)
                      values (%(source_system_id)s, 'approved_memory', %(id)s::uuid, %(external_id)s, 'replace', 'failed', %(actor)s, %(request)s::jsonb, %(response)s::jsonb, %(error)s, 1, now(), now())
                    """, {'source_system_id': omi_source_id, 'id': str(memory_id), 'external_id': new_external_id, 'actor': actor, 'request': json.dumps({'create': create_payload, 'delete_old_external_id': old_external_id}), 'response': json.dumps({'create': create_response}), 'error': str(e)})
                    conn.commit()
                    raise RuntimeError(f'Created replacement Omi memory {new_external_id}, but failed to delete old Omi memory {old_external_id}: {e}')

            cur.execute("""
              insert into pmh.sync_jobs(source_system_id, local_record_type, local_record_id, external_id, action, status, requested_by, request_payload, response_payload, attempts, started_at, finished_at)
              values (%(source_system_id)s, 'approved_memory', %(id)s::uuid, %(external_id)s, %(action)s, 'succeeded', %(actor)s, %(request)s::jsonb, %(response)s::jsonb, 1, now(), now())
              returning sync_job_id
            """, {'source_system_id': omi_source_id, 'id': str(memory_id), 'external_id': new_external_id, 'action': sync_action, 'actor': actor, 'request': json.dumps({'create': create_payload, 'delete_old_external_id': old_external_id}), 'response': json.dumps({'created': create_response, 'deleted_old': delete_response, 'delete_status': delete_status})})
            job_id = cur.fetchone()['sync_job_id']

            if old_external_id and old_external_id != new_external_id:
                cur.execute("""
                  update pmh.external_refs
                  set sync_status='deleted_remote', last_synced_at=now(), meta=coalesce(meta,'{}'::jsonb) || %(meta)s::jsonb
                  where source_system_id=%(source_system_id)s and external_id=%(old_external_id)s
                """, {'source_system_id': omi_source_id, 'old_external_id': old_external_id, 'meta': json.dumps({'superseded_by': new_external_id, 'sync_job_id': str(job_id)})})

            cur.execute("""
              insert into pmh.external_refs(source_system_id, local_record_type, local_record_id, external_id, last_synced_at, sync_status, meta)
              values (%(source_system_id)s, 'memory_object', %(id)s::uuid, %(external_id)s, now(), 'synced', %(meta)s::jsonb)
              on conflict (source_system_id, local_record_type, local_record_id, external_id)
              do update set last_synced_at=excluded.last_synced_at, sync_status='synced', meta=excluded.meta
            """, {'source_system_id': omi_source_id, 'id': str(memory_id), 'external_id': new_external_id, 'meta': json.dumps({'sync_job_id': str(job_id), 'omi_api_status': status, 'action': sync_action, 'supersedes': old_external_id})})

            cur.execute("""
              update pmh.sync_jobs
              set status='succeeded', finished_at=coalesce(finished_at, now()), response_payload=coalesce(response_payload, '{}'::jsonb) || %(queued_response)s::jsonb
              where local_record_type='approved_memory' and local_record_id=%(id)s::uuid and status='queued'
            """, {'id': str(memory_id), 'queued_response': json.dumps({'completed_by_sync_job_id': str(job_id), 'omi_external_id': new_external_id})})

            cur.execute("""
              insert into pmh.review_actions(approved_memory_id, action, actor, notes, before_state, after_state)
              values (%(id)s::uuid, 'submit_to_omi', %(actor)s, %(notes)s, %(before)s::jsonb, %(after)s::jsonb)
            """, {'id': str(memory_id), 'actor': actor, 'notes': 'Submitted Omi memory by creating full-detail memory' + (' and deleting superseded original' if old_external_id else ''), 'before': json.dumps(dict(mem), default=str), 'after': json.dumps({'old_external_id': old_external_id, 'new_external_id': new_external_id, 'sync_job_id': str(job_id), 'omi_api_status': status, 'action': sync_action, 'delete_status': delete_status})})
            conn.commit()
            return {'action': sync_action, 'old_external_id': old_external_id, 'new_external_id': new_external_id, 'sync_job_id': str(job_id), 'omi_api_status': status, 'delete_status': delete_status}



def move_memory_to_trash(memory_id, actor, reason='Moved to trash from PMH UI'):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("select * from pmh.approved_memories where approved_memory_id=%s for update", (str(memory_id),))
            mem = cur.fetchone()
            if not mem:
                raise HTTPException(404, 'memory not found')
            if mem.get('lifecycle_status') == 'deleted':
                return {'status': 'already_deleted'}
            before = dict(mem)
            old_external_id = get_omi_external_id(cur, mem)
            delete_status = None
            delete_response = None
            omi_source_id = get_source_system_id(cur, 'omi')
            if old_external_id:
                delete_status, delete_response = omi_request('DELETE', f'/v1/dev/user/memories/{old_external_id}')
                cur.execute("""
                  update pmh.external_refs
                  set sync_status='deleted_remote', last_synced_at=now(), meta=coalesce(meta,'{}'::jsonb) || %(meta)s::jsonb
                  where source_system_id=%(source_system_id)s and external_id=%(external_id)s
                """, {'source_system_id': omi_source_id, 'external_id': old_external_id, 'meta': json.dumps({'deleted_by': actor, 'deleted_reason': reason})})
                cur.execute("""
                  insert into pmh.sync_jobs(source_system_id, local_record_type, local_record_id, external_id, action, status, requested_by, request_payload, response_payload, attempts, started_at, finished_at)
                  values (%s,'approved_memory',%s,%s,'delete','succeeded',%s,%s::jsonb,%s::jsonb,1,now(),now())
                """, (omi_source_id, memory_id, old_external_id, actor, json.dumps({'reason': reason}), json.dumps({'delete_status': delete_status, 'delete_response': delete_response})))
            cur.execute("""
              update pmh.sync_jobs
              set status='cancelled', finished_at=now(), response_payload=coalesce(response_payload,'{}'::jsonb) || %(payload)s::jsonb
              where local_record_type='approved_memory' and local_record_id=%(id)s::uuid and status='queued'
            """, {'id': str(memory_id), 'payload': json.dumps({'cancelled_by': actor, 'reason': 'memory_moved_to_trash'})})
            cur.execute("""
              update pmh.approved_memories
              set lifecycle_status='deleted', recall_eligible=false, updated_at=now(), review_notes=concat_ws(E'\n', review_notes, %(note)s::text)
              where approved_memory_id=%(id)s::uuid
              returning *
            """, {'id': str(memory_id), 'note': f'Trashed by {actor}: {reason}'})
            after = cur.fetchone()
            cur.execute("""
              insert into pmh.review_actions(approved_memory_id, action, actor, notes, before_state, after_state)
              values (%s,'delete',%s,%s,%s::jsonb,%s::jsonb)
            """, (memory_id, actor, reason, json.dumps(before, default=str), json.dumps(dict(after), default=str)))
            conn.commit()
            return {'status': 'trashed', 'deleted_omi_external_id': old_external_id, 'delete_status': delete_status}


def restore_memory_from_trash(memory_id, actor):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("select * from pmh.approved_memories where approved_memory_id=%s for update", (str(memory_id),))
            mem = cur.fetchone()
            if not mem:
                raise HTTPException(404, 'memory not found')
            if mem.get('lifecycle_status') != 'deleted':
                return {'status': 'not_in_trash'}
            before = dict(mem)
            recall = False if mem.get('sensitivity') in ('sensitive', 'restricted') else bool(mem.get('recall_eligible'))
            cur.execute("""
              update pmh.approved_memories
              set lifecycle_status='active', recall_eligible=%s, updated_at=now(), review_notes=concat_ws(E'\n', review_notes, %s::text)
              where approved_memory_id=%s
              returning *
            """, (recall, f'Restored from trash by {actor}; Omi will be created as a new memory on submission.', memory_id))
            after = cur.fetchone()
            omi_source_id = get_source_system_id(cur, 'omi')
            cur.execute("""
              insert into pmh.sync_jobs(source_system_id, local_record_type, local_record_id, action, status, requested_by, request_payload)
              values (%s,'approved_memory',%s,'create','queued',%s,%s::jsonb)
            """, (omi_source_id, memory_id, actor, json.dumps({'reason': 'restored_from_trash_create_new_omi_memory'})))
            cur.execute("""
              insert into pmh.review_actions(approved_memory_id, action, actor, notes, before_state, after_state)
              values (%s,'restore',%s,%s,%s::jsonb,%s::jsonb)
            """, (memory_id, actor, 'Restored from trash; queued to create a new Omi memory', json.dumps(before, default=str), json.dumps(dict(after), default=str)))
            conn.commit()
            return {'status': 'restored_and_queued'}

def layout(title, body, notice=""):
    nav = """
      <a class='btn secondary' href='/memory/home'>Home</a>
      <a class='btn secondary' href='/review'>Review Queue</a>
      <a class='btn secondary' href='/memories'>Primary Memories</a>
      <a class='btn secondary' href='/omi/pull'>Retrieve from Omi</a>
      <a class='btn secondary' href='/memory/new'>New Memory</a>
      <a class='btn secondary' href='/submissions'>Submission Queue</a>
      <a class='btn secondary' href='/trash'>Trash Bin</a>
    """
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{esc(title)} · PMH</title>
<style>
:root {{ --bg:#080b18; --panel:rgba(18,25,48,.78); --panel2:rgba(30,39,76,.72); --text:#edf3ff; --muted:#9fb0d0; --accent:#8a5cff; --accent2:#20e3b2; --danger:#ff5c8a; --warn:#ffcc66; --ok:#42f59b; }}
* {{ box-sizing:border-box; }} body {{ margin:0; min-height:100vh; font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; color:var(--text); background: radial-gradient(circle at 20% 10%, #31206a 0, transparent 28rem), radial-gradient(circle at 80% 0%, #0a6b70 0, transparent 24rem), linear-gradient(135deg,#070914,#101427 55%,#080b18); }}
a {{ color:#9bdcff; text-decoration:none; }} .wrap {{ max-width:1240px; margin:0 auto; padding:32px 20px 60px; }}
.hero {{ display:flex; justify-content:space-between; gap:20px; align-items:center; margin-bottom:24px; }}
.brand {{ font-size:30px; font-weight:800; letter-spacing:-.04em; }} .brand span {{ background:linear-gradient(90deg,var(--accent2),#d6c7ff,var(--accent)); -webkit-background-clip:text; color:transparent; }}
.sub {{ color:var(--muted); margin-top:6px; }} .nav {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:flex-end; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:20px 0; }}
.card {{ background:linear-gradient(180deg,var(--panel),rgba(10,14,32,.82)); border:1px solid rgba(255,255,255,.10); border-radius:22px; padding:18px; box-shadow:0 20px 50px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.08); backdrop-filter: blur(18px); }}
.metric {{ font-size:34px; font-weight:800; }} .label {{ color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; }}
.queue {{ display:grid; gap:14px; }} .candidate {{ transition:.2s transform,.2s border-color; }} .candidate:hover {{ transform:translateY(-2px); border-color:rgba(138,92,255,.55); }}
.badges {{ display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }} .badge {{ padding:5px 9px; border-radius:999px; font-size:12px; background:rgba(255,255,255,.09); color:#d7e3ff; }}
.badge.warn {{ background:rgba(255,204,102,.16); color:#ffe2a0; }} .badge.ok {{ background:rgba(66,245,155,.14); color:#9fffd1; }} .badge.danger {{ background:rgba(255,92,138,.15); color:#ffadc4; }}
.preview {{ color:#dce6ff; line-height:1.45; white-space:pre-wrap; }} .muted {{ color:var(--muted); }}
.actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:16px; }} button,.btn {{ border:0; border-radius:14px; padding:10px 14px; color:#07111d; background:linear-gradient(90deg,var(--accent2),#9bdcff); font-weight:750; cursor:pointer; box-shadow:0 10px 24px rgba(32,227,178,.18); }}
button.secondary,.btn.secondary {{ color:var(--text); background:rgba(255,255,255,.10); box-shadow:none; border:1px solid rgba(255,255,255,.12); }} button.danger {{ color:white; background:linear-gradient(90deg,#ff4d79,#ff8a5c); }} button.warn {{ color:#211600; background:linear-gradient(90deg,#ffcc66,#fff0a8); }}
textarea,input,select {{ width:100%; border:1px solid rgba(255,255,255,.14); border-radius:16px; padding:12px; color:var(--text); background:rgba(2,5,16,.62); outline:none; }} textarea {{ min-height:160px; }} label {{ display:block; margin:14px 0 7px; color:#c7d4ef; font-weight:650; }}
input[type=checkbox] {{ width:auto; }} .two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }} .three {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }} @media(max-width:800px){{.two,.three{{grid-template-columns:1fr}} .hero{{display:block}}}}
.notice {{ border:1px solid rgba(32,227,178,.25); background:rgba(32,227,178,.10); padding:12px 14px; border-radius:16px; margin-bottom:16px; color:#cffff1; }}
.code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; white-space:pre-wrap; overflow:auto; max-height:300px; background:rgba(0,0,0,.25); border-radius:16px; padding:12px; }}
.toolbar {{ display:flex; gap:12px; flex-wrap:wrap; align-items:end; justify-content:space-between; }} .inline-form {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }} .inline-form select {{ width:auto; min-width:130px; padding:8px 10px; border-radius:12px; }}
.row-head {{ display:flex; gap:14px; align-items:flex-start; }} .row-head input {{ margin-top:8px; }} details summary {{ cursor:pointer; color:#d7e3ff; }}
</style>
<script>
function toggleAll(source) {{ document.querySelectorAll('input[name="candidate_ids"]').forEach(cb => cb.checked = source.checked); }}
</script>
</head><body><div class='wrap'><div class='hero'><div><div class='brand'><span>Personal Memory Hub</span></div><div class='sub'>Omi-centered Memory Console · evidence → candidate → approved memory</div></div><div class='nav'>{nav}</div></div>{f"<div class='notice'>{esc(notice)}</div>" if notice else ""}{body}</div></body></html>"""


@app.get('/health')
def health():
    return {"ok": True}


def omi_home_body():
    summary = {r['bucket']: r['count'] for r in q("select bucket, count from pmh.memory_status_summary order by bucket")}
    pending = summary.get('new', 0) + summary.get('needs_review', 0) + summary.get('edited', 0)
    active = summary.get('approved', 0) + summary.get('active', 0)
    queued = one("select count(*) as c from pmh.sync_jobs where status in ('queued','pending','ready')") or {'c': 0}
    trash = one("select count(*) as c from pmh.approved_memories where lifecycle_status='deleted'") or {'c': 0}
    return f'''
    <section class='card' style='padding:28px; margin-bottom:20px'>
      <div class='label'>Omi Memory Management</div>
      <h1 style='margin-top:8px'>Omi <span style='background:linear-gradient(90deg,var(--accent2),#d6c7ff,var(--accent)); -webkit-background-clip:text; color:transparent'>Memory Console</span></h1>
      <p class='muted' style='font-size:18px; max-width:780px'>A focused starting point for reviewing Omi-derived memory evidence, approving durable memories, creating new Omi-bound memories, and watching submission/sync activity.</p>
      <div class='actions'>
        <a class='btn' href='/review'>Review candidates</a>
        <a class='btn secondary' href='/memories'>Primary memories</a>
        <a class='btn secondary' href='/omi/pull'>Retrieve from Omi</a>
        <a class='btn secondary' href='http://patriciai-ui.gtgb.io/'>Back to PatriciAI Home</a>
      </div>
    </section>
    <section class='grid'>
      <a class='card' href='/review'><div class='metric'>{esc(pending)}</div><div class='label'>Candidates needing review</div><p class='muted'>Approve, edit, reject, or tune Omi-derived memory candidates before recall.</p></a>
      <a class='card' href='/memories'><div class='metric'>{esc(active)}</div><div class='label'>Primary memories</div><p class='muted'>Browse approved durable memory and submit corrected records back to Omi.</p></a>
      <a class='card' href='/memory/new'><div class='metric'>+</div><div class='label'>New Omi memory</div><p class='muted'>Create a reviewed memory manually and queue it for Omi submission.</p></a>
      <a class='card' href='/submissions'><div class='metric'>{esc(queued['c'])}</div><div class='label'>Queued submissions</div><p class='muted'>Inspect Omi sync jobs and retry or review pending submissions.</p></a>
      <a class='card' href='/trash'><div class='metric'>{esc(trash['c'])}</div><div class='label'>Trash bin</div><p class='muted'>Restore memories that were removed in error.</p></a>
    </section>
    '''


@app.get('/', response_class=HTMLResponse)
@app.get('/home', response_class=HTMLResponse)
@app.get('/memory/home', response_class=HTMLResponse)
def root(user=Depends(auth)):
    return layout('Omi Memory Console', omi_home_body())


@app.get('/review', response_class=HTMLResponse)
def review(request: Request, user=Depends(auth), notice: str = "", limit: int = 50, offset: int = 0):
    limit = clamp_limit(limit)
    summary = q("select bucket, count from pmh.memory_status_summary order by bucket")
    queue = q("select * from pmh.review_queue limit %(limit)s offset %(offset)s", {"limit": limit, "offset": max(offset, 0)})
    metrics = ''.join([f"<div class='card'><div class='metric'>{esc(r['count'])}</div><div class='label'>{esc(r['bucket'])}</div></div>" for r in summary]) or "<div class='card'><div class='metric'>0</div><div class='label'>memory records</div></div>"
    size_opts = ''.join([f"<option value='{n}'{' selected' if n == limit else ''}>{n}</option>" for n in PAGE_SIZE_OPTIONS])
    toolbar = f"""
    <div class='toolbar card'>
      <form class='inline-form' method='get' action='/review'>
        <label style='margin:0'>Show <select name='limit' onchange='this.form.submit()'>{size_opts}</select> memories</label>
      </form>
      <div class='muted'>Quick category/sensitivity changes boost confidence to <strong>0.900</strong>. Full edit + approval sets confidence to <strong>1.000</strong>.</div>
    </div>
    """
    cards = []
    for r in queue:
        cid = r['candidate_id']
        quick = f"""
        <form class='inline-form' method='post' action='/candidate/{cid}/quick'>
          <select name='category'><option value=''>Category…</option>{options(CATEGORY_OPTIONS, r['proposed_category'])}</select>
          <select name='sensitivity'><option value=''>Sensitivity…</option>{options(SENSITIVITY_OPTIONS, r['sensitivity'])}</select>
          <button class='secondary'>Quick update</button>
        </form>
        """
        cards.append(f"""
        <div class='card candidate'>
          <div class='row-head'><input form='bulkForm' type='checkbox' name='candidate_ids' value='{cid}'><div style='flex:1'>
            <div class='label'>{esc(r['source_key'])} · {esc(r['review_status'])}</div>
            <h2><a href='/candidate/{cid}'>{esc(r['proposed_title'] or 'Untitled candidate')}</a></h2>
            <div class='badges'><span class='badge warn'>confidence {esc(r['confidence'])}</span><span class='badge'>{esc(r['sensitivity'])}</span><span class='badge'>{esc(r['proposed_category'])}</span></div>
            <div class='preview'>{esc(r['proposed_content_preview'])}</div>
            <div class='actions'><a class='btn secondary' href='/candidate/{cid}'>Review/Edit</a>{quick}</div>
          </div></div>
        </div>""")
    if cards:
        bulk = f"""
        <form id='bulkForm' method='post' action='/review/bulk'></form>
        <div class='card toolbar'>
          <label style='margin:0'><input type='checkbox' onclick='toggleAll(this)'> Select all on page</label>
          <div class='inline-form'>
            <select form='bulkForm' name='action'><option value='approve'>Approve selected</option><option value='reject'>Deny/reject selected</option><option value='expire'>Expire selected</option><option value='suppress_recall'>Suppress recall selected</option></select>
            <input form='bulkForm' name='notes' placeholder='Optional bulk notes' style='width:260px'>
            <button form='bulkForm'>Apply bulk action</button>
          </div>
        </div>
        <div class='queue'>{''.join(cards)}</div>"""
    else:
        bulk = "<div class='card'><h2>No candidates waiting</h2><p class='muted'>Reviewed memories with confidence 1.000 stay out of this review queue and remain available in Primary Memories.</p></div>"
    body = f"<div class='grid'>{metrics}</div>{toolbar}<h1>Review Queue</h1>{bulk}"
    return layout('Review Queue', body, notice)


@app.post('/review/bulk')
def bulk_action(action: str = Form(...), candidate_ids: List[str] = Form(default=[]), notes: Optional[str] = Form(None), user=Depends(auth)):
    if action not in ('approve', 'reject', 'expire', 'suppress_recall'):
        raise HTTPException(400, 'unsupported bulk action')
    count = 0
    for cid in candidate_ids:
        try:
            exec_one("""
                select pmh.apply_candidate_review(%(candidate_id)s::uuid, %(action)s::text, %(actor)s::text, null, null, null, null, null, null, %(notes)s, %(reject)s, null, null, false) as result
            """, {"candidate_id": cid, "action": action, "actor": f"pmh-ui:{user}", "notes": notes, "reject": notes if action == 'reject' else None})
            count += 1
        except Exception:
            # Continue bulk operations; individual failures can be revisited in the queue.
            pass
    return RedirectResponse(f"/review?notice={html.escape(f'Bulk {action} applied to {count} selected memories')}", status_code=303)


@app.post('/candidate/{candidate_id}/quick')
def candidate_quick(candidate_id: UUID, category: Optional[str] = Form(None), sensitivity: Optional[str] = Form(None), user=Depends(auth)):
    if category and category not in CATEGORY_OPTIONS:
        raise HTTPException(400, 'unsupported category')
    if sensitivity and sensitivity not in SENSITIVITY_OPTIONS:
        raise HTTPException(400, 'unsupported sensitivity')
    exec_one("""
      with before as (select to_jsonb(c) b from pmh.memory_candidates c where candidate_id=%(id)s::uuid), upd as (
        update pmh.memory_candidates
        set proposed_category = coalesce(nullif(%(category)s,''), proposed_category),
            sensitivity = coalesce(nullif(%(sensitivity)s,''), sensitivity),
            confidence = greatest(coalesce(confidence,0), 0.900),
            updated_at = now()
        where candidate_id=%(id)s::uuid and review_status in ('new','needs_review')
        returning *
      )
      insert into pmh.review_actions(candidate_id, action, actor, notes, before_state, after_state)
      select %(id)s::uuid, 'quick_update', %(actor)s, 'Quick category/sensitivity update; confidence boosted to 0.900', before.b, to_jsonb(upd)
      from before, upd
      returning review_action_id
    """, {"id": str(candidate_id), "category": category or '', "sensitivity": sensitivity or '', "actor": f"pmh-ui:{user}"})
    return RedirectResponse('/review?notice=Quick update applied; confidence boosted to 0.900', status_code=303)


@app.get('/candidate/{candidate_id}', response_class=HTMLResponse)
def candidate(candidate_id: UUID, user=Depends(auth)):
    r = one("select c.*, ss.source_key, ss.display_name from pmh.memory_candidates c join pmh.source_systems ss on ss.source_system_id=c.source_system_id where c.candidate_id=%(id)s", {"id": str(candidate_id)})
    if not r:
        raise HTTPException(404, 'candidate not found')
    evidence = esc(json.dumps(r.get('evidence'), indent=2, default=str))
    body = f"""
<div class='card'>
  <div class='label'>{esc(r['source_key'])} · {esc(r['review_status'])}</div>
  <h1>{esc(r['proposed_title'])}</h1>
  <div class='badges'><span class='badge warn'>confidence {esc(r['confidence'])}</span><span class='badge'>{esc(r['sensitivity'])}</span><span class='badge'>{esc(r['proposed_category'])}</span><span class='badge {'ok' if r['recall_eligible'] else 'danger'}'>recall {'on' if r['recall_eligible'] else 'off'}</span></div>
</div>
<form class='card' method='post' action='/candidate/{candidate_id}/action'>
  <div class='three'><div><label>Title</label><input name='title' value='{esc(r['proposed_title'])}'></div><div><label>Category</label><select name='category'>{options(CATEGORY_OPTIONS, r['proposed_category'])}</select></div><div><label>Omi visibility</label><select name='omi_visibility'>{options(OMI_VISIBILITY_OPTIONS, (r.get('evidence') or {}).get('visibility') if isinstance(r.get('evidence'), dict) else 'private')}</select></div></div>
  <label>Memory content</label><textarea name='content'>{esc(r['proposed_content'])}</textarea>
  <div class='two'><div><label>Sensitivity</label><select name='sensitivity'>{options(SENSITIVITY_OPTIONS, r['sensitivity'])}</select></div><div><label>Omi create supports</label><div class='muted'>content, category, visibility, tags</div></div></div>{tag_editor(r['proposed_tags'] or [])}
  <label>Reviewer notes</label><textarea name='notes' style='min-height:80px'></textarea>
  <div class='badges'><label><input type='checkbox' name='recall_eligible' value='true'{checked(r['recall_eligible'])}> Recall eligible after approval</label><label><input type='checkbox' name='sync_to_source' value='true'> Queue Omi sync-back after final confirmation</label></div>
  <div class='actions'>
    <button name='action' value='approve'>Approve as-is</button>
    <button name='action' value='correct_and_approve'>Save edits + Approve (confidence 1.000)</button>
    <button class='danger' name='action' value='reject'>Deny / Reject</button>
    <button class='warn' name='action' value='expire'>Expire</button>
    <button class='secondary' name='action' value='mark_sensitive'>Mark Sensitive</button>
    <button class='secondary' name='action' value='suppress_recall'>Suppress Recall</button>
  </div>
</form>
<div class='card'><h2>Evidence</h2><div class='code'>{evidence}</div></div>
"""
    return layout('Candidate', body)


def confirm_candidate_page(candidate_id, form):
    fields = ''.join(hidden(k, v) for k, v in form.items()) + hidden('confirmed', 'true')
    body = f"""
    <div class='card'>
      <h1>Are you sure you wanna do this?</h1>
      <p class='muted'>This will approve the memory locally and queue an Omi sync-back job. Nothing is submitted to Omi until this final confirmation.</p>
      <form method='post' action='/candidate/{candidate_id}/action'>{fields}<div class='actions'><button>Yes, queue Omi sync-back</button><a class='btn secondary' href='/candidate/{candidate_id}'>Cancel</a></div></form>
    </div>"""
    return layout('Confirm Omi Sync', body)


@app.post('/candidate/{candidate_id}/action', response_class=HTMLResponse)
async def candidate_action(request: Request, candidate_id: UUID, user=Depends(auth)):
    form = await request.form()
    action = form.get('action') or ''
    sync = form.get('sync_to_source') == 'true'
    confirmed = form.get('confirmed') == 'true'
    if sync and not confirmed and action in ('approve', 'correct_and_approve'):
        return confirm_candidate_page(candidate_id, form)
    tags = parse_tags_from_form(form)
    ensure_tags_registered(tags, f"pmh-ui:{user}")
    row = exec_one("""
        select pmh.apply_candidate_review(
          %(candidate_id)s::uuid, %(action)s::text, %(actor)s::text,
          %(title)s::text, %(content)s::text, %(category)s::text,
          %(tags)s::text[], %(sensitivity)s::text, %(recall)s::boolean,
          %(notes)s::text, %(rejection_reason)s::text,
          null::timestamptz, null::timestamptz, %(sync)s::boolean
        ) as result
    """, {
        "candidate_id": str(candidate_id), "action": action, "actor": f"pmh-ui:{user}",
        "title": form.get('title'), "content": form.get('content'), "category": form.get('category'), "tags": tags,
        "sensitivity": form.get('sensitivity'), "recall": form.get('recall_eligible') == 'true', "notes": form.get('notes'),
        "rejection_reason": form.get('notes') if action == 'reject' else None, "sync": sync and confirmed
    })
    result = row['result']
    if action in ('approve', 'correct_and_approve') and result.get('approved_memory_id'):
        exec_one("update pmh.approved_memories set omi_visibility=%(visibility)s where approved_memory_id=%(id)s::uuid returning approved_memory_id", {"visibility": form.get('omi_visibility') or 'private', "id": result.get('approved_memory_id')})
    return RedirectResponse(f"/review?notice={html.escape('Review action applied: ' + str(result))}", status_code=303)


@app.get('/memories', response_class=HTMLResponse)
def memories(user=Depends(auth), notice: str = '', limit: int = 50, offset: int = 0):
    limit = clamp_limit(limit)
    rows = q("""
      select * from pmh.approved_memories
      where lifecycle_status = 'active'
      order by updated_at desc, approved_at desc
      limit %(limit)s offset %(offset)s
    """, {"limit": limit, "offset": max(offset, 0)})
    size_opts = ''.join([f"<option value='{n}'{' selected' if n == limit else ''}>{n}</option>" for n in PAGE_SIZE_OPTIONS])
    toolbar = f"<div class='toolbar card'><form class='inline-form' method='get'><label style='margin:0'>Show <select name='limit' onchange='this.form.submit()'>{size_opts}</select> memories</label></form><div class='muted'>Primary approved memory interface. Edited memories are saved at confidence 1.000.</div></div>"
    cards = ''.join([f"""
      <div class='card candidate'><div class='label'>{esc(r['category'])} · {esc(r['sensitivity'])} · Omi {esc(r.get('omi_visibility') or 'private')}</div><h2>{esc(r['title'] or 'Untitled memory')}</h2><div class='badges'><span class='badge ok'>confidence {esc(r['confidence'])}</span><span class='badge {'ok' if r['recall_eligible'] else 'danger'}'>recall {'on' if r['recall_eligible'] else 'off'}</span></div><div class='preview'>{esc(r['content'])}</div><div class='actions'><a class='btn secondary' href='/memory/{r['approved_memory_id']}/edit'>Edit</a><a class='btn' href='/memory/{r['approved_memory_id']}/submit'>Submit to Omi</a><form method='post' action='/memory/{r['approved_memory_id']}/trash' onsubmit="return confirm('Move this memory to trash? If it exists in Omi, it will be deleted there now.');"><button class='danger'>Trash</button></form></div></div>
    """ for r in rows]) or "<div class='card'><h2>No approved memories yet</h2><p class='muted'>Approved memories will appear here after review.</p></div>"
    return layout('Primary Memories', f"{toolbar}<h1>Primary Memories</h1><div class='queue'>{cards}</div>", notice)


@app.get('/memory/{memory_id}/edit', response_class=HTMLResponse)
def memory_edit(memory_id: UUID, user=Depends(auth)):
    r = one("select * from pmh.approved_memories where approved_memory_id=%(id)s", {"id": str(memory_id)})
    if not r:
        raise HTTPException(404, 'memory not found')
    body = f"""
<form class='card' method='post' action='/memory/{memory_id}/edit'>
  <h1>Edit Approved Memory</h1>
  <div class='three'><div><label>Title</label><input name='title' value='{esc(r['title'])}'></div><div><label>Category</label><select name='category'>{options(CATEGORY_OPTIONS, r['category'])}</select></div><div><label>Omi visibility</label><select name='omi_visibility'>{options(OMI_VISIBILITY_OPTIONS, r.get('omi_visibility') or 'private')}</select></div></div>
  <label>Memory content</label><textarea name='content'>{esc(r['content'])}</textarea>
  <div class='two'><div><label>Sensitivity</label><select name='sensitivity'>{options(SENSITIVITY_OPTIONS, r['sensitivity'])}</select></div><div><label>Omi create supports</label><div class='muted'>content, category, visibility, tags</div></div></div>{tag_editor(r['tags'] or [])}
  <div class='badges'><label><input type='checkbox' name='recall_eligible' value='true'{checked(r['recall_eligible'])}> Recall eligible</label><label><input type='checkbox' name='sync_to_source' value='true'> Queue Omi sync-back after final confirmation</label></div>
  <label>Notes</label><textarea name='notes' style='min-height:80px'></textarea>
  <div class='actions'><button>Save edited memory (confidence 1.000)</button><a class='btn' href='/memory/{memory_id}/submit'>Submit to Omi</a><a class='btn secondary' href='/memories'>Cancel</a></div>
  </form>
  <form class='card' method='post' action='/memory/{memory_id}/trash' onsubmit="return confirm('Move this memory to trash? If it exists in Omi, it will be deleted there now.');"><button class='danger'>Move to Trash</button></form>
  <form style='display:none'>
</form>"""
    return layout('Edit Memory', body)


def confirm_memory_page(memory_id, form):
    fields = ''.join(hidden(k, v) for k, v in form.items()) + hidden('confirmed', 'true')
    body = f"""
    <div class='card'>
      <h1>Are you sure you wanna do this?</h1>
      <p class='muted'>This will save the approved memory edit and queue an Omi sync-back job. Nothing is submitted to Omi until this final confirmation.</p>
      <form method='post' action='/memory/{memory_id}/edit'>{fields}<div class='actions'><button>Yes, queue Omi sync-back</button><a class='btn secondary' href='/memory/{memory_id}/edit'>Cancel</a></div></form>
    </div>"""
    return layout('Confirm Omi Sync', body)


@app.post('/memory/{memory_id}/edit', response_class=HTMLResponse)
async def memory_update(request: Request, memory_id: UUID, user=Depends(auth)):
    form = await request.form()
    sync = form.get('sync_to_source') == 'true'
    confirmed = form.get('confirmed') == 'true'
    if sync and not confirmed:
        return confirm_memory_page(memory_id, form)
    tags = parse_tags_from_form(form)
    ensure_tags_registered(tags, f"pmh-ui:{user}")
    sensitivity = form.get('sensitivity') or 'normal'
    recall = form.get('recall_eligible') == 'true'
    if sensitivity in ('sensitive', 'restricted'):
        recall = False
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("select * from pmh.approved_memories where approved_memory_id=%s for update", (str(memory_id),))
            before = cur.fetchone()
            if not before:
                raise HTTPException(404, 'memory not found')
            cur.execute("""
              update pmh.approved_memories
              set title=%(title)s, content=%(content)s, category=%(category)s, tags=%(tags)s::text[], sensitivity=%(sensitivity)s, omi_visibility=%(omi_visibility)s,
                  recall_eligible=%(recall)s, confidence=1.000, updated_at=now(), review_notes=%(notes)s
              where approved_memory_id=%(id)s::uuid
              returning *
            """, {"id": str(memory_id), "title": form.get('title'), "content": form.get('content'), "category": form.get('category'), "tags": tags, "sensitivity": sensitivity, "omi_visibility": form.get('omi_visibility') or 'private', "recall": recall, "notes": form.get('notes')})
            after = cur.fetchone()
            cur.execute("""
              insert into pmh.review_actions(approved_memory_id, action, actor, notes, before_state, after_state)
              values (%(id)s::uuid, 'edit_approved_memory', %(actor)s, %(notes)s, %(before)s::jsonb, %(after)s::jsonb)
            """, {"id": str(memory_id), "actor": f"pmh-ui:{user}", "notes": form.get('notes'), "before": json.dumps(dict(before), default=str), "after": json.dumps(dict(after), default=str)})
            if sync and confirmed:
                cur.execute("""
                  insert into pmh.sync_jobs(source_system_id, local_record_type, local_record_id, action, requested_by, request_payload)
                  values (%(source_system_id)s, 'approved_memory', %(id)s::uuid, 'update', %(actor)s, %(payload)s::jsonb)
                """, {"source_system_id": after['source_system_id'], "id": str(memory_id), "actor": f"pmh-ui:{user}", "payload": json.dumps({"approved_memory_id": str(memory_id), "reason": "approved_memory_edit_confirmed"})})
            conn.commit()
    return RedirectResponse('/memories?notice=Approved memory updated with confidence 1.000', status_code=303)


@app.get('/memory/{memory_id}/submit', response_class=HTMLResponse)
def memory_submit_confirm(memory_id: UUID, user=Depends(auth)):
    r = one("select * from pmh.approved_memories where approved_memory_id=%(id)s", {"id": str(memory_id)})
    if not r:
        raise HTTPException(404, 'memory not found')
    # Resolve whether this will replace an existing Omi memory or create a new one.
    external_id = None
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            external_id = get_omi_external_id(cur, r)
    mode = 'Replace existing Omi memory: create corrected memory, then delete old' if external_id else 'Create new Omi memory (no original Omi ID found)'
    body = f"""
    <div class='card'>
      <h1>Are you sure you wanna do this?</h1>
      <p class='muted'>This will submit the approved PMH memory to the Omi platform now. Existing Omi memories are replaced: PMH creates the corrected memory with all POST-supported fields, verifies the new Omi ID, then deletes the superseded original.</p>
      <div class='badges'><span class='badge warn'>{esc(mode)}</span>{f"<span class='badge'>Omi ID {esc(external_id)}</span>" if external_id else ""}<span class='badge'>{esc(r['category'])}</span><span class='badge'>Omi {esc(r.get('omi_visibility') or 'private')}</span><span class='badge'>{esc(r['sensitivity'])}</span></div>
      <h2>{esc(r['title'] or 'Untitled memory')}</h2>
      <div class='preview'>{esc(r['content'])}</div>
      <form method='post' action='/memory/{memory_id}/submit'>
        <div class='actions'><button>Yes, submit to Omi now</button><a class='btn secondary' href='/memory/{memory_id}/edit'>Cancel</a></div>
      </form>
    </div>
    """
    return layout('Confirm Submit to Omi', body)


@app.post('/memory/{memory_id}/submit')
def memory_submit(memory_id: UUID, user=Depends(auth)):
    try:
        result = submit_memory_to_omi(memory_id, f"pmh-ui:{user}")
    except Exception as e:
        return RedirectResponse(f"/memory/{memory_id}/edit?notice={html.escape('Omi submit failed: ' + str(e))}", status_code=303)
    return RedirectResponse(f"/memories?notice={html.escape('Submitted to Omi: ' + json.dumps(result))}", status_code=303)


@app.get('/omi/pull', response_class=HTMLResponse)
def omi_pull_form(user=Depends(auth), notice: str = ''):
    available_tags = get_available_tags()
    tag_checks = ''.join([f"<label style='margin:6px 10px 6px 0; display:inline-flex; gap:6px; align-items:center'><input type='checkbox' name='filter_tags' value='{esc(t)}'> {esc(t)}</label>" for t in available_tags]) or "<p class='muted'>No local tag registry yet. Pulling without tag filters will populate review candidates.</p>"
    body = f"""
    <div class='card'>
      <h1>Retrieve more memories from Omi</h1>
      <p class='muted'>Choose how many unsynced memories you want. PMH scans Omi from newest to older and skips anything already pulled or created by PMH sync-back.</p>
      <form method='post' action='/omi/pull'>
        <div class='three'>
          <div><label>How many unsynced memories?</label><input name='limit' type='number' min='1' max='100' value='25'></div>
          <div><label>Category</label><select name='category_filter'><option value=''>Any category</option>{options(CATEGORY_OPTIONS, '')}</select></div>
          <div><label>Visibility</label><select name='visibility_filter'><option value=''>Any visibility</option>{options(OMI_VISIBILITY_OPTIONS, '')}</select></div>
        </div>
        <div class='two'>
          <div><label>Reviewed in Omi</label><select name='reviewed_filter'><option value=''>Any</option><option value='true'>Reviewed only</option><option value='false'>Unreviewed only</option></select></div>
          <div><label>Maximum Omi records to scan</label><select name='max_scan'><option value='250'>250</option><option value='500' selected>500</option><option value='1000'>1000</option><option value='2000'>2000</option></select></div>
        </div>
        <details class='card' style='margin-top:16px'><summary><strong>Filter by tags</strong> <span class='muted'>optional; all selected tags must be present</span></summary><div class='badges' style='margin-top:12px'>{tag_checks}</div></details>
        <div class='actions'><button>Retrieve unsynced memories</button></div>
      </form>
    </div>
    """
    return layout('Retrieve from Omi', body, notice)


def omi_memory_matches_filters(mem, category_filter='', visibility_filter='', reviewed_filter='', filter_tags=None):
    filter_tags = [t.lower() for t in (filter_tags or []) if t]
    if category_filter and (mem.get('category') or '') != category_filter:
        return False
    if visibility_filter and (mem.get('visibility') or '') != visibility_filter:
        return False
    if reviewed_filter:
        expected = reviewed_filter == 'true'
        if bool(mem.get('reviewed')) != expected:
            return False
    if filter_tags:
        mem_tags = {clean_tag(t).lower() for t in (mem.get('tags') or []) if clean_tag(t)}
        if not all(t in mem_tags for t in filter_tags):
            return False
    return True


@app.post('/omi/pull')
async def omi_pull(request: Request, user=Depends(auth)):
    form = await request.form()
    limit = max(1, min(int(form.get('limit') or 25), 100))
    max_scan = max(limit, min(int(form.get('max_scan') or 500), 2000))
    category_filter = form.get('category_filter') or ''
    visibility_filter = form.get('visibility_filter') or ''
    reviewed_filter = form.get('reviewed_filter') or ''
    filter_tags = [clean_tag(t) for t in form.getlist('filter_tags') if clean_tag(t)]
    page_size = min(100, max(25, limit))
    inserted = skipped = candidates = scanned = matched = 0
    offset = 0
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            source_id = get_source_system_id(cur, 'omi')
            while inserted < limit and scanned < max_scan:
                qs = f'?limit={page_size}&offset={offset}'
                # If Omi supports category server-side filtering this narrows the API page;
                # local filtering below remains the authority either way.
                if category_filter:
                    qs += '&categories=' + urllib.request.quote(category_filter)
                status, memories = omi_request('GET', '/v1/dev/user/memories' + qs)
                if not isinstance(memories, list):
                    raise HTTPException(502, 'Unexpected Omi memories response')
                if not memories:
                    break
                for mem in memories:
                    scanned += 1
                    if scanned > max_scan or inserted >= limit:
                        break
                    if not omi_memory_matches_filters(mem, category_filter, visibility_filter, reviewed_filter, filter_tags):
                        continue
                    matched += 1
                    external_id = str(mem.get('id') or '').strip()
                    if not external_id:
                        skipped += 1
                        continue
                    cur.execute("""
                      select 1 where exists (select 1 from pmh.raw_events where source_system_id=%s and external_memory_id=%s)
                         or exists (select 1 from pmh.external_refs where source_system_id=%s and external_id=%s and sync_status in ('seen','synced','pending','drifted','conflict'))
                    """, (source_id, external_id, source_id, external_id))
                    if cur.fetchone():
                        skipped += 1
                        continue
                    payload_hash = stable_hash(mem)
                    cur.execute("""
                      insert into pmh.raw_events(source_system_id, external_memory_id, event_type, event_timestamp, idempotency_key, payload_hash, payload, ingest_status, notes)
                      values (%s,%s,'omi.memory_api_pull',coalesce((%s)::timestamptz, now()),%s,%s,%s::jsonb,'candidate_created','Pulled from Omi via PMH UI')
                      on conflict do nothing
                      returning raw_event_id
                    """, (source_id, external_id, mem.get('updated_at') or mem.get('created_at'), f'omi:memory_api_pull:{external_id}', payload_hash, json.dumps(mem)))
                    row = cur.fetchone()
                    if not row:
                        skipped += 1
                        continue
                    raw_event_id = row['raw_event_id']
                    content = mem.get('content') or ''
                    tags = unique_keep_order([clean_tag(t) for t in (mem.get('tags') or []) if clean_tag(t)])[:32]
                    evidence = {
                        'source': 'omi_developer_api',
                        'external_memory_id': external_id,
                        'created_at': mem.get('created_at'),
                        'updated_at': mem.get('updated_at'),
                        'visibility': mem.get('visibility'),
                        'reviewed_in_omi': mem.get('reviewed'),
                        'raw_event_id': str(raw_event_id),
                        'pull_filters': {'category': category_filter, 'visibility': visibility_filter, 'reviewed': reviewed_filter, 'tags': filter_tags},
                    }
                    cur.execute("""
                      insert into pmh.memory_candidates(source_system_id, raw_event_id, proposed_title, proposed_content, proposed_category, proposed_tags, confidence, sensitivity, review_status, recall_eligible, evidence)
                      values (%s,%s,%s,%s,%s,%s::text[],0.750,%s,'needs_review',false,%s::jsonb)
                    """, (source_id, raw_event_id, (content[:80] + '…') if len(content) > 80 else content, content, mem.get('category') or 'system', tags, sensitivity_for_content(content), json.dumps(evidence)))
                    cur.execute("""
                      insert into pmh.external_refs(source_system_id, local_record_type, local_record_id, external_id, last_seen_at, sync_status, meta)
                      values (%s,'raw_event',%s,%s,now(),'seen',%s::jsonb)
                      on conflict do nothing
                    """, (source_id, raw_event_id, external_id, json.dumps({'pulled_by': f'pmh-ui:{user}', 'event_type': 'omi.memory_api_pull'})))
                    inserted += 1
                    candidates += 1
                offset += len(memories)
                if len(memories) < page_size:
                    break
            conn.commit()
    notice = f'Omi pull complete: {inserted} new, {skipped} skipped, {candidates} candidates created, {scanned} scanned, {matched} matched filters'
    return RedirectResponse(f"/review?notice={html.escape(notice)}", status_code=303)


@app.get('/memory/new', response_class=HTMLResponse)
def new_memory_form(user=Depends(auth), notice: str = ''):
    body = f"""
    <form class='card' method='post' action='/memory/new'>
      <h1>Create new memory</h1>
      <p class='muted'>Creates a PMH-approved memory from scratch and places it into the submission queue. It will not touch Omi until submitted.</p>
      <div class='three'><div><label>Title</label><input name='title'></div><div><label>Category</label><select name='category'>{options(CATEGORY_OPTIONS, 'system')}</select></div><div><label>Omi visibility</label><select name='omi_visibility'>{options(OMI_VISIBILITY_OPTIONS, 'private')}</select></div></div>
      <label>Memory content</label><textarea name='content'></textarea>
      <div class='two'><div><label>Sensitivity</label><select name='sensitivity'>{options(SENSITIVITY_OPTIONS, 'normal')}</select></div><div class='muted' style='align-self:end'>Tag limits: 5 new per edit, 32 per memory, 256 global.</div></div>
      {tag_editor([])}
      <label>Notes</label><textarea name='notes' style='min-height:80px'></textarea>
      <div class='badges'><label><input type='checkbox' name='recall_eligible' value='true'> Recall eligible</label></div>
      <div class='actions'><button>Create and queue for Omi submission</button></div>
    </form>
    """
    return layout('Create Memory', body, notice)


@app.post('/memory/new')
async def new_memory_create(request: Request, user=Depends(auth)):
    form = await request.form()
    content = (form.get('content') or '').strip()
    if not content:
        raise HTTPException(400, 'memory content is required')
    tags = parse_tags_from_form(form)
    ensure_tags_registered(tags, f'pmh-ui:{user}')
    sensitivity = form.get('sensitivity') or 'normal'
    recall = form.get('recall_eligible') == 'true'
    if sensitivity in ('sensitive', 'restricted'):
        recall = False
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            source_id = get_source_system_id(cur, 'manual')
            cur.execute("""
              insert into pmh.approved_memories(source_system_id, title, content, category, tags, confidence, sensitivity, recall_eligible, source_of_truth, review_notes, approved_by, omi_visibility)
              values (%s,%s,%s,%s,%s::text[],1.000,%s,%s,'personal_memory_hub',%s,%s,%s)
              returning approved_memory_id
            """, (source_id, form.get('title'), content, form.get('category') or 'system', tags, sensitivity, recall, form.get('notes'), f'pmh-ui:{user}', form.get('omi_visibility') or 'private'))
            memory_id = cur.fetchone()['approved_memory_id']
            cur.execute("""
              insert into pmh.sync_jobs(source_system_id, local_record_type, local_record_id, action, status, requested_by, request_payload)
              values (%s,'approved_memory',%s,'create','queued',%s,%s::jsonb)
            """, (source_id, memory_id, f'pmh-ui:{user}', json.dumps({'reason': 'manual_memory_created_from_ui', 'visibility': form.get('omi_visibility') or 'private'})))
            conn.commit()
    return RedirectResponse('/submissions?notice=New memory created and queued for Omi submission', status_code=303)


@app.get('/submissions', response_class=HTMLResponse)
def submissions(user=Depends(auth), notice: str = '', limit: int = 50):
    limit = clamp_limit(limit)
    rows = q("""
      select j.*, m.title, m.content, m.category, m.omi_visibility, m.sensitivity
      from pmh.sync_jobs j
      left join pmh.approved_memories m on m.approved_memory_id = j.local_record_id
      where j.local_record_type='approved_memory' and j.status='queued'
      order by j.created_at desc
      limit %(limit)s
    """, {'limit': limit})
    cards = ''.join([f"""
      <div class='card candidate'><div class='label'>{esc(r['action'])} · {esc(r['category'])} · Omi {esc(r['omi_visibility'])}</div><h2>{esc(r['title'] or 'Untitled memory')}</h2><div class='preview'>{esc(r['content'])}</div><div class='actions'><a class='btn' href='/memory/{r['local_record_id']}/submit'>Review & Submit to Omi</a><a class='btn secondary' href='/memory/{r['local_record_id']}/edit'>Edit first</a><form method='post' action='/memory/{r['local_record_id']}/trash' onsubmit="return confirm('Remove this queued memory and move it to trash?');"><button class='danger'>Trash</button></form></div></div>
    """ for r in rows]) or "<div class='card'><h2>No queued submissions</h2><p class='muted'>New scratch memories and future queued syncs will appear here.</p></div>"
    return layout('Submission Queue', f"<h1>Submission Queue</h1>{cards}", notice)


@app.post('/memory/{memory_id}/trash')
def memory_trash(memory_id: UUID, user=Depends(auth)):
    result = move_memory_to_trash(memory_id, f'pmh-ui:{user}')
    return RedirectResponse(f"/trash?notice={html.escape('Memory moved to trash: ' + json.dumps(result))}", status_code=303)


@app.get('/trash', response_class=HTMLResponse)
def trash_bin(user=Depends(auth), notice: str = '', limit: int = 100):
    rows = q("""
      select m.*,
        (select external_id from pmh.external_refs er where er.local_record_id=m.approved_memory_id and er.sync_status='deleted_remote' order by er.last_synced_at desc nulls last limit 1) as deleted_external_id
      from pmh.approved_memories m
      where m.lifecycle_status='deleted'
      order by m.updated_at desc nulls last, m.created_at desc
      limit %(limit)s
    """, {'limit': min(clamp_limit(limit), 100)})
    cards = ''.join([f"""
      <div class='card candidate'><div class='label'>trashed · {esc(r['category'])} · {esc(r['sensitivity'])}</div><h2>{esc(r['title'] or 'Untitled memory')}</h2><div class='badges'>{f"<span class='badge danger'>Removed from Omi {esc(r['deleted_external_id'])}</span>" if r.get('deleted_external_id') else "<span class='badge'>Local only / no Omi ID</span>"}</div><div class='preview'>{esc(r['content'])}</div><div class='actions'><form method='post' action='/memory/{r['approved_memory_id']}/restore'><button>Restore & Queue New Omi Memory</button></form></div></div>
    """ for r in rows]) or "<div class='card'><h2>Trash is empty</h2><p class='muted'>Deleted memories will appear here and can be restored later.</p></div>"
    return layout('Trash Bin', f"<h1>Trash Bin</h1><p class='muted'>Restoring a memory queues it to create a brand-new Omi memory; old Omi IDs remain marked deleted.</p>{cards}", notice)


@app.post('/memory/{memory_id}/restore')
def memory_restore(memory_id: UUID, user=Depends(auth)):
    result = restore_memory_from_trash(memory_id, f'pmh-ui:{user}')
    return RedirectResponse(f"/submissions?notice={html.escape('Memory restored: ' + json.dumps(result))}", status_code=303)

# Compatibility routes for PatriciAI proxy paths that may strip the /memory prefix.
@app.get('/{memory_id}/edit', response_class=HTMLResponse)
def memory_edit_compat(memory_id: UUID, user=Depends(auth)):
    return memory_edit(memory_id, user)

@app.post('/{memory_id}/edit', response_class=HTMLResponse)
async def memory_update_compat(request: Request, memory_id: UUID, user=Depends(auth)):
    return await memory_update(request, memory_id, user)

@app.get('/{memory_id}/submit', response_class=HTMLResponse)
def memory_submit_confirm_compat(memory_id: UUID, user=Depends(auth)):
    return memory_submit_confirm(memory_id, user)

@app.post('/{memory_id}/trash')
def memory_trash_compat(memory_id: UUID, user=Depends(auth)):
    return memory_trash(memory_id, user)

@app.post('/{memory_id}/restore')
def memory_restore_compat(memory_id: UUID, user=Depends(auth)):
    return memory_restore(memory_id, user)

@app.post('/{memory_id}/submit')
def memory_submit_compat(memory_id: UUID, user=Depends(auth)):
    return memory_submit(memory_id, user)
