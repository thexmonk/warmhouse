from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os


DATABASE_URL = os.getenv("TELEMETRY_DB_URL", "sqlite:///./telemetry.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TelemetryRecord(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="C")
    status = Column(String, nullable=False, default="ok")
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)


class TelemetryIn(BaseModel):
    sensorId: str = Field(..., description="Sensor identifier")
    value: float = Field(..., description="Measured temperature value")
    unit: str = Field("C", description="Measurement unit")
    status: str = Field("ok", description="Status of the measurement")
    timestamp: Optional[datetime] = Field(
        default=None, description="Measurement timestamp; defaults to current time"
    )


class TelemetryOut(BaseModel):
    id: int
    sensorId: str
    value: float
    unit: str
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True


app = FastAPI(
    title="Telemetry Service",
    description="Service for storing and retrieving temperature telemetry data",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/telemetry", response_model=TelemetryOut, status_code=201)
def create_telemetry(record: TelemetryIn):
    db = next(get_db())

    ts = record.timestamp or datetime.utcnow()

    db_record = TelemetryRecord(
        sensor_id=record.sensorId,
        value=record.value,
        unit=record.unit,
        status=record.status,
        timestamp=ts,
    )

    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return TelemetryOut(
        id=db_record.id,
        sensorId=db_record.sensor_id,
        value=db_record.value,
        unit=db_record.unit,
        status=db_record.status,
        timestamp=db_record.timestamp,
    )


@app.get("/telemetry", response_model=List[TelemetryOut])
def get_telemetry(
    sensor_id: str = Query(..., alias="sensorId", description="Sensor identifier"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
):
    db = next(get_db())

    stmt = (
        select(TelemetryRecord)
        .where(TelemetryRecord.sensor_id == sensor_id)
        .order_by(TelemetryRecord.timestamp.desc())
        .limit(limit)
    )

    results = db.execute(stmt).scalars().all()
    return [
        TelemetryOut(
            id=r.id,
            sensorId=r.sensor_id,
            value=r.value,
            unit=r.unit,
            status=r.status,
            timestamp=r.timestamp,
        )
        for r in results
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8090"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

