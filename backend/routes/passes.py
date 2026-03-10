from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_select, db_insert, db_update
from datetime import datetime
import random, string

router = APIRouter()


class GeneratePass(BaseModel):
    visit_id: str


def _zones_for_department(department: str) -> str:
    dept = (department or "").strip()
    if dept == "Manufacturing":
        return "Production Floor, Safety Zone, Reception, Cafeteria"
    if dept == "Chemical Lab":
        return "Lab Wing, Clean Room Corridor, Reception"
    if dept == "Electrical":
        return "Electrical Bay, Testing Area, Reception"
    if dept == "Warehouse":
        return "Warehouse Floor, Loading Bay, Reception"
    if dept == "Office / Admin":
        return "Office Floors, Meeting Rooms, Reception, Cafeteria"
    return "Reception, Meeting Rooms"


@router.post("/passes/generate")
def generate_pass(payload: GeneratePass):
    try:
        visit_id = payload.visit_id
        visitor_result = db_select("visitors", {"id": f"eq.{visit_id}"})
        if not visitor_result:
            raise HTTPException(status_code=404, detail="Visitor not found")

        visitor = visitor_result[0]

        chars = string.ascii_uppercase + string.digits
        rand = "".join(random.choices(chars, k=8))
        pass_id = f"PASS-{rand}"

        zones = _zones_for_department(visitor.get("department", ""))

        db_insert(
            "passes",
            {
                "pass_id": pass_id,
                "visit_id": visit_id,
                "visitor_name": visitor["name"],
                "company": visitor["company"],
                "department": visitor["department"],
                "host_name": visitor["host_name"],
                "visit_date": visitor["visit_date"],
                "time_slot": visitor["time_slot"],
                "permitted_zones": zones,
                "industry": visitor.get("industry", ""),
                "is_active": True,
            },
        )

        db_update("visitors", "id", visit_id, {"pass_id": pass_id, "status": "pass_issued"})

        return {
            "success": True,
            "pass_id": pass_id,
            "visit_id": visit_id,
            "visitor_name": visitor["name"],
            "company": visitor["company"],
            "department": visitor["department"],
            "host_name": visitor["host_name"],
            "visit_date": visitor["visit_date"],
            "time_slot": visitor["time_slot"],
            "permitted_zones": zones,
            "qr_data": f"SAFEENTRY|{pass_id}|{visit_id}|verified",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/passes/{pass_id}")
def get_pass(pass_id: str):
    try:
        pass_result = db_select("passes", {"pass_id": f"eq.{pass_id}"})
        if not pass_result:
            raise HTTPException(status_code=404, detail="Pass not found")

        pass_data = pass_result[0]

        visitor_result = db_select("visitors", {"id": f"eq.{pass_data['visit_id']}"})
        visitor = visitor_result[0] if visitor_result else {}

        blacklist_result = db_select("blacklist", {"phone": f"eq.{visitor.get('phone','')}"})
        is_blacklisted = len(blacklist_result) > 0

        return {
            "pass": pass_data,
            "visitor": visitor,
            "is_blacklisted": is_blacklisted,
            "is_active": pass_data["is_active"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
