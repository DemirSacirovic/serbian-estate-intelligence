"""
Serbian Zestimate - Zillow-style procena vrednosti za srpsko tržište
Uzima u obzir lokalne faktore, prevare i realne cene
"""
import statistics
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class SerbianZestimate:
    """
    Procenjuje REALNU vrednost nekretnina u Srbiji
    po uzoru na Zillow Zestimate algoritam
    """
    
    def __init__(self):
        # Faktori specifični za srpsko tržište
        self.market_data = {
            'Beograd': {
                'zones': {
                    'ultra_premium': {
                        'municipalities': ['Dedinje', 'Senjak', 'Topčidersko brdo'],
                        'base_price_m2': 3500,
                        'growth_rate': 0.06
                    },
                    'premium': {
                        'municipalities': ['Vračar', 'Stari grad', 'Savski venac'],
                        'base_price_m2': 2800,
                        'growth_rate': 0.08
                    },
                    'mid_high': {
                        'municipalities': ['Novi Beograd', 'Zvezdara'],
                        'base_price_m2': 2300,
                        'growth_rate': 0.10
                    },
                    'mid': {
                        'municipalities': ['Voždovac', 'Čukarica', 'Zemun'],
                        'base_price_m2': 1900,
                        'growth_rate': 0.09
                    },
                    'affordable': {
                        'municipalities': ['Rakovica', 'Palilula', 'Grocka'],
                        'base_price_m2': 1500,
                        'growth_rate': 0.12  # Veći potencijal rasta
                    }
                },
                'metro_impact': {  # Uticaj buduće metro linije
                    'confirmed_stations': ['Prokop', 'Slavija', 'Trg Republike'],
                    'price_boost': 0.15  # 15% na vrednost
                }
            },
            'Novi Sad': {
                'zones': {
                    'premium': {
                        'neighborhoods': ['Centar', 'Stari grad', 'Dunav'],
                        'base_price_m2': 2000,
                        'growth_rate': 0.10
                    },
                    'mid': {
                        'neighborhoods': ['Liman', 'Grbavica', 'Novo naselje'],
                        'base_price_m2': 1600,
                        'growth_rate': 0.09
                    },
                    'affordable': {
                        'neighborhoods': ['Detelinara', 'Klisa', 'Veternik'],
                        'base_price_m2': 1200,
                        'growth_rate': 0.11
                    }
                }
            },
            'Novi Pazar': {
                'base_price_m2': 800,
                'growth_rate': 0.15,  # Najveći rast!
                'diaspora_factor': 1.2  # Dijaspora podiže cene
            },
            'Zlatibor': {
                'zones': {
                    'centar': {
                        'base_price_m2': 2500,
                        'seasonal_factor': 1.3  # Zimi skuplje
                    },
                    'periferija': {
                        'base_price_m2': 1800,
                        'seasonal_factor': 1.2
                    }
                },
                'tourism_growth': 0.12
            }
        }
        
        # Faktori koji utiču na cenu
        self.adjustment_factors = {
            'floor': {
                'basement': 0.70,
                'ground': 0.85,
                'first': 1.05,
                'middle': 1.00,
                'top_with_elevator': 0.95,
                'top_no_elevator': 0.85,
                'penthouse': 1.10
            },
            'age': {
                'new': 1.15,
                'under_5': 1.10,
                '5_to_10': 1.00,
                '10_to_20': 0.90,
                '20_to_30': 0.85,
                'over_30_renovated': 0.95,
                'over_30_original': 0.75
            },
            'condition': {
                'lux': 1.20,
                'excellent': 1.10,
                'good': 1.00,
                'needs_cosmetic': 0.90,
                'needs_renovation': 0.75,
                'construction': 1.05
            },
            'heating': {
                'central_city': 1.05,
                'central_building': 1.00,
                'gas': 0.98,
                'electric': 0.85,
                'solid_fuel': 0.80,
                'floor_heating': 1.10
            },
            'parking': {
                'garage': 1.10,
                'spot': 1.05,
                'street': 1.00,
                'none': 0.95
            },
            'extras': {
                'terrace': 1.05,
                'balcony': 1.02,
                'basement_storage': 1.03,
                'elevator': 1.05,
                'security': 1.05,
                'garden': 1.08
            }
        }
        
        # Sezonski faktori
        self.seasonal_adjustments = {
            'winter': {'Zlatibor': 1.15, 'default': 0.98},
            'spring': {'default': 1.02},
            'summer': {'seaside': 1.20, 'default': 1.00},
            'fall': {'default': 0.98}
        }
        
    def calculate_zestimate(self, property_data: Dict, comparables: List[Dict] = None) -> Dict:
        """
        Glavni algoritam za procenu vrednosti
        
        Args:
            property_data: Podaci o nekretnini
            comparables: Lista sličnih prodatih nekretnina
            
        Returns:
            Dict sa procenom i svim faktorima
        """
        
        # 1. Bazna cena po m2 za lokaciju
        base_price_m2 = self._get_base_price_m2(property_data)
        
        if not base_price_m2:
            return None
            
        # 2. Primeni sve adjustment faktore
        adjusted_price_m2 = base_price_m2
        adjustments = {}
        
        # Sprat
        floor_factor = self._calculate_floor_factor(property_data)
        adjusted_price_m2 *= floor_factor
        adjustments['floor'] = floor_factor
        
        # Stanje i starost
        condition_factor = self._calculate_condition_factor(property_data)
        adjusted_price_m2 *= condition_factor
        adjustments['condition'] = condition_factor
        
        # Grejanje
        heating_factor = self._calculate_heating_factor(property_data)
        adjusted_price_m2 *= heating_factor
        adjustments['heating'] = heating_factor
        
        # Parking
        parking_factor = self._calculate_parking_factor(property_data)
        adjusted_price_m2 *= parking_factor
        adjustments['parking'] = parking_factor
        
        # Dodatni faktori
        extras_factor = self._calculate_extras_factor(property_data)
        adjusted_price_m2 *= extras_factor
        adjustments['extras'] = extras_factor
        
        # 3. Sezonska prilagođavanja
        seasonal_factor = self._get_seasonal_factor(property_data)
        adjusted_price_m2 *= seasonal_factor
        adjustments['seasonal'] = seasonal_factor
        
        # 4. Uporedi sa sličnim nekretninama (ako postoje)
        if comparables:
            comp_adjustment = self._analyze_comparables(property_data, comparables)
            adjusted_price_m2 *= comp_adjustment
            adjustments['comparables'] = comp_adjustment
        
        # 5. Finalna procena
        area = property_data.get('area', 0)
        estimated_value = adjusted_price_m2 * area
        
        # 6. Confidence score (0-100)
        confidence = self._calculate_confidence(property_data, comparables)
        
        # 7. Detektuj da li je dobra prilika
        asking_price = property_data.get('price')
        if asking_price:
            discount = (estimated_value - asking_price) / estimated_value
            is_good_deal = discount > 0.10  # 10%+ ispod procene
        else:
            discount = None
            is_good_deal = False
        
        return {
            'estimated_value': round(estimated_value, 0),
            'estimated_price_m2': round(adjusted_price_m2, 0),
            'base_price_m2': round(base_price_m2, 0),
            'adjustments': adjustments,
            'confidence_score': confidence,
            'asking_price': asking_price,
            'discount': discount,
            'is_good_deal': is_good_deal,
            'market_trend': self._get_market_trend(property_data),
            'investment_rating': self._calculate_investment_rating(
                property_data, estimated_value, discount
            )
        }
    
    def _get_base_price_m2(self, property_data: Dict) -> Optional[float]:
        """Dobija baznu cenu po m2 za lokaciju"""
        city = property_data.get('city', '').strip()
        municipality = property_data.get('municipality', '').strip()
        neighborhood = property_data.get('neighborhood', '').strip()
        
        # Beograd
        if city == 'Beograd' and city in self.market_data:
            for zone_name, zone_data in self.market_data['Beograd']['zones'].items():
                if municipality in zone_data.get('municipalities', []):
                    return zone_data['base_price_m2']
            # Default za Beograd
            return 2000
        
        # Novi Sad
        elif city == 'Novi Sad' and city in self.market_data:
            for zone_name, zone_data in self.market_data['Novi Sad']['zones'].items():
                if neighborhood in zone_data.get('neighborhoods', []):
                    return zone_data['base_price_m2']
            # Default za Novi Sad
            return 1500
        
        # Novi Pazar
        elif city == 'Novi Pazar':
            return self.market_data['Novi Pazar']['base_price_m2']
        
        # Zlatibor
        elif 'Zlatibor' in city or 'zlatibor' in city.lower():
            if 'centar' in neighborhood.lower():
                return self.market_data['Zlatibor']['zones']['centar']['base_price_m2']
            else:
                return self.market_data['Zlatibor']['zones']['periferija']['base_price_m2']
        
        # Default
        return None
    
    def _calculate_floor_factor(self, property_data: Dict) -> float:
        """Kalkuliše faktor za sprat"""
        floor = property_data.get('floor')
        total_floors = property_data.get('total_floors')
        has_elevator = property_data.get('has_elevator', False)
        
        if floor is None:
            return 1.0
        
        if floor == -1:
            return self.adjustment_factors['floor']['basement']
        elif floor == 0:
            return self.adjustment_factors['floor']['ground']
        elif floor == 1:
            return self.adjustment_factors['floor']['first']
        elif floor == total_floors:
            if has_elevator or (total_floors and total_floors <= 3):
                return self.adjustment_factors['floor']['top_with_elevator']
            else:
                return self.adjustment_factors['floor']['top_no_elevator']
        else:
            return self.adjustment_factors['floor']['middle']
    
    def _calculate_condition_factor(self, property_data: Dict) -> float:
        """Procenjuje stanje nekretnine"""
        title = property_data.get('title', '').lower()
        description = property_data.get('description', '').lower()
        all_text = title + ' ' + description
        
        # Ključne reči za stanje
        if any(word in all_text for word in ['lux', 'luksuzan', 'luksuzno']):
            return self.adjustment_factors['condition']['lux']
        elif any(word in all_text for word in ['nov', 'novogradnja', 'useljiv']):
            return self.adjustment_factors['condition']['excellent']
        elif any(word in all_text for word in ['renoviran', 'adaptiran']):
            return self.adjustment_factors['condition']['good']
        elif any(word in all_text for word in ['potrebno renoviranje', 'za renoviranje']):
            return self.adjustment_factors['condition']['needs_renovation']
        
        # Default
        return self.adjustment_factors['condition']['good']
    
    def _calculate_heating_factor(self, property_data: Dict) -> float:
        """Kalkuliše faktor za grejanje"""
        features = property_data.get('features', [])
        features_text = ' '.join(features).lower()
        
        if 'cg' in features_text or 'centralno grejanje' in features_text:
            return self.adjustment_factors['heating']['central_city']
        elif 'etažno' in features_text:
            return self.adjustment_factors['heating']['central_building']
        elif 'gas' in features_text:
            return self.adjustment_factors['heating']['gas']
        elif 'podno' in features_text:
            return self.adjustment_factors['heating']['floor_heating']
        
        return self.adjustment_factors['heating']['electric']
    
    def _calculate_parking_factor(self, property_data: Dict) -> float:
        """Kalkuliše faktor za parking"""
        all_text = (property_data.get('title', '') + ' ' + 
                   ' '.join(property_data.get('features', []))).lower()
        
        if 'garaž' in all_text:
            return self.adjustment_factors['parking']['garage']
        elif 'parking' in all_text:
            return self.adjustment_factors['parking']['spot']
        
        # U centru grada parking je važniji
        if property_data.get('municipality') in ['Vračar', 'Stari grad']:
            return self.adjustment_factors['parking']['none'] - 0.05
        
        return self.adjustment_factors['parking']['street']
    
    def _calculate_extras_factor(self, property_data: Dict) -> float:
        """Kalkuliše dodatne faktore"""
        factor = 1.0
        all_text = (property_data.get('title', '') + ' ' + 
                   ' '.join(property_data.get('features', []))).lower()
        
        if 'terasa' in all_text:
            factor *= self.adjustment_factors['extras']['terrace']
        if 'balkon' in all_text or 'lodja' in all_text:
            factor *= self.adjustment_factors['extras']['balcony']
        if 'podrum' in all_text or 'ostava' in all_text:
            factor *= self.adjustment_factors['extras']['basement_storage']
        if 'lift' in all_text:
            factor *= self.adjustment_factors['extras']['elevator']
        if 'security' in all_text or 'obezbeđenje' in all_text:
            factor *= self.adjustment_factors['extras']['security']
        
        return factor
    
    def _get_seasonal_factor(self, property_data: Dict) -> float:
        """Sezonski faktor"""
        month = datetime.now().month
        city = property_data.get('city', '')
        
        # Određi sezonu
        if month in [12, 1, 2]:
            season = 'winter'
        elif month in [3, 4, 5]:
            season = 'spring'
        elif month in [6, 7, 8]:
            season = 'summer'
        else:
            season = 'fall'
        
        # Zlatibor zimi
        if 'Zlatibor' in city and season == 'winter':
            return self.seasonal_adjustments['winter']['Zlatibor']
        
        return self.seasonal_adjustments[season].get('default', 1.0)
    
    def _analyze_comparables(self, property_data: Dict, comparables: List[Dict]) -> float:
        """Analizira slične prodate nekretnine"""
        if not comparables:
            return 1.0
        
        # Filtriraj samo relevantne
        relevant = []
        target_area = property_data.get('area', 0)
        
        for comp in comparables:
            comp_area = comp.get('area', 0)
            if comp_area > 0:
                area_diff = abs(comp_area - target_area) / target_area
                if area_diff < 0.3:  # Max 30% razlike
                    relevant.append(comp)
        
        if not relevant:
            return 1.0
        
        # Izračunaj prosečnu cenu po m2
        prices_per_m2 = []
        for comp in relevant:
            if comp.get('price') and comp.get('area'):
                prices_per_m2.append(comp['price'] / comp['area'])
        
        if prices_per_m2:
            avg_comp_price = statistics.median(prices_per_m2)
            # Ako imamo baznu cenu, uporedi
            base = self._get_base_price_m2(property_data)
            if base:
                return avg_comp_price / base
        
        return 1.0
    
    def _calculate_confidence(self, property_data: Dict, comparables: List[Dict]) -> int:
        """Kalkuliše confidence score (0-100)"""
        score = 50  # Početni score
        
        # Više informacija = veći confidence
        if property_data.get('area'):
            score += 10
        if property_data.get('rooms'):
            score += 10
        if property_data.get('floor') is not None:
            score += 5
        if property_data.get('municipality'):
            score += 10
        
        # Comparables povećavaju confidence
        if comparables:
            score += min(15, len(comparables) * 3)
        
        # Duplikati na više sajtova = veći confidence
        if property_data.get('found_on_sites', 0) > 1:
            score += 10
        
        return min(100, score)
    
    def _get_market_trend(self, property_data: Dict) -> Dict:
        """Vraća trend tržišta za lokaciju"""
        city = property_data.get('city', '')
        municipality = property_data.get('municipality', '')
        
        # Default trend
        trend = {
            'direction': 'stable',
            'yearly_change': 0.05,
            'forecast': 'stable growth'
        }
        
        # Beograd - brzi rast
        if city == 'Beograd':
            if municipality in ['Vračar', 'Stari grad']:
                trend['direction'] = 'rising'
                trend['yearly_change'] = 0.08
                trend['forecast'] = 'continued growth'
            elif municipality in ['Rakovica', 'Palilula']:
                trend['direction'] = 'rapidly rising'
                trend['yearly_change'] = 0.12
                trend['forecast'] = 'high growth potential'
        
        # Novi Pazar - najbrži rast
        elif city == 'Novi Pazar':
            trend['direction'] = 'rapidly rising'
            trend['yearly_change'] = 0.15
            trend['forecast'] = 'explosive growth - diaspora investment'
        
        return trend
    
    def _calculate_investment_rating(self, property_data: Dict, 
                                   estimated_value: float, 
                                   discount: Optional[float]) -> str:
        """
        Kalkuliše investment rating
        AAA - odlična investicija
        AA - vrlo dobra
        A - dobra
        B - prosečna
        C - loša
        """
        score = 0
        
        # Popust
        if discount:
            if discount > 0.20:
                score += 40
            elif discount > 0.10:
                score += 30
            elif discount > 0.05:
                score += 20
            elif discount > 0:
                score += 10
        
        # Lokacija
        city = property_data.get('city', '')
        municipality = property_data.get('municipality', '')
        
        if city == 'Beograd':
            if municipality in ['Vračar', 'Stari grad', 'Savski venac']:
                score += 30
            elif municipality in ['Novi Beograd', 'Zvezdara']:
                score += 25
            else:
                score += 20
        elif city == 'Novi Sad':
            score += 20
        elif city == 'Novi Pazar':
            score += 25  # Visok potencijal rasta
        
        # Veličina (likvidnost)
        area = property_data.get('area', 0)
        if 40 <= area <= 70:
            score += 20  # Idealna veličina
        elif 30 <= area <= 90:
            score += 15
        else:
            score += 5
        
        # Određi rating
        if score >= 80:
            return 'AAA'
        elif score >= 65:
            return 'AA'
        elif score >= 50:
            return 'A'
        elif score >= 35:
            return 'B'
        else:
            return 'C'
    
    def detect_market_manipulation(self, listings: List[Dict]) -> List[Dict]:
        """
        Detektuje tržišne manipulacije i prevare
        Vraća listu sumnjvih obrazaca
        """
        alerts = []
        
        # Grupiši po agentu/vlasniku
        by_owner = {}
        for listing in listings:
            owner = listing.get('agent', listing.get('owner', 'unknown'))
            if owner not in by_owner:
                by_owner[owner] = []
            by_owner[owner].append(listing)
        
        # Proveri obrasce
        for owner, props in by_owner.items():
            if len(props) > 5:
                # Isti vlasnik ima previše oglasa
                alerts.append({
                    'type': 'multiple_listings',
                    'owner': owner,
                    'count': len(props),
                    'message': f'Isti oglašivač ima {len(props)} oglasa - moguća agencija ili investitor'
                })
            
            # Proveri cene
            if len(props) > 2:
                prices = [p.get('price', 0) for p in props if p.get('price')]
                if prices:
                    avg_price = statistics.mean(prices)
                    for prop in props:
                        if prop.get('price'):
                            diff = abs(prop['price'] - avg_price) / avg_price
                            if diff > 0.5:  # 50% razlika
                                alerts.append({
                                    'type': 'price_manipulation',
                                    'property': prop,
                                    'message': 'Sumnjivo odstupanje cene od proseka istog oglašivača'
                                })
        
        # Proveri duplikate sa različitim cenama
        seen = {}
        for listing in listings:
            # Generiši ključ
            key = f"{listing.get('area', 0)}_{listing.get('municipality', '')}"
            
            if key in seen:
                price_diff = abs(listing.get('price', 0) - seen[key].get('price', 0))
                if price_diff > 10000:  # Razlika veća od 10k EUR
                    alerts.append({
                        'type': 'duplicate_different_price',
                        'listings': [seen[key], listing],
                        'price_difference': price_diff,
                        'message': f'Ista nekretnina sa razlikom u ceni od €{price_diff:,.0f}'
                    })
            else:
                seen[key] = listing
        
        return alerts


