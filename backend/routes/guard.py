from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_select, db_insert, db_update
from datetime import datetime
from typing import Optional

router = APIRouter()


class QRScan(BaseModel):
    qr_data: str


@router.post("/guard/scan")
def guard_scan(payload: QRScan):
    try:
        parts = (payload.qr_data or "").split("|")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid QR code")

        pass_id = parts[1]
        visit_id = parts[2]

        pass_result = db_select("passes", {"pass_id": f"eq.{pass_id}"})
        if not pass_result:
            return {"found": False, "message": "Invalid or expired pass"}
        pass_data = pass_result[0]

        visitor_result = db_select("visitors", {"id": f"eq.{visit_id}"})
        if not visitor_result:
            return {"found": False, "message": "Visitor not found"}
        visitor = visitor_result[0]

        blacklist_result = db_select("blacklist", {"phone": f"eq.{visitor.get('phone','')}"})
        is_blacklisted = len(blacklist_result) > 0

        return {
            "found": True,
            "visitor": {
                "name": visitor["name"],
                "company": visitor["company"],
                "department": visitor["department"],
                "host_name": visitor["host_name"],
                "visitor_type": visitor.get("visitor_type", ""),
                "phone": visitor["phone"],
            },
            "pass": {
                "pass_id": pass_data["pass_id"],
                "visit_date": pass_data["visit_date"],
                "time_slot": pass_data["time_slot"],
                "permitted_zones": pass_data["permitted_zones"],
                "is_active": pass_data["is_active"],
            },
            "briefing_complete": visitor.get("briefing_complete", False),
            "face_match": visitor.get("face_match", 0),
            "otp_verified": visitor.get("otp_verified", False),
            "is_blacklisted": is_blacklisted,
            "current_status": visitor.get("status", "pending"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GuardAction(BaseModel):
    pass_id: str
    visit_id: str
    action: str
    guard_note: Optional[str] = ""


@router.post("/guard/action")
def guard_action(payload: GuardAction):
    try:
        logged_at = datetime.utcnow().isoformat()
        db_insert(
            "entry_logs",
            {
                "visit_id": payload.visit_id,
                "pass_id": payload.pass_id,
                "action": payload.action,
                "guard_note": payload.guard_note or "",
                "logged_at": logged_at,
            },
        )

        if payload.action == "allow":
            db_update("visitors", "id", payload.visit_id, {"status": "checked_in"})
        if payload.action == "deny":
            db_update("passes", "pass_id", payload.pass_id, {"is_active": False})
            db_update("visitors", "id", payload.visit_id, {"status": "denied"})
        if payload.action == "checkout":
            db_update("passes", "pass_id", payload.pass_id, {"is_active": False})
            db_update("visitors", "id", payload.visit_id, {"status": "checked_out"})

        return {"success": True, "logged_at": logged_at}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/guard/live-visitors")
def live_visitors():
    try:
        visitors = db_select("visitors", {"status": "eq.checked_in"}) or []
        result_list = []

        for v in visitors:
            pass_result = db_select(
                "passes",
                {"visit_id": f"eq.{v['id']}", "is_active": "eq.true"},
            )
            pass_id = pass_result[0].get("pass_id") if pass_result else ""

            result_list.append(
                {
                    "name": v.get("name", ""),
                    "company": v.get("company", ""),
                    "department": v.get("department", ""),
                    "host_name": v.get("host_name", ""),
                    "visit_date": v.get("visit_date", ""),
                    "time_slot": v.get("time_slot", ""),
                    "pass_id": pass_id,
                }
            )

        return {"visitors": result_list, "count": len(result_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class Checkout(BaseModel):
    visit_id: str
    pass_id: str


@router.post("/guard/checkout")
def checkout(payload: Checkout):
    try:
        checked_out_at = datetime.utcnow().isoformat()
        db_insert(
            "entry_logs",
            {
                "visit_id": payload.visit_id,
                "pass_id": payload.pass_id,
                "action": "checkout",
                "guard_note": "Checked out",
                "logged_at": checked_out_at,
            },
        )

        db_update("passes", "pass_id", payload.pass_id, {"is_active": False})
        db_update("visitors", "id", payload.visit_id, {"status": "checked_out"})

        return {"success": True, "checked_out_at": checked_out_at}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
