from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_insert, db_select, db_update
from datetime import datetime, timedelta
import random

router = APIRouter()


class OTPSend(BaseModel):
    phone: str
    visit_id: str


@router.post("/otp/send")
def send_otp(payload: OTPSend):
    try:
        otp = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        db_insert(
            "otp_store",
            {
                "visit_id": payload.visit_id,
                "phone": payload.phone,
                "otp_value": otp,
                "expires_at": expires_at.isoformat(),
                "used": False,
            },
        )

        return {
            "success": True,
            "otp": otp,
            "message": "OTP sent",
            "expires_in_seconds": 300,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OTPVerify(BaseModel):
    phone: str
    otp: str
    visit_id: str


def _parse_iso_datetime(value: str) -> datetime:
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


@router.post("/otp/verify")
def verify_otp(payload: OTPVerify):
    try:
        results = db_select(
            "otp_store",
            {"visit_id": f"eq.{payload.visit_id}", "phone": f"eq.{payload.phone}"},
        )

        if not results:
            raise HTTPException(status_code=404, detail="OTP not found")

        record = results[-1]

        if record.get("used") is True:
            return {"success": False, "message": "OTP already used"}

        expires_at_raw = record.get("expires_at")
        if not expires_at_raw:
            return {"success": False, "message": "OTP expired"}

        try:
            expires_at = _parse_iso_datetime(expires_at_raw)
        except Exception:
            return {"success": False, "message": "OTP expired"}

        if expires_at < datetime.utcnow():
            return {"success": False, "message": "OTP expired"}

        if str(record.get("otp_value")) != str(payload.otp):
            return {"success": False, "message": "Incorrect OTP"}

        db_update("otp_store", "id", record["id"], {"used": True})
        return {"success": True, "message": "OTP verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
