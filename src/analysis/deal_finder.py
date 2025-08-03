"""
Deal Finder - Pronalazi potcenjene nekretnine
"""
import statistics
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DealFinder:
    """Analizira tržište i pronalazi dobre ponude"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        
    def calculate_fair_price(self, property_data: Dict) -> float:
        """
        Kalkuliše fer cenu na osnovu:
        - Lokacije (grad, opština, kvart)
        - Površine
        - Broja soba
        - Sprata
        - Stanja (ako imamo info)
        """
        # Pronađi slične nekretnine
        similar = self._find_similar_properties(property_data)
        
        if len(similar) < 3:
            return None
            
        # Kalkuliši prosečnu cenu po m2
        prices_per_m2 = [p.price_per_m2 for p in similar if p.price_per_m2]
        
        if not prices_per_m2:
            return None
            
        # Ukloni outliers (top 10% i bottom 10%)
        prices_per_m2.sort()
        trim_count = max(1, len(prices_per_m2) // 10)
        trimmed_prices = prices_per_m2[trim_count:-trim_count] if len(prices_per_m2) > 2 else prices_per_m2
        
        # Kalkuliši fer cenu
        avg_price_per_m2 = statistics.mean(trimmed_prices)
        fair_price = avg_price_per_m2 * property_data.get('area_m2', 0)
        
        return round(fair_price, 0)
    
    def _find_similar_properties(self, property_data: Dict) -> List:
        """Pronađi slične nekretnine za poređenje"""
        session = self.db.get_session()
        try:
            from database.models import Property
            
            query = session.query(Property).filter(
                Property.city == property_data.get('city'),
                Property.property_type == property_data.get('property_type', 'stan'),
                Property.listing_type == property_data.get('listing_type', 'prodaja')
            )
            
            # Filter po opštini ako postoji
            if property_data.get('municipality'):
                query = query.filter(Property.municipality == property_data['municipality'])
            
            # Filter po broju soba (±0.5)
            if property_data.get('rooms'):
                rooms = property_data['rooms']
                query = query.filter(
                    Property.rooms >= rooms - 0.5,
                    Property.rooms <= rooms + 0.5
                )
            
            # Filter po površini (±20%)
            if property_data.get('area_m2'):
                area = property_data['area_m2']
                query = query.filter(
                    Property.area_m2 >= area * 0.8,
                    Property.area_m2 <= area * 1.2
                )
            
            # Samo aktivne i novije oglase
            thirty_days_ago = datetime.now() - timedelta(days=30)
            query = query.filter(
                Property.is_active == True,
                Property.created_at >= thirty_days_ago
            )
            
            return query.all()
            
        finally:
            session.close()
    
    def find_underpriced_properties(self, 
                                   discount_threshold: float = 0.15,
                                   min_similar: int = 5) -> List[Dict]:
        """
        Pronađi nekretnine koje su bar 15% ispod tržišne cene
        
        Args:
            discount_threshold: Minimalni popust (0.15 = 15%)
            min_similar: Minimalan broj sličnih nekretnina za poređenje
        """
        session = self.db.get_session()
        try:
            from database.models import Property
            
            # Uzmi sve aktivne nekretnine
            properties = session.query(Property).filter(
                Property.is_active == True,
                Property.price_eur.isnot(None),
                Property.area_m2.isnot(None)
            ).all()
            
            deals = []
            
            for prop in properties:
                # Konvertuj u dict
                prop_dict = {
                    'id': prop.id,
                    'external_id': prop.external_id,
                    'title': prop.title,
                    'price_eur': prop.price_eur,
                    'city': prop.city,
                    'municipality': prop.municipality,
                    'neighborhood': prop.neighborhood,
                    'area_m2': prop.area_m2,
                    'rooms': prop.rooms,
                    'property_type': prop.property_type,
                    'listing_type': prop.listing_type,
                    'link': prop.link
                }
                
                # Kalkuliši fer cenu
                fair_price = self.calculate_fair_price(prop_dict)
                
                if not fair_price:
                    continue
                
                # Proveri da li je potcenjena
                discount = (fair_price - prop.price_eur) / fair_price
                
                if discount >= discount_threshold:
                    similar_count = len(self._find_similar_properties(prop_dict))
                    
                    if similar_count >= min_similar:
                        deals.append({
                            'property': prop_dict,
                            'fair_price': fair_price,
                            'current_price': prop.price_eur,
                            'discount': discount,
                            'discount_amount': fair_price - prop.price_eur,
                            'similar_properties_count': similar_count,
                            'score': self._calculate_deal_score(prop_dict, discount, similar_count)
                        })
            
            # Sortiraj po score (najbolji prvi)
            deals.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Pronađeno {len(deals)} potcenjenih nekretnina")
            return deals
            
        finally:
            session.close()
    
    def _calculate_deal_score(self, property_data: Dict, discount: float, similar_count: int) -> float:
        """
        Kalkuliše score za deal (0-100)
        Uzima u obzir:
        - Popust
        - Broj sličnih nekretnina
        - Lokaciju
        - Likvidnost
        """
        score = 0
        
        # Popust (max 40 poena)
        score += min(40, discount * 200)
        
        # Broj sličnih (max 20 poena)
        score += min(20, similar_count * 2)
        
        # Lokacija (max 20 poena)
        if property_data.get('city') == 'Beograd':
            if property_data.get('municipality') in ['Vračar', 'Stari grad', 'Savski venac']:
                score += 20
            elif property_data.get('municipality') in ['Novi Beograd', 'Zvezdara', 'Voždovac']:
                score += 15
            else:
                score += 10
        elif property_data.get('city') == 'Novi Sad':
            score += 15
        else:
            score += 5
        
        # Likvidnost - manji stanovi se lakše prodaju (max 20 poena)
        area = property_data.get('area_m2', 0)
        if 40 <= area <= 70:
            score += 20  # Najpopularniji
        elif 30 <= area <= 40 or 70 <= area <= 90:
            score += 15
        elif area < 30 or 90 <= area <= 120:
            score += 10
        else:
            score += 5
        
        return round(score, 2)
    
    def get_market_insights(self, city: str = None) -> Dict:
        """Vraća uvide u tržište"""
        session = self.db.get_session()
        try:
            from database.models import Property
            from sqlalchemy import func
            
            query = session.query(Property).filter(Property.is_active == True)
            
            if city:
                query = query.filter(Property.city == city)
            
            # Osnovne statistike
            total_count = query.count()
            avg_price = session.query(func.avg(Property.price_eur)).scalar()
            avg_price_per_m2 = session.query(func.avg(Property.price_per_m2)).scalar()
            
            # Po opštinama
            municipality_stats = session.query(
                Property.municipality,
                func.count(Property.id).label('count'),
                func.avg(Property.price_per_m2).label('avg_price_per_m2')
            ).filter(
                Property.city == (city or 'Beograd'),
                Property.municipality.isnot(None)
            ).group_by(Property.municipality).all()
            
            # Najbolje opštine za investiranje (najniža cena po m2)
            best_municipalities = sorted(
                [(m[0], m[2]) for m in municipality_stats if m[2]],
                key=lambda x: x[1]
            )[:5]
            
            return {
                'total_properties': total_count,
                'avg_price': round(avg_price, 0) if avg_price else 0,
                'avg_price_per_m2': round(avg_price_per_m2, 0) if avg_price_per_m2 else 0,
                'best_municipalities_to_invest': best_municipalities,
                'municipality_stats': {
                    m[0]: {
                        'count': m[1],
                        'avg_price_per_m2': round(m[2], 0) if m[2] else 0
                    } for m in municipality_stats
                }
            }
            
        finally:
            session.close()


# Primer korišćenja
if __name__ == "__main__":
    from database.db_manager import DatabaseManager
    
    db = DatabaseManager()
    finder = DealFinder(db)
    
    # Pronađi potcenjene nekretnine
    deals = finder.find_underpriced_properties(discount_threshold=0.10)  # 10% popust
    
    print(f"\n🏠 PRONAĐENO {len(deals)} POTCENJENIH NEKRETNINA:\n")
    
    for i, deal in enumerate(deals[:10], 1):
        print(f"{i}. {deal['property']['title']}")
        print(f"   📍 {deal['property']['city']}, {deal['property']['municipality']}")
        print(f"   💰 Cena: €{deal['current_price']:,.0f} (fer cena: €{deal['fair_price']:,.0f})")
        print(f"   📉 Popust: {deal['discount']*100:.1f}% (€{deal['discount_amount']:,.0f})")
        print(f"   📏 {deal['property']['area_m2']} m², {deal['property']['rooms']} soba")
        print(f"   ⭐ Score: {deal['score']}/100")
        print(f"   🔗 {deal['property']['link']}")
        print()
    
    # Tržišni uvidi
    insights = finder.get_market_insights('Beograd')
    print("\n📊 TRŽIŠNI UVIDI - BEOGRAD:")
    print(f"Ukupno nekretnina: {insights['total_properties']}")
    print(f"Prosečna cena: €{insights['avg_price']:,.0f}")
    print(f"Prosečna cena po m²: €{insights['avg_price_per_m2']:,.0f}")
    print(f"\nNajbolje opštine za investiranje:")
    for municipality, price_per_m2 in insights['best_municipalities_to_invest']:
        print(f"  - {municipality}: €{price_per_m2:.0f}/m²")