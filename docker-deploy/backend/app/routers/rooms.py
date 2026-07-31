from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get("/", response_model=list[schemas.RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(models.Room).all()

@router.get("/{room_id}", response_model=schemas.RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room: raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.post("/", response_model=schemas.RoomOut)
def create_room(room: schemas.RoomCreate, db: Session = Depends(get_db)):
    if db.query(models.Room).filter(models.Room.name == room.name).first():
        raise HTTPException(status_code=400, detail="Room name already exists")
    db_room = models.Room(**room.model_dump())
    db.add(db_room); db.commit(); db.refresh(db_room)
    return db_room

@router.put("/{room_id}", response_model=schemas.RoomOut)
def update_room(room_id: int, room: schemas.RoomCreate, db: Session = Depends(get_db)):
    db_room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not db_room: raise HTTPException(status_code=404, detail="Room not found")
    for key, value in room.model_dump().items(): setattr(db_room, key, value)
    db.commit(); db.refresh(db_room)
    return db_room

@router.delete("/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db)):
    db_room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not db_room: raise HTTPException(status_code=404, detail="Room not found")
    db.delete(db_room); db.commit()
    return {"ok": True}
