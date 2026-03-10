from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_select, db_insert, db_update, db_delete
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()


@router.get("/admin/stats")
def admin_stats():
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")

        visitors = db_select("visitors", {}) or []
        total_today = sum(1 for v in visitors if v.get("visit_date") == today)
        currently_inside = sum(1 for v in visitors if v.get("status") == "checked_in")

        logs = db_select("entry_logs", {}) or []
        flagged_today = sum(
            1 for l in logs if l.get("action") == "flag" and str(l.get("logged_at", "")).startswith(today)
        )
        denied_today = sum(
            1 for l in logs if l.get("action") == "deny" and str(l.get("logged_at", "")).startswith(today)
        )

        return {
            "total_today": total_today,
            "currently_inside": currently_inside,
            "flagged_today": flagged_today,
            "denied_today": denied_today,
            "avg_checkin_mins": 4.2,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/chart-weekly")
def admin_chart_weekly():
    try:
        days_list = []
        for i in range(6, -1, -1):
            date = datetime.utcnow() - timedelta(days=i)
            days_list.append(date.strftime("%Y-%m-%d"))

        visitors = db_select("visitors", {}) or []

        data = []
        for d in days_list:
            count = sum(1 for v in visitors if v.get("visit_date") == d)
            day = datetime.strptime(d, "%Y-%m-%d").strftime("%a")
            data.append({"date": d, "day": day, "count": count})

        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/chart-departments")
def admin_chart_departments():
    try:
        visitors = db_select("visitors", {}) or []
        dept_counts = {}
        for v in visitors:
            dept = v.get("department") or "Unknown"
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        total = len(visitors)
        data = []
        for dept, count in dept_counts.items():
            percentage = int(round((count / total) * 100)) if total > 0 else 0
            data.append({"department": dept, "count": count, "percentage": percentage})

        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BlacklistAdd(BaseModel):
    name: str
    phone: str
    reason: str


@router.post("/admin/blacklist")
def admin_blacklist_add(payload: BlacklistAdd):
    try:
        db_insert(
            "blacklist",
            {
                "name": payload.name,
                "phone": payload.phone,
                "reason": payload.reason,
                "added_at": datetime.utcnow().isoformat(),
                "added_by": "admin",
            },
        )
        return {"success": True, "message": "Added to blacklist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/blacklist")
def admin_blacklist_list():
    try:
        result = db_select("blacklist", {}) or []
        return {"entries": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class Lockdown(BaseModel):
    activate: bool


@router.post("/admin/lockdown")
def admin_lockdown(payload: Lockdown):
    try:
        if payload.activate is True:
            active_passes = db_select("passes", {"is_active": "eq.true"}) or []
            for p in active_passes:
                db_update("passes", "pass_id", p["pass_id"], {"is_active": False})
            count = len(active_passes)
            return {
                "success": True,
                "passes_invalidated": count,
                "activated_at": datetime.utcnow().isoformat(),
                "message": "LOCKDOWN ACTIVE - All passes invalidated",
            }

        return {"success": True, "message": "Lockdown deactivated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
