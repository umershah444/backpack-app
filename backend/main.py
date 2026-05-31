"""
Backpack — Job Costing Prototype (KTP Associate pre-interview task)
Backend API: FastAPI + SQLite (SQLAlchemy)

This service lets an Operative submit job details (time on site, plant/tools,
vehicles, materials) and computes a job cost for the QS.

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs auto-generated at:  http://localhost:8000/docs
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

# --------------------------------------------------------------------------
# Database setup (SQLite chosen for a zero-config prototype; the SQLAlchemy
# ORM means swapping to PostgreSQL in production is a one-line URL change.)
# --------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./backpack.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --------------------------------------------------------------------------
# Reference cost rates. In production these live in a configurable table the
# QS can edit. Hard-coded here as the task permits estimating values.
# --------------------------------------------------------------------------
LABOUR_RATE_PER_HOUR = 28.50          # GBP, blended operative rate
VEHICLE_RATES_PER_DAY = {             # GBP per vehicle per day on site
    "Van": 45.00,
    "Tipper": 70.00,
    "Cherry Picker": 180.00,
    "Flatbed Truck": 120.00,
}
PLANT_RATES_PER_DAY = {               # GBP per tool/plant item per day
    "Mini Excavator": 150.00,
    "Generator": 40.00,
    "Compactor Plate": 35.00,
    "Pressure Washer": 25.00,
    "Hand Tools (kit)": 10.00,
}


# --------------------------------------------------------------------------
# ORM model
# --------------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, index=True)
    operative_name = Column(String)
    description = Column(String)
    time_on_site_hours = Column(Float)
    materials_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    # computed snapshot stored so the QS sees the figure as-submitted
    labour_cost = Column(Float, default=0.0)
    vehicle_cost = Column(Float, default=0.0)
    plant_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    vehicles = relationship("JobVehicle", back_populates="job",
                            cascade="all, delete-orphan")
    plant = relationship("JobPlant", back_populates="job",
                         cascade="all, delete-orphan")


class JobVehicle(Base):
    __tablename__ = "job_vehicles"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    vehicle_type = Column(String)
    days_on_site = Column(Float, default=1.0)
    job = relationship("Job", back_populates="vehicles")


class JobPlant(Base):
    __tablename__ = "job_plant"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    plant_type = Column(String)
    days_on_site = Column(Float, default=1.0)
    job = relationship("Job", back_populates="plant")


Base.metadata.create_all(bind=engine)


# --------------------------------------------------------------------------
# Pydantic schemas (request/response validation)
# --------------------------------------------------------------------------
class VehicleIn(BaseModel):
    vehicle_type: str
    days_on_site: float = Field(default=1.0, ge=0)


class PlantIn(BaseModel):
    plant_type: str
    days_on_site: float = Field(default=1.0, ge=0)


class JobIn(BaseModel):
    reference: str
    operative_name: str
    description: str = ""
    time_on_site_hours: float = Field(ge=0)
    materials_cost: float = Field(default=0.0, ge=0)
    vehicles: List[VehicleIn] = []
    plant: List[PlantIn] = []


class CostBreakdown(BaseModel):
    labour_cost: float
    vehicle_cost: float
    plant_cost: float
    materials_cost: float
    total_cost: float


class JobOut(BaseModel):
    id: int
    reference: str
    operative_name: str
    description: str
    time_on_site_hours: float
    created_at: datetime
    breakdown: CostBreakdown

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------
# Core costing logic — pure function, kept separate so it is unit-testable
# without a database or web server.
# --------------------------------------------------------------------------
def calculate_cost(job: JobIn) -> CostBreakdown:
    """Calculate a job's cost from its components.

    cost = labour + vehicles + plant + materials
    """
    labour = round(job.time_on_site_hours * LABOUR_RATE_PER_HOUR, 2)

    vehicle_cost = 0.0
    for v in job.vehicles:
        rate = VEHICLE_RATES_PER_DAY.get(v.vehicle_type, 0.0)
        vehicle_cost += rate * v.days_on_site
    vehicle_cost = round(vehicle_cost, 2)

    plant_cost = 0.0
    for p in job.plant:
        rate = PLANT_RATES_PER_DAY.get(p.plant_type, 0.0)
        plant_cost += rate * p.days_on_site
    plant_cost = round(plant_cost, 2)

    materials = round(job.materials_cost, 2)
    total = round(labour + vehicle_cost + plant_cost + materials, 2)

    return CostBreakdown(
        labour_cost=labour,
        vehicle_cost=vehicle_cost,
        plant_cost=plant_cost,
        materials_cost=materials,
        total_cost=total,
    )


# --------------------------------------------------------------------------
# FastAPI app
# --------------------------------------------------------------------------
app = FastAPI(title="Backpack Job Costing API", version="1.0.0")

# CORS so the React frontend (served from a different origin) can call the API.
# In production, set ALLOWED_ORIGINS to your frontend URL (comma-separated).
_origins = os.environ.get("ALLOWED_ORIGINS", "*")
allow_origins = ["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/rates")
def get_rates():
    """Expose reference rates so the UI can display/estimate live."""
    return {
        "labour_rate_per_hour": LABOUR_RATE_PER_HOUR,
        "vehicle_rates_per_day": VEHICLE_RATES_PER_DAY,
        "plant_rates_per_day": PLANT_RATES_PER_DAY,
    }


@app.post("/jobs", response_model=JobOut)
def create_job(job_in: JobIn, db: Session = Depends(get_db)):
    breakdown = calculate_cost(job_in)
    job = Job(
        reference=job_in.reference,
        operative_name=job_in.operative_name,
        description=job_in.description,
        time_on_site_hours=job_in.time_on_site_hours,
        materials_cost=job_in.materials_cost,
        labour_cost=breakdown.labour_cost,
        vehicle_cost=breakdown.vehicle_cost,
        plant_cost=breakdown.plant_cost,
        total_cost=breakdown.total_cost,
    )
    for v in job_in.vehicles:
        job.vehicles.append(JobVehicle(vehicle_type=v.vehicle_type,
                                       days_on_site=v.days_on_site))
    for p in job_in.plant:
        job.plant.append(JobPlant(plant_type=p.plant_type,
                                  days_on_site=p.days_on_site))
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut(
        id=job.id, reference=job.reference, operative_name=job.operative_name,
        description=job.description, time_on_site_hours=job.time_on_site_hours,
        created_at=job.created_at, breakdown=breakdown,
    )


@app.get("/jobs", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [
        JobOut(
            id=j.id, reference=j.reference, operative_name=j.operative_name,
            description=j.description, time_on_site_hours=j.time_on_site_hours,
            created_at=j.created_at,
            breakdown=CostBreakdown(
                labour_cost=j.labour_cost, vehicle_cost=j.vehicle_cost,
                plant_cost=j.plant_cost, materials_cost=j.materials_cost,
                total_cost=j.total_cost,
            ),
        )
        for j in jobs
    ]


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.query(Job).filter(Job.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(
        id=j.id, reference=j.reference, operative_name=j.operative_name,
        description=j.description, time_on_site_hours=j.time_on_site_hours,
        created_at=j.created_at,
        breakdown=CostBreakdown(
            labour_cost=j.labour_cost, vehicle_cost=j.vehicle_cost,
            plant_cost=j.plant_cost, materials_cost=j.materials_cost,
            total_cost=j.total_cost,
        ),
    )
