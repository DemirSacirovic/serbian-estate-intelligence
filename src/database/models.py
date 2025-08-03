"""
Database Models za nekretnine
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Property(Base):
    """Model za nekretnine"""
    __tablename__ = 'properties'
    
    # Osnovni podaci
    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, index=True)  # ID sa halooglasi
    title = Column(String(500))
    link = Column(String(1000))
    
    # Cena
    price_eur = Column(Float, index=True)
    price_rsd = Column(Float)
    currency = Column(String(10))
    price_per_m2 = Column(Float, index=True)
    
    # Lokacija
    city = Column(String(100), index=True)
    municipality = Column(String(100), index=True)
    neighborhood = Column(String(100), index=True)
    street = Column(String(200))
    location_raw = Column(String(500))
    
    # Karakteristike
    area_m2 = Column(Float, index=True)
    rooms = Column(Float, index=True)
    floor = Column(Integer)
    total_floors = Column(Integer)
    
    # Tip nekretnine
    property_type = Column(String(50), index=True)  # stan, kuća, poslovni prostor
    listing_type = Column(String(20), index=True)  # prodaja, izdavanje
    
    # Dodatni podaci
    description = Column(Text)
    features = Column(JSON)  # Lista dodatnih karakteristika
    images = Column(JSON)    # Lista URL-ova slika
    
    # Metadata
    scraped_at = Column(DateTime)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Property(id={self.external_id}, title={self.title[:50]}...)>"


class PriceHistory(Base):
    """Model za praćenje istorije cena"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, index=True)
    price_eur = Column(Float)
    price_rsd = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PriceHistory(property_id={self.property_id}, price={self.price_eur}, date={self.recorded_at})>"


class SearchQuery(Base):
    """Model za čuvanje pretrage korisnika"""
    __tablename__ = 'search_queries'
    
    id = Column(Integer, primary_key=True)
    query_params = Column(JSON)
    results_count = Column(Integer)
    user_ip = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SearchQuery(id={self.id}, results={self.results_count})>"


# Database setup funkcije
def get_database_url():
    """Vraća database URL iz environment varijabli ili default"""
    import os
    return os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost/serbian_estates')


def init_database():
    """Inicijalizuje database i kreira tabele"""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Kreira novu database sesiju"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    # Test database konekciju
    print("Inicijalizujem database...")
    try:
        engine = init_database()
        print("✓ Database tabele kreirane uspešno")
        
        # Test konekciju
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✓ Database konekcija uspešna")
    except Exception as e:
        print(f"✗ Greška: {str(e)}")
        print("\nDa bi koristio PostgreSQL, pokreni:")
        print("sudo apt install postgresql postgresql-contrib")
        print("sudo -u postgres createdb serbian_estates")
        print("\nIli koristi SQLite za development:")
        print("export DATABASE_URL='sqlite:///serbian_estates.db'")