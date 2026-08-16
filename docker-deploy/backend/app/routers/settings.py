import json
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULTS = {
    "deepseek_model": "deepseek-chat",
    "deepseek_base_url": "https://api.deepseek.com",
}


def get_setting(db: Session, key: str) -> str:
    row = db.query(models.AppSetting).filter(models.AppSetting.key == key).first()
    return row.value if row and row.value else DEFAULTS.get(key, "")


def set_setting(db: Session, key: str, value: str):
    row = db.query(models.AppSetting).filter(models.AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.AppSetting(key=key, value=value))


def _mask_key(key: str) -> str:
    if not key: return ""
    if len(key) <= 8: return key[:2] + "****"
    return key[:6] + "****" + key[-4:]


@router.get("/", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    api_key = get_setting(db, "deepseek_api_key")
    return schemas.SettingsOut(
        deepseek_api_key_set=bool(api_key),
        deepseek_api_key_masked=_mask_key(api_key),
        deepseek_model=get_setting(db, "deepseek_model"),
        deepseek_base_url=get_setting(db, "deepseek_base_url"),
    )


@router.put("/", response_model=schemas.SettingsOut)
def update_settings(body: schemas.SettingsUpdate, db: Session = Depends(get_db)):
    if body.api_key is not None:
        api_key = body.api_key.strip()
        if api_key:
            set_setting(db, "deepseek_api_key", api_key)
        else:
            set_setting(db, "deepseek_api_key", "")
    if body.model:
        set_setting(db, "deepseek_model", body.model.strip())
    if body.base_url:
        set_setting(db, "deepseek_base_url", body.base_url.strip().rstrip("/"))
    db.commit()
    return get_settings(db)


@router.post("/test")
def test_deepseek(api_key: str = None, db: Session = Depends(get_db)):
    key = (api_key or "").strip() or get_setting(db, "deepseek_api_key")
    if not key:
        raise HTTPException(status_code=400, detail="请先填写 DeepSeek API Key")
    base_url = get_setting(db, "deepseek_base_url")
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id") for m in data.get("data", [])]
        return {"ok": True, "models": ids[:20]}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise HTTPException(status_code=502, detail=f"连接失败（{e.code}）：{body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"连接失败：{e}")
