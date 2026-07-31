from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/adjustments", tags=["adjustments"])

@router.get("/")
def list_adjustments(course_id: int = None, date_val: date = None, db: Session = Depends(get_db)):
    q = db.query(models.ScheduleAdjustment).options(joinedload(models.ScheduleAdjustment.course).joinedload(models.Course.subject), joinedload(models.ScheduleAdjustment.course).joinedload(models.Course.teacher), joinedload(models.ScheduleAdjustment.course).joinedload(models.Course.room))
    if course_id: q = q.filter(models.ScheduleAdjustment.course_id == course_id)
    if date_val: q = q.filter(models.ScheduleAdjustment.adjustment_date == date_val)
    return q.order_by(models.ScheduleAdjustment.adjustment_date.desc()).all()

@router.post("/")
def create_adjustment(body: schemas.AdjustmentCreate, db: Session = Depends(get_db)):
    adj = models.ScheduleAdjustment(course_id=body.course_id, adjustment_date=body.adjustment_date, original_day=body.original_day, original_slot=body.original_slot, original_room_id=body.original_room_id, new_day=body.new_day, new_slot=body.new_slot, new_room_id=body.new_room_id, adjustment_type=body.adjustment_type, reason=body.reason)
    db.add(adj); db.commit(); db.refresh(adj)
    return adj

@router.put("/{adj_id}")
def update_adjustment(adj_id: int, body: schemas.AdjustmentCreate, db: Session = Depends(get_db)):
    adj = db.query(models.ScheduleAdjustment).filter(models.ScheduleAdjustment.id == adj_id).first()
    if not adj: raise HTTPException(status_code=404, detail="Adjustment not found")
    for key, val in body.model_dump().items(): setattr(adj, key, val)
    db.commit(); return adj

@router.delete("/{adj_id}")
def delete_adjustment(adj_id: int, db: Session = Depends(get_db)):
    adj = db.query(models.ScheduleAdjustment).filter(models.ScheduleAdjustment.id == adj_id).first()
    if not adj: raise HTTPException(status_code=404, detail="Adjustment not found")
    db.delete(adj); db.commit()
    return {"ok": True}
