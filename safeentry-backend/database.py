import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def db_select(table, filters=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = filters or {}
    r = httpx.get(url, headers=HEADERS, params=params)
    return r.json()

def db_insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = httpx.post(url, headers=HEADERS, json=data)
    return r.json()

def db_update(table, match_col, match_val, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {match_col: f"eq.{match_val}"}
    r = httpx.patch(url, headers=HEADERS, params=params, json=data)
    return r.json()

def db_delete(table, match_col, match_val):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = {match_col: f"eq.{match_val}"}
    r = httpx.delete(url, headers=HEADERS, params=params)
    return r.status_code