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
        today = datetime.now().strftime("%Y%m%d")
        rand = random.randint(1000, 9999)
        visit_id = f"VIS-{today}-{rand}"

        data = payload.model_dump()
        data["id"] = visit_id
        data["status"] = "pending"

        supabase.table("visitors").insert(data).execute()

        return {"success": True, "visit_id": visit_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/visitor/{visit_id}")
def get_visitor(visit_id: str):
    try:
        res = supabase.table("visitors").select("*").eq("id", visit_id).execute()
        rows = getattr(res, "data", None) or []

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
        supabase.table("visitors").update(update_data).eq("id", visit_id).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PhoneCheck(BaseModel):
    phone: str


@router.post("/check-return")
def check_return(payload: PhoneCheck):
    try:
        res = (
            supabase.table("visitors")
            .select("*")
            .eq("phone", payload.phone)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(res, "data", None) or []

        if not rows:
            return {"is_new": True}

        created_at = rows[0].get("created_at")
        if not created_at:
            return {"is_new": True}

        created_at_str = str(created_at).replace("Z", "+00:00")
        last_dt = datetime.fromisoformat(created_at_str)
        now_dt = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()
        days = (now_dt - last_dt).days

        if days <= 7:
            return {"is_frequent": True, "days_since": days}
        if days <= 30:
            return {"is_return": True, "days_since": days}
        return {"is_new": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
