from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import db_select, db_insert, db_update
from datetime import datetime, timedelta
import random
import os

router = APIRouter()


class OTPSend(BaseModel):
    phone: str
    visit_id: str


class OTPVerify(BaseModel):
    phone: str
    otp: str
    visit_id: str


@router.post("/otp/send")
async def send_otp(data: OTPSend):
    try:
        otp = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        db_insert(
            "otp_store",
            {
                "visit_id": data.visit_id,
                "phone": data.phone,
                "otp_value": otp,
                "expires_at": expires_at.isoformat(),
                "used": False,
            },
        )

        sms_sent = False
        TWILIO_SID = os.getenv("TWILIO_SID")
        TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
        TWILIO_FROM = os.getenv("TWILIO_FROM")

        if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
            try:
                from twilio.rest import Client

                client = Client(TWILIO_SID, TWILIO_TOKEN)

                phone_e164 = data.phone
                if not phone_e164.startswith("+"):
                    phone_e164 = "+91" + phone_e164.lstrip("0")

                message = client.messages.create(
                    body=f"Your SafeEntry Pro OTP is: {otp}. Valid for 5 minutes. Do not share with anyone.",
                    from_=TWILIO_FROM,
                    to=phone_e164,
                )

                if message.sid:
                    sms_sent = True
                    print(f"✅ SMS sent to {phone_e164}, SID: {message.sid}")

            except Exception as sms_err:
                print(f"❌ Twilio error: {sms_err}")

        response = {
            "success": True,
            "expires_in_seconds": 300,
            "sms_sent": sms_sent,
            "message": "OTP sent to your mobile" if sms_sent else "OTP generated",
        }

        if not sms_sent:
            response["otp"] = otp
            print(f"⚠️ SMS not sent, OTP for demo: {otp}")

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/otp/verify")
async def verify_otp(data: OTPVerify):
    try:
        result = db_select(
            "otp_store",
            {
                "visit_id": f"eq.{data.visit_id}",
                "phone": f"eq.{data.phone}",
            },
        )

        if not result:
            return {"success": False, "message": "OTP not found"}

        record = result[-1]

        if record["used"]:
            return {"success": False, "message": "OTP already used"}

        expires_at = datetime.fromisoformat(
            record["expires_at"].replace("Z", "+00:00")
        ).replace(tzinfo=None)

        if datetime.utcnow() > expires_at:
            return {"success": False, "message": "OTP expired"}

        if record["otp_value"] != data.otp:
            return {"success": False, "message": "Incorrect OTP"}

        db_update("otp_store", "id", record["id"], {"used": True})

        return {"success": True, "message": "OTP verified successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
