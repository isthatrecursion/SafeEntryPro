from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_select, db_insert, db_update
import random
from datetime import datetime

router = APIRouter()


class VisitorRegister(BaseModel):
    name: str
    email: str
    phone: str
    company: str
    department: str
    visitor_type: str = ""
    host_name: str
    host_designation: str = ""
    purpose: str
    visit_date: str
    time_slot: str
    notes: str = ""
    industry: str = ""


@router.post("/register")
def register_visitor(payload: VisitorRegister):
    try:
        # --- Check 1: Exact duplicate (same phone + visit_date + time_slot) ---
        exact_matches = db_select(
            "visitors",
            {
                "phone": f"eq.{payload.phone}",
                "visit_date": f"eq.{payload.visit_date}",
                "time_slot": f"eq.{payload.time_slot}",
            },
        ) or []

        if exact_matches:
            return {
                "success": False,
                "duplicate": True,
                "message": "You are already registered for this date and time slot.",
                "existing_id": exact_matches[0]["id"],
            }

        # --- Check 2: Same-day visit (same phone + visit_date, any slot) ---
        same_day_matches = db_select(
            "visitors",
            {
                "phone": f"eq.{payload.phone}",
                "visit_date": f"eq.{payload.visit_date}",
            },
        ) or []

        same_day_warning = bool(same_day_matches)

        # --- Proceed with insert ---
        today = datetime.now().strftime("%Y%m%d")
        rand = random.randint(1000, 9999)
        visit_id = f"VIS-{today}-{rand}"

        db_insert(
            "visitors",
            {
                "id": visit_id,
                "name": payload.name,
                "email": payload.email,
                "phone": payload.phone,
                "company": payload.company,
                "department": payload.department,
                "visitor_type": payload.visitor_type,
                "host_name": payload.host_name,
                "host_designation": payload.host_designation,
                "purpose": payload.purpose,
                "visit_date": payload.visit_date,
                "time_slot": payload.time_slot,
                "notes": payload.notes,
                "industry": payload.industry,
                "status": "pending",
            },
        )

        response = {"success": True, "visit_id": visit_id}

        if same_day_warning:
            response["same_day_warning"] = True
            response["warning_message"] = "You have another visit scheduled today."

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visitor/{visit_id}")
def get_visitor(visit_id: str):
    try:
        rows = db_select("visitors", {"id": f"eq.{visit_id}"}) or []

        if not rows:
            raise HTTPException(status_code=404, detail="Visitor not found")

        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class VisitorUpdate(BaseModel):
    status: str = None
    face_match: int = None
    otp_verified: bool = None
    briefing_complete: bool = None
    pass_id: str = None
    manual_review: bool = None


@router.put("/visitor/{visit_id}")
def update_visitor(visit_id: str, payload: VisitorUpdate):
    try:
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        db_update("visitors", "id", visit_id, update_data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PhoneCheck(BaseModel):
    phone: str


def _parse_iso_datetime(value: str) -> datetime:
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


@router.post("/check-return")
def check_return(payload: PhoneCheck):
    try:
        rows = db_select("visitors", {"phone": f"eq.{payload.phone}"}) or []

        if not rows:
            return {"is_new": True}

        def _created_at_key(rec):
            raw = rec.get("created_at")
            if not raw:
                return datetime.min
            try:
                return _parse_iso_datetime(raw)
            except Exception:
                return datetime.min

        rows_sorted = sorted(rows, key=_created_at_key, reverse=True)
        created_at = rows_sorted[0].get("created_at")
        if not created_at:
            return {"is_new": True}

        try:
            last_dt = _parse_iso_datetime(created_at)
        except Exception:
            return {"is_new": True}

        days = (datetime.utcnow() - last_dt).days

        if days <= 7:
            return {"is_frequent": True, "days_since": days}
        if days <= 30:
            return {"is_return": True, "days_since": days}
        return {"is_new": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
