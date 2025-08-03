"""
Database Manager - Upravlja operacijama sa bazom podataka
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, Property, PriceHistory, SearchQuery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Upravlja database operacijama"""
    
    def __init__(self, database_url: Optional[str] = None):
        if not database_url:
            # Koristi SQLite za development
            database_url = 'sqlite:///../../data/serbian_estates.db'
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_db()
    
    def _init_db(self):
        """Inicijalizuje database tabele"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tabele inicijalizovane")
    
    def get_session(self) -> Session:
        """Vraća novu database sesiju"""
        return self.SessionLocal()
    
    def insert_property(self, property_data: Dict) -> Optional[Property]:
        """Ubacuje novu nekretninu u bazu"""
        session = self.get_session()
        try:
            # Proveri da li već postoji
            existing = session.query(Property).filter_by(
                external_id=property_data.get('id')
            ).first()
            
            if existing:
                # Ažuriraj postojeću
                for key, value in property_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                property_obj = existing
            else:
                # Kreiraj novu
                property_obj = Property(
                    external_id=property_data.get('id'),
                    title=property_data.get('title'),
                    link=property_data.get('link'),
                    price_eur=property_data.get('price_eur'),
                    price_rsd=property_data.get('price_rsd'),
                    currency=property_data.get('currency'),
                    price_per_m2=property_data.get('price_per_m2'),
                    city=property_data.get('city'),
                    municipality=property_data.get('municipality'),
                    neighborhood=property_data.get('neighborhood'),
                    street=property_data.get('street'),
                    location_raw=property_data.get('location_raw'),
                    area_m2=property_data.get('area_m2'),
                    rooms=property_data.get('rooms'),
                    floor=property_data.get('floor'),
                    total_floors=property_data.get('total_floors'),
                    features=property_data.get('features_raw'),
                    scraped_at=datetime.fromisoformat(property_data.get('scraped_at')),
                    processed_at=datetime.fromisoformat(property_data.get('processed_at'))
                )
                session.add(property_obj)
            
            session.commit()
            logger.info(f"Nekretnina {property_obj.external_id} sačuvana")
            return property_obj
            
        except Exception as e:
            session.rollback()
            logger.error(f"Greška pri čuvanju nekretnine: {str(e)}")
            return None
        finally:
            session.close()
    
    def insert_batch(self, properties: List[Dict]) -> int:
        """Ubacuje batch nekretnina"""
        count = 0
        for prop in properties:
            if self.insert_property(prop):
                count += 1
        
        logger.info(f"Sačuvano {count}/{len(properties)} nekretnina")
        return count
    
    def search_properties(self, 
                         city: Optional[str] = None,
                         min_price: Optional[float] = None,
                         max_price: Optional[float] = None,
                         min_area: Optional[float] = None,
                         max_area: Optional[float] = None,
                         rooms: Optional[float] = None,
                         property_type: Optional[str] = None,
                         listing_type: Optional[str] = None,
                         limit: int = 100) -> List[Property]:
        """Pretražuje nekretnine po kriterijumima"""
        session = self.get_session()
        try:
            query = session.query(Property).filter(Property.is_active == True)
            
            if city:
                query = query.filter(Property.city == city)
            
            if min_price:
                query = query.filter(Property.price_eur >= min_price)
            
            if max_price:
                query = query.filter(Property.price_eur <= max_price)
            
            if min_area:
                query = query.filter(Property.area_m2 >= min_area)
            
            if max_area:
                query = query.filter(Property.area_m2 <= max_area)
            
            if rooms:
                query = query.filter(Property.rooms == rooms)
            
            if property_type:
                query = query.filter(Property.property_type == property_type)
            
            if listing_type:
                query = query.filter(Property.listing_type == listing_type)
            
            # Sortiraj po datumu
            query = query.order_by(Property.created_at.desc())
            
            results = query.limit(limit).all()
            
            # Logiraj pretragu
            search_log = SearchQuery(
                query_params={
                    'city': city,
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_area': min_area,
                    'max_area': max_area,
                    'rooms': rooms
                },
                results_count=len(results)
            )
            session.add(search_log)
            session.commit()
            
            return results
            
        finally:
            session.close()
    
    def get_statistics(self) -> Dict:
        """Vraća statistike o nekretninama u bazi"""
        session = self.get_session()
        try:
            stats = {
                'total_properties': session.query(Property).count(),
                'active_properties': session.query(Property).filter(Property.is_active == True).count(),
                'avg_price_eur': session.query(func.avg(Property.price_eur)).scalar(),
                'avg_price_per_m2': session.query(func.avg(Property.price_per_m2)).scalar(),
                'avg_area': session.query(func.avg(Property.area_m2)).scalar(),
                'cities': {}
            }
            
            # Statistike po gradovima
            city_stats = session.query(
                Property.city,
                func.count(Property.id).label('count'),
                func.avg(Property.price_eur).label('avg_price')
            ).group_by(Property.city).all()
            
            for city, count, avg_price in city_stats:
                if city:
                    stats['cities'][city] = {
                        'count': count,
                        'avg_price': round(avg_price, 2) if avg_price else 0
                    }
            
            return stats
            
        finally:
            session.close()
    
    def record_price_change(self, property_id: int, new_price_eur: float, new_price_rsd: float):
        """Beleži promenu cene"""
        session = self.get_session()
        try:
            price_history = PriceHistory(
                property_id=property_id,
                price_eur=new_price_eur,
                price_rsd=new_price_rsd
            )
            session.add(price_history)
            session.commit()
            
        finally:
            session.close()


# Test
if __name__ == "__main__":
    db = DatabaseManager()
    
    # Test insert
    test_property = {
        'id': 'test123',
        'title': 'Test stan na Vračaru',
        'link': 'https://example.com/test',
        'price_eur': 150000,
        'price_rsd': 17550000,
        'currency': 'EUR',
        'price_per_m2': 2500,
        'city': 'Beograd',
        'municipality': 'Vračar',
        'area_m2': 60,
        'rooms': 2,
        'scraped_at': datetime.now().isoformat(),
        'processed_at': datetime.now().isoformat()
    }
    
    result = db.insert_property(test_property)
    if result:
        print(f"✓ Test property inserted: {result}")
    
    # Test search
    results = db.search_properties(city='Beograd', min_area=50, max_area=100)
    print(f"✓ Found {len(results)} properties")
    
    # Test statistics
    stats = db.get_statistics()
    print(f"✓ Statistics: {stats}")