# ===============================================================
#  AI-Powered Health Risk Prediction API
#  Author: Programmer Aviral
#  Version: 5.0
#  Framework: FastAPI + SQLAlchemy + Pydantic
# ===============================================================

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import random

# ---------------- Configuration ----------------
DATABASE_URL = "sqlite:///./india_health_risk.db"
HIGH_RISK_THRESHOLD = 0.75

# ---------------- Database Setup ----------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    state = Column(String)
    area_sq_km = Column(Float, default=1000.0)
    population = Column(Integer)
    base_risk = Column(Float)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)

Base.metadata.create_all(bind=engine)

# ---------------- Dependency ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- Pydantic Models ----------------
class CityBase(BaseModel):
    name: str
    state: str
    population: int
    base_risk: float
    area_sq_km: float = 1000.0
    latitude: float = 0.0
    longitude: float = 0.0

class CityRead(CityBase):
    id: int
    class Config:
        orm_mode = True

class RiskRequest(BaseModel):
    city: str
    date: str  # YYYY-MM-DD

class RiskPredictionResponse(BaseModel):
    city: str
    date: str
    predicted_risk: float

class HealthTrendData(BaseModel):
    date: str
    risk_score: float

class CityHeatmapData(BaseModel):
    city: str
    risk: float

class SummaryResponse(BaseModel):
    highest_risk_city: CityHeatmapData
    average_risk: float
    total_cities: int

class AlertResponse(BaseModel):
    alerts: List[CityHeatmapData]
    count: int

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str


# ---------------- Helper Functions ----------------
def compute_risk(base_risk: float, date: datetime, population: int, area_sq_km: float) -> float:
    """
    Compute dynamic risk based on population density, season, and randomness.
    Returns risk between 0 and 1.
    """
    # Seasonal impact
    monsoon_factor = 0.1 if date.month in [6, 7, 8, 9] else 0
    summer_factor = 0.05 if date.month in [4, 5] else 0

    # Population density factor
    density = population / area_sq_km
    density_factor = min(0.15, max(0.0, (density / 30000) * 0.15))

    # Random environmental noise
    noise = random.uniform(-0.03, 0.03)

    # Total score
    risk = base_risk + monsoon_factor + summer_factor + density_factor + noise
    return round(min(max(risk, 0), 1), 2)


def init_cities():
    """Initialize database with some Indian metro cities."""
    db = SessionLocal()
    if db.query(City).count() == 0:
        cities_data = [
            {"name": "Delhi", "state": "Delhi", "population": 20000000, "area_sq_km": 1500, "base_risk": 0.65, "latitude": 28.6139, "longitude": 77.2090},
            {"name": "Mumbai", "state": "Maharashtra", "population": 20000000, "area_sq_km": 600, "base_risk": 0.55, "latitude": 19.0760, "longitude": 72.8777},
            {"name": "Bangalore", "state": "Karnataka", "population": 12000000, "area_sq_km": 750, "base_risk": 0.60, "latitude": 12.9716, "longitude": 77.5946},
            {"name": "Kolkata", "state": "West Bengal", "population": 15000000, "area_sq_km": 206, "base_risk": 0.65, "latitude": 22.5726, "longitude": 88.3639},
            {"name": "Chennai", "state": "Tamil Nadu", "population": 11000000, "area_sq_km": 426, "base_risk": 0.60, "latitude": 13.0827, "longitude": 80.2707}
        ]
        for c in cities_data:
            db.add(City(**c))
        db.commit()
    db.close()

init_cities()

# ---------------- FastAPI App Setup ----------------
app = FastAPI(title="AI Health Risk API", version="5.0")

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve HTML dashboard
app.mount("/", StaticFiles(directory="static", html=True), name="static")


# ---------------- API Endpoints ----------------

