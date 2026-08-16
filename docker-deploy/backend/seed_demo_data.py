# -*- coding: utf-8 -*-
"""One-off script: generate realistic mock attendance and score records."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, SessionLocal, engine
from app.demo_data import seed_demo_data


Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    result = seed_demo_data(db)
    print("模拟数据生成完成：", result)
finally:
    db.close()
