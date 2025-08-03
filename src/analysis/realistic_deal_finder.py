"""
Realistic Deal Finder - Realno pronalaženje potcenjenih nekretnina u Srbiji
"""
import statistics
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)


class RealisticDealFinder:
    """
    Realistični pristup pronalaženju potcenjenih nekretnina
    uzimajući u obzir specifičnosti srpskog tržišta
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
        
        # Faktori koji utiču na cenu u Srbiji
        self.location_multipliers = {
            # Beograd - premium lokacije
            ('Beograd', 'Vračar'): 1.15,
            ('Beograd', 'Stari grad'): 1.20,
            ('Beograd', 'Savski venac'): 1.10,
            ('Beograd', 'Dedinje'): 1.25,
            
            # Beograd - srednje lokacije
            ('Beograd', 'Novi Beograd'): 1.0,
            ('Beograd', 'Zvezdara'): 0.95,
            ('Beograd', 'Voždovac'): 0.90,
            
            # Beograd - jeftinije lokacije
            ('Beograd', 'Čukarica'): 0.85,
            ('Beograd', 'Rakovica'): 0.80,
            ('Beograd', 'Palilula'): 0.85,
            ('Beograd', 'Zemun'): 0.90,
            
            # Drugi gradovi
            ('Novi Sad', None): 0.75,
            ('Niš', None): 0.50,
            ('Kragujevac', None): 0.45,
        }
        
        # Blizina bitnih lokacija (metro stanice kada bude)
        self.proximity_bonuses = {
            'blizu_fakulteta': 1.05,
            'blizu_klinickog_centra': 1.05,
            'centar_grada': 1.10,
            'blizu_parka': 1.05,
            'glavna_ulica': 0.95,  # buka
            'mirna_ulica': 1.05,
            'blizu_skole': 1.03,
            'blizu_vrtića': 1.03,
        }
    
    def calculate_realistic_market_value(self, property_data: Dict) -> Optional[float]:
        """
        Kalkuliše realnu tržišnu vrednost uzimajući u obzir:
        - Lokaciju (grad, opština, kvart, ulica)
        - Sprat (prizemlje i poslednji sprat su jeftiniji)
        - Stanje (novogradnja vs staro)
        - Struktura stana
        - Parking
        - Terasa/balkon
        - Grejanje
        """
        
        # Osnovna cena po m2 na osnovu lokacije
        base_price_per_m2 = self._get_base_price_per_m2(property_data)
        
        if not base_price_per_m2:
            return None
        
        # Primeni faktore
        adjusted_price = base_price_per_m2
        
        # Faktor sprata
        floor_factor = self._calculate_floor_factor(
            property_data.get('floor'),
            property_data.get('total_floors')
        )
        adjusted_price *= floor_factor
        
        # Faktor starosti/stanja
        condition_factor = self._estimate_condition_factor(property_data)
        adjusted_price *= condition_factor
        
        # Faktor strukture stana
        structure_factor = self._calculate_structure_factor(property_data)
        adjusted_price *= structure_factor
        
        # Dodatni faktori iz opisa
        extras_factor = self._analyze_description_factors(property_data)
        adjusted_price *= extras_factor
        
        # Finalna cena
        total_price = adjusted_price * property_data.get('area_m2', 0)
        
        return round(total_price, 0)
    
    def _get_base_price_per_m2(self, property_data: Dict) -> Optional[float]:
        """Dobija osnovnu cenu po m2 za lokaciju"""
        city = property_data.get('city')
        municipality = property_data.get('municipality')
        
        # Pronađi slične prodaje u poslednjih 60 dana
        similar = self._find_recent_similar_sales(property_data, days=60)
        
        if len(similar) < 3:
            # Ako nema dovoljno podataka, koristi prosek za opštinu
            return self._get_municipality_average(city, municipality)
        
        # Filtriraj ekstreme
        prices_per_m2 = [p.price_per_m2 for p in similar if p.price_per_m2]
        if not prices_per_m2:
            return None
        
        # Ukloni top 10% i bottom 10%
        prices_per_m2.sort()
        if len(prices_per_m2) > 10:
            trim = len(prices_per_m2) // 10
            prices_per_m2 = prices_per_m2[trim:-trim]
        
        return statistics.median(prices_per_m2)
    
    def _find_recent_similar_sales(self, property_data: Dict, days: int = 60) -> List:
        """Pronađi skoro prodate slične nekretnine"""
        session = self.db.get_session()
        try:
            from database.models import Property
            
            # Bazni upit
            query = session.query(Property).filter(
                Property.city == property_data.get('city'),
                Property.property_type == property_data.get('property_type', 'stan'),
                Property.listing_type == 'prodaja',
                Property.price_per_m2.isnot(None),
                Property.price_per_m2 > 500,  # Minimum realna cena
                Property.price_per_m2 < 5000,  # Maximum realna cena
            )
            
            # Lokacija
            if property_data.get('municipality'):
                query = query.filter(Property.municipality == property_data['municipality'])
            
            # Površina ±30%
            if property_data.get('area_m2'):
                area = property_data['area_m2']
                query = query.filter(
                    Property.area_m2 >= area * 0.7,
                    Property.area_m2 <= area * 1.3
                )
            
            # Broj soba
            if property_data.get('rooms'):
                rooms = property_data['rooms']
                # Za garsonjere i jednosobne tačno
                if rooms <= 1.5:
                    query = query.filter(Property.rooms == rooms)
                else:
                    # Za veće stanove ±0.5 sobe
                    query = query.filter(
                        Property.rooms >= rooms - 0.5,
                        Property.rooms <= rooms + 0.5
                    )
            
            # Samo noviji oglasi
            date_limit = datetime.now() - timedelta(days=days)
            query = query.filter(Property.created_at >= date_limit)
            
            return query.all()
            
        finally:
            session.close()
    
    def _calculate_floor_factor(self, floor: Optional[int], total_floors: Optional[int]) -> float:
        """
        Kalkuliše faktor sprata
        - Prizemlje: -10% do -15%
        - Prvi sprat: +5%
        - Srednji spratovi: najbolji
        - Poslednji bez lifta: -10%
        - Poslednji sa liftom: -5%
        """
        if floor is None:
            return 1.0
        
        # Prizemlje
        if floor == 0:
            return 0.85
        
        # Prvi sprat - dobar za starije
        if floor == 1:
            return 1.05
        
        # Visoki sprat bez lifta
        if floor > 4 and total_floors and total_floors <= 5:
            return 0.90
        
        # Poslednji sprat
        if floor == total_floors and total_floors:
            if total_floors > 5:  # Verovatno ima lift
                return 0.95
            else:
                return 0.90
        
        # Srednji spratovi su najbolji
        return 1.0
    
    def _estimate_condition_factor(self, property_data: Dict) -> float:
        """
        Procenjuje stanje nekretnine iz dostupnih podataka
        """
        title = property_data.get('title', '').lower()
        description = property_data.get('description', '').lower()
        
        # Novogradnja
        if any(word in title + description for word in ['novogradnja', 'novo', 'useljivo odmah']):
            return 1.15
        
        # Renoviran
        if any(word in title + description for word in ['renoviran', 'kompletno renoviran', 'lux']):
            return 1.10
        
        # Potrebno renoviranje
        if any(word in title + description for word in ['hitno', 'potrebno renoviranje', 'staro']):
            return 0.80
        
        # Default - prosečno stanje
        return 0.95
    
    def _calculate_structure_factor(self, property_data: Dict) -> float:
        """
        Faktor strukture stana
        - Jednosobni/garsonjere lakše se izdaju
        - Trosobni idealni za porodice
        - Četvorosobni i veći teže se prodaju
        """
        rooms = property_data.get('rooms')
        area = property_data.get('area_m2', 0)
        
        if not rooms:
            return 1.0
        
        # Proveri da li je realna kvadratura za broj soba
        expected_area_ranges = {
            0.5: (20, 35),   # Garsonjera
            1.0: (30, 50),   # Jednosoban
            1.5: (35, 55),   # Jednoiposoban
            2.0: (45, 70),   # Dvosoban
            2.5: (55, 80),   # Dvoiposoban
            3.0: (65, 100),  # Trosoban
            3.5: (75, 120),  # Troiposoban
            4.0: (85, 150),  # Četvorosoban
        }
        
        # Proveri da li je struktura realna
        if rooms in expected_area_ranges:
            min_area, max_area = expected_area_ranges[rooms]
            if area < min_area:
                return 0.90  # Premali za broj soba
            elif area > max_area:
                return 0.95  # Preveliki za broj soba
        
        # Idealne strukture
        if rooms in [1.0, 2.0, 3.0]:
            return 1.05
        
        # Velike strukture se teže prodaju
        if rooms >= 4.0:
            return 0.90
        
        return 1.0
    
    def _analyze_description_factors(self, property_data: Dict) -> float:
        """Analizira dodatne faktore iz opisa"""
        factor = 1.0
        
        title = property_data.get('title', '').lower()
        features = property_data.get('features_raw', [])
        features_text = ' '.join(features).lower() if features else ''
        
        all_text = title + ' ' + features_text
        
        # Pozitivni faktori
        if 'garaža' in all_text or 'parking' in all_text:
            factor *= 1.10
        
        if 'terasa' in all_text and not 'bez terase' in all_text:
            factor *= 1.05
        
        if 'cg' in all_text or 'centralno' in all_text:
            factor *= 1.05
        
        if 'lift' in all_text:
            factor *= 1.03
        
        if 'podrum' in all_text:
            factor *= 1.02
        
        # Negativni faktori
        if 'hitno' in all_text or 'hitna prodaja' in all_text:
            factor *= 0.90  # Možda ima problem
        
        if 'etažno' in all_text and 'cg' not in all_text:
            factor *= 0.95
        
        if 'potkrovlje' in all_text:
            factor *= 0.90
        
        return factor
    
    def find_real_deals(self, min_discount: float = 0.10) -> List[Dict]:
        """
        Pronađi STVARNO potcenjene nekretnine
        """
        session = self.db.get_session()
        try:
            from database.models import Property
            
            # Uzmi samo nekretnine sa realnim cenama
            properties = session.query(Property).filter(
                Property.is_active == True,
                Property.price_eur.isnot(None),
                Property.price_eur > 20000,  # Minimum 20k EUR
                Property.price_eur < 1000000,  # Max 1M EUR
                Property.area_m2.isnot(None),
                Property.area_m2 > 15,  # Minimum 15m2
                Property.area_m2 < 300,  # Max 300m2
                Property.listing_type == 'prodaja'
            ).all()
            
            real_deals = []
            
            for prop in properties:
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
                    'floor': prop.floor,
                    'total_floors': prop.total_floors,
                    'property_type': prop.property_type,
                    'listing_type': prop.listing_type,
                    'link': prop.link,
                    'features_raw': prop.features or []
                }
                
                # Kalkuliši realnu tržišnu vrednost
                market_value = self.calculate_realistic_market_value(prop_dict)
                
                if not market_value:
                    continue
                
                # Proveri popust
                discount = (market_value - prop.price_eur) / market_value
                
                # Dodatni filteri za realnost
                if discount >= min_discount:
                    # Proveri da li je cena po m2 realna
                    price_per_m2 = prop.price_eur / prop.area_m2
                    
                    # Za Beograd minimum 1000 EUR/m2, max 4000 EUR/m2
                    if prop.city == 'Beograd':
                        if price_per_m2 < 800 or price_per_m2 > 4500:
                            continue
                    
                    # Proveri da li ima dovoljno sličnih za poređenje
                    similar_count = len(self._find_recent_similar_sales(prop_dict, days=90))
                    
                    if similar_count >= 3:
                        # Razlozi zašto je jeftiniji
                        reasons = self._analyze_why_cheaper(prop_dict, discount)
                        
                        real_deals.append({
                            'property': prop_dict,
                            'market_value': market_value,
                            'current_price': prop.price_eur,
                            'discount': discount,
                            'discount_amount': market_value - prop.price_eur,
                            'price_per_m2': price_per_m2,
                            'similar_properties_count': similar_count,
                            'reasons': reasons,
                            'investment_score': self._calculate_investment_score(prop_dict, discount, reasons)
                        })
            
            # Sortiraj po investment score
            real_deals.sort(key=lambda x: x['investment_score'], reverse=True)
            
            logger.info(f"Pronađeno {len(real_deals)} stvarno potcenjenih nekretnina")
            return real_deals
            
        finally:
            session.close()
    
    def _analyze_why_cheaper(self, property_data: Dict, discount: float) -> List[str]:
        """Analizira razloge zašto je nekretnina jeftinija"""
        reasons = []
        
        title = property_data.get('title', '').lower()
        
        # Hitna prodaja
        if 'hitno' in title or 'hitna prodaja' in title:
            reasons.append("Hitna prodaja - vlasnik želi brzo da proda")
        
        # Sprat
        if property_data.get('floor') == 0:
            reasons.append("Prizemlje - manja potražnja")
        elif property_data.get('floor') == property_data.get('total_floors'):
            reasons.append("Poslednji sprat")
        
        # Potrebno renoviranje
        if any(word in title for word in ['renoviranje', 'adaptacija']):
            reasons.append("Potrebno renoviranje")
        
        # Velika struktura
        if property_data.get('rooms', 0) >= 4:
            reasons.append("Velika struktura - manja potražnja")
        
        # Lokacija
        municipality = property_data.get('municipality', '')
        if municipality in ['Rakovica', 'Čukarica', 'Palilula']:
            reasons.append(f"Lokacija ({municipality}) - niže cene")
        
        # Ako je previše jeftino
        if discount > 0.25:
            reasons.append("⚠️ Proveriti - možda postoji skriveni problem")
        
        if not reasons:
            reasons.append("Dobra prilika - nema očiglednih nedostataka")
        
        return reasons
    
    def _calculate_investment_score(self, property_data: Dict, discount: float, reasons: List[str]) -> float:
        """
        Kalkuliše investment score (0-100)
        Uzima u obzir:
        - ROI potencijal
        - Likvidnost
        - Rizik
        - Lokaciju
        """
        score = 0
        
        # Popust (max 30 poena)
        score += min(30, discount * 150)
        
        # Likvidnost - manji stanovi se lakše prodaju/izdaju (max 25 poena)
        area = property_data.get('area_m2', 0)
        rooms = property_data.get('rooms', 0)
        
        if 35 <= area <= 65 and rooms in [1.0, 1.5, 2.0]:
            score += 25  # Najpopularniji
        elif 25 <= area <= 45:
            score += 20  # Garsonjere
        elif 65 <= area <= 85 and rooms in [2.5, 3.0]:
            score += 15
        else:
            score += 5
        
        # Lokacija (max 25 poena)
        city = property_data.get('city')
        municipality = property_data.get('municipality', '')
        
        if city == 'Beograd':
            if municipality in ['Vračar', 'Stari grad', 'Savski venac']:
                score += 25
            elif municipality in ['Novi Beograd', 'Zvezdara']:
                score += 20
            elif municipality in ['Voždovac', 'Čukarica']:
                score += 15
            else:
                score += 10
        elif city == 'Novi Sad':
            score += 15
        else:
            score += 5
        
        # Rizik faktori (max -20 poena)
        risk_penalty = 0
        
        if property_data.get('floor') == 0:
            risk_penalty += 5
        
        if 'hitno' in property_data.get('title', '').lower():
            risk_penalty += 5
        
        if any('skriveni problem' in r for r in reasons):
            risk_penalty += 10
        
        score -= risk_penalty
        
        # ROI potencijal za izdavanje (max 20 poena)
        # Manji stanovi imaju bolji ROI
        if rooms <= 2.0 and area <= 60:
            score += 20
        elif rooms <= 3.0 and area <= 80:
            score += 15
        else:
            score += 5
        
        return max(0, min(100, score))
    
    def _get_municipality_average(self, city: str, municipality: str) -> Optional[float]:
        """Dobija prosečnu cenu za opštinu"""
        session = self.db.get_session()
        try:
            from database.models import Property
            from sqlalchemy import func
            
            avg = session.query(func.avg(Property.price_per_m2)).filter(
                Property.city == city,
                Property.municipality == municipality,
                Property.is_active == True,
                Property.price_per_m2 > 500,
                Property.price_per_m2 < 5000
            ).scalar()
            
            return float(avg) if avg else None
            
        finally:
            session.close()


if __name__ == "__main__":
    from database.db_manager import DatabaseManager
    
    db = DatabaseManager()
    finder = RealisticDealFinder(db)
    
    # Pronađi realne ponude
    deals = finder.find_real_deals(min_discount=0.10)
    
    print("\n🏠 REALNO POTCENJENE NEKRETNINE U SRBIJI")
    print("=" * 80)
    
    for i, deal in enumerate(deals[:10], 1):
        print(f"\n{i}. {deal['property']['title']}")
        print(f"   📍 {deal['property']['city']}, {deal['property']['municipality']}")
        print(f"   💰 Cena: €{deal['current_price']:,.0f}")
        print(f"   📊 Tržišna vrednost: €{deal['market_value']:,.0f}")
        print(f"   📉 Popust: {deal['discount']*100:.1f}% (€{deal['discount_amount']:,.0f})")
        print(f"   📏 {deal['property']['area_m2']} m², €{deal['price_per_m2']:.0f}/m²")
        print(f"   🏠 {deal['property']['rooms']} soba, {deal['property']['floor']}/{deal['property']['total_floors']} sprat")
        print(f"   ⭐ Investment score: {deal['investment_score']}/100")
        print(f"   \n   💡 Razlozi niže cene:")
        for reason in deal['reasons']:
            print(f"      - {reason}")
        print(f"   🔗 {deal['property']['link']}")