# --- Cities CRUD ---
@app.post("/cities/", response_model=CityRead, status_code=status.HTTP_201_CREATED)
def create_city(city: CityBase, db: Session = Depends(get_db)):
    if db.query(City).filter(City.name == city.name).first():
        raise HTTPException(status_code=400, detail="City already exists")
    db_city = City(**city.dict())
    db.add(db_city)
    db.commit()
    db.refresh(db_city)
    return db_city


@app.get("/cities/", response_model=List[CityRead])
def read_cities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(City).offset(skip).limit(limit).all()


# --- Heatmap Data ---
@app.get("/heatmap-data", response_model=List[CityHeatmapData])
def get_heatmap_data(db: Session = Depends(get_db)):
    today = datetime.today()
    return [
        {"city": c.name, "risk": compute_risk(c.base_risk, today, c.population, c.area_sq_km)}
        for c in db.query(City).all()
    ]


# --- Trend Data ---
@app.get("/trend", response_model=List[HealthTrendData])
def get_trend(city: str, db: Session = Depends(get_db)):
    c = db.query(City).filter(City.name == city).first()
    if not c:
        raise HTTPException(status_code=404, detail="City not found")

    today = datetime.today()
    return [
        {"date": (today - timedelta(days=i)).strftime("%Y-%m-%d"),
         "risk_score": compute_risk(c.base_risk, today - timedelta(days=i), c.population, c.area_sq_km)}
        for i in range(6, -1, -1)
    ]


# --- Predict Risk for City & Date ---
@app.post("/predict-risk", response_model=RiskPredictionResponse)
def predict_risk(req: RiskRequest, db: Session = Depends(get_db)):
    c = db.query(City).filter(City.name == req.city).first()
    if not c:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        date_obj = datetime.strptime(req.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

    risk_score = compute_risk(c.base_risk, date_obj, c.population, c.area_sq_km)
    return {"city": c.name, "date": req.date, "predicted_risk": risk_score}


# --- Summary ---
@app.get("/summary", response_model=SummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    today = datetime.today()
    cities = db.query(City).all()
    if not cities:
        return {"highest_risk_city": {"city": "N/A", "risk": 0}, "average_risk": 0, "total_cities": 0}

    data = [{"city": c.name, "risk": compute_risk(c.base_risk, today, c.population, c.area_sq_km)} for c in cities]
    highest = max(data, key=lambda x: x["risk"])
    avg = round(sum(d["risk"] for d in data) / len(data), 2)

    return {"highest_risk_city": highest, "average_risk": avg, "total_cities": len(cities)}


# --- Alerts ---
@app.get("/alerts", response_model=AlertResponse)
def get_alerts(db: Session = Depends(get_db)):
    today = datetime.today()
    alerts = [
        {"city": c.name, "risk": compute_risk(c.base_risk, today, c.population, c.area_sq_km)}
        for c in db.query(City).all()
        if compute_risk(c.base_risk, today, c.population, c.area_sq_km) >= HIGH_RISK_THRESHOLD
    ]
    return {"alerts": alerts, "count": len(alerts)}


# --- Simple Chatbot ---
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    text = req.query.lower()
    today = datetime.today()
    cities = db.query(City).all()

    for c in cities:
        if c.name.lower() in text:
            if "risk" in text:
                r = compute_risk(c.base_risk, today, c.population, c.area_sq_km)
                return {"response": f"The current health risk in {c.name} is {r}."}
            if "trend" in text:
                return {"response": f"You can check the risk trend at /trend?city={c.name}"}

    if "high risk" in text or "alerts" in text:
        high_risk = [
            f"{c.name} ({compute_risk(c.base_risk, today, c.population, c.area_sq_km)})"
            for c in cities
            if compute_risk(c.base_risk, today, c.population, c.area_sq_km) >= HIGH_RISK_THRESHOLD
        ]
        return {"response": "High-risk cities: " + ", ".join(high_risk)} if high_risk else {"response": "No high-risk cities right now."}

    return {"response": "Ask about a city's risk, risk trend, or high-risk alerts."}



# ===============================================================
# Run using: uvicorn app:app --reload
# Open dashboard: http://127.0.0.1:8000
# ===============================================================
