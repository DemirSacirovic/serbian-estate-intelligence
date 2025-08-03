"""
Serbian Estate Intelligence API
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import sys
import os

# Dodaj parent direktorijum u path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from database.models import Property

app = FastAPI(
    title="Serbian Estate Intelligence API",
    description="API za pretragu nekretnina u Srbiji",
    version="1.0.0"
)

# CORS middleware za frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic modeli
class PropertyResponse(BaseModel):
    id: int
    external_id: str
    title: str
    price_eur: float
    price_per_m2: Optional[float]
    city: Optional[str]
    municipality: Optional[str]
    neighborhood: Optional[str]
    area_m2: Optional[float]
    rooms: Optional[float]
    floor: Optional[int]
    total_floors: Optional[int]
    link: str
    scraped_at: datetime
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    city: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    rooms: Optional[float] = None
    property_type: Optional[str] = None
    listing_type: Optional[str] = None
    limit: int = 100

class StatsResponse(BaseModel):
    total_properties: int
    active_properties: int
    avg_price_eur: Optional[float]
    avg_price_per_m2: Optional[float]
    avg_area: Optional[float]
    cities: dict

# Dependency za database
def get_db():
    return DatabaseManager()

@app.get("/")
def root():
    """Početna stranica"""
    return {
        "message": "Serbian Estate Intelligence API",
        "endpoints": {
            "search": "/api/properties/search",
            "stats": "/api/stats",
            "property": "/api/properties/{id}",
            "docs": "/docs"
        }
    }

@app.post("/api/properties/search", response_model=List[PropertyResponse])
def search_properties(
    request: SearchRequest,
    db: DatabaseManager = Depends(get_db)
):
    """
    Pretražuje nekretnine po zadatim kriterijumima
    
    - **city**: Grad (Beograd, Novi Sad, itd)
    - **min_price**: Minimalna cena u EUR
    - **max_price**: Maksimalna cena u EUR
    - **min_area**: Minimalna površina u m²
    - **max_area**: Maksimalna površina u m²
    - **rooms**: Broj soba
    - **property_type**: Tip nekretnine (stan, kuća, poslovni_prostor)
    - **listing_type**: Tip oglasa (prodaja, izdavanje)
    - **limit**: Maksimalan broj rezultata
    """
    properties = db.search_properties(
        city=request.city,
        min_price=request.min_price,
        max_price=request.max_price,
        min_area=request.min_area,
        max_area=request.max_area,
        rooms=request.rooms,
        property_type=request.property_type,
        listing_type=request.listing_type,
        limit=request.limit
    )
    
    return properties

@app.get("/api/properties/{property_id}", response_model=PropertyResponse)
def get_property(property_id: int, db: DatabaseManager = Depends(get_db)):
    """Vraća detalje o specifičnoj nekretnini"""
    session = db.get_session()
    try:
        property_obj = session.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            raise HTTPException(status_code=404, detail="Nekretnina nije pronađena")
        return property_obj
    finally:
        session.close()

@app.get("/api/stats", response_model=StatsResponse)
def get_statistics(db: DatabaseManager = Depends(get_db)):
    """Vraća statistike o nekretninama"""
    stats = db.get_statistics()
    return StatsResponse(**stats)

@app.get("/api/cities")
def get_cities(db: DatabaseManager = Depends(get_db)):
    """Vraća listu dostupnih gradova"""
    session = db.get_session()
    try:
        cities = session.query(Property.city).distinct().filter(
            Property.city.isnot(None)
        ).all()
        return [city[0] for city in cities]
    finally:
        session.close()

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)