# Test
if __name__ == "__main__":
    estimator = SerbianZestimate()
    
    # Test nekretnine
    test_properties = [
        {
            'title': 'Lux stan na Vračaru, novogradnja',
            'city': 'Beograd',
            'municipality': 'Vračar',
            'area': 65,
            'rooms': 2.5,
            'floor': 3,
            'total_floors': 5,
            'price': 195000,
            'features': ['CG', 'Lift', 'Terasa', 'Parking mesto']
        },
        {
            'title': 'Stan u Novom Pazaru, centar',
            'city': 'Novi Pazar',
            'municipality': 'Centar',
            'area': 80,
            'rooms': 3,
            'floor': 2,
            'total_floors': 4,
            'price': 55000,
            'features': ['Etažno grejanje', 'Renoviran']
        }
    ]
    
    for prop in test_properties:
        print(f"\n{'='*60}")
        print(f"Nekretnina: {prop['title']}")
        print(f"Lokacija: {prop['city']}, {prop['municipality']}")
        print(f"Površina: {prop['area']}m², Cena: €{prop['price']:,}")
        
        estimate = estimator.calculate_zestimate(prop)
        
        if estimate:
            print(f"\nZESTIMATE ANALIZA:")
            print(f"  Procenjena vrednost: €{estimate['estimated_value']:,.0f}")
            print(f"  Procena po m²: €{estimate['estimated_price_m2']:,.0f}/m²")
            print(f"  Confidence: {estimate['confidence_score']}%")
            
            if estimate['discount'] is not None:
                if estimate['discount'] > 0:
                    print(f"  ✅ POTCENJENA za {estimate['discount']*100:.0f}%!")
                else:
                    print(f"  ❌ Precenjena za {abs(estimate['discount'])*100:.0f}%")
            
            print(f"  Investment Rating: {estimate['investment_rating']}")
            print(f"  Trend: {estimate['market_trend']['direction']} ({estimate['market_trend']['yearly_change']*100:.0f}% godišnje)")