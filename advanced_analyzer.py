#!/usr/bin/env python3
"""
Napredni analizator - radi bez dodatnih biblioteka
Analizira sve podatke i pronalazi prave prilike
"""
import json
import statistics
from datetime import datetime

class AdvancedAnalyzer:
    def __init__(self):
        # Realne cene po m² za Beograd (2024)
        self.municipality_avg_prices = {
            'Vračar': 3200,
            'Stari grad': 3500,
            'Savski venac': 3000,
            'Dedinje': 3500,
            'Novi Beograd': 2500,
            'Zvezdara': 2300,
            'Voždovac': 2100,
            'Čukarica': 1800,
            'Rakovica': 1700,
            'Palilula': 1900,
            'Zemun': 2000,
        }
        
    def analyze_property(self, prop):
        """Analizira pojedinačnu nekretninu"""
        # Izvuci osnovne podatke
        price = self.extract_price(prop.get('price', ''))
        area = self.extract_area(prop.get('features', []))
        rooms = self.extract_rooms(prop.get('features', []))
        floor_info = self.extract_floor(prop.get('features', []))
        location_data = self.parse_location(prop.get('location', ''))
        
        if not price or not area:
            return None
            
        price_per_m2 = price / area
        
        # Proceni fer cenu
        fair_price = self.estimate_fair_price(
            area, location_data, floor_info, prop.get('title', '')
        )
        
        if not fair_price:
            return None
            
        discount = (fair_price - price) / fair_price if fair_price > 0 else 0
        
        return {
            'id': prop.get('id'),
            'title': prop.get('title'),
            'price': price,
            'area': area,
            'rooms': rooms,
            'price_per_m2': price_per_m2,
            'location': location_data,
            'floor_info': floor_info,
            'fair_price': fair_price,
            'discount': discount,
            'discount_amount': fair_price - price,
            'link': prop.get('link'),
            'score': self.calculate_investment_score(
                price, area, location_data, discount, floor_info
            )
        }
    
    def extract_price(self, price_str):
        """Izvlači cenu iz stringa"""
        if '€' in price_str:
            try:
                return float(price_str.replace('€', '').replace('.', '').strip())
            except:
                return None
        return None
    
    def extract_area(self, features):
        """Izvlači površinu"""
        for feature in features:
            if 'm2' in feature:
                try:
                    return float(feature.replace('m2Kvadratura', '').strip())
                except:
                    pass
        return None
    
    def extract_rooms(self, features):
        """Izvlači broj soba"""
        for feature in features:
            if 'Broj soba' in feature:
                try:
                    return float(feature.replace('Broj soba', '').strip())
                except:
                    pass
        return None
    
    def extract_floor(self, features):
        """Izvlači informacije o spratu"""
        for feature in features:
            if 'Spratnost' in feature:
                floor_str = feature.replace('Spratnost', '').strip()
                # Pokušaj da parsiraš format "2/5" ili "PR/4"
                if '/' in floor_str:
                    parts = floor_str.split('/')
                    floor = parts[0]
                    total = parts[1] if len(parts) > 1 else None
                    
                    # Konvertuj sprat
                    if floor == 'PR':
                        floor = 0
                    elif floor == 'VPR':
                        floor = 0
                    elif floor == 'SUT':
                        floor = -1
                    else:
                        try:
                            floor = int(floor)
                        except:
                            floor = None
                    
                    # Konvertuj ukupno spratova
                    try:
                        total = int(total) if total else None
                    except:
                        total = None
                        
                    return {'floor': floor, 'total_floors': total}
        return {'floor': None, 'total_floors': None}
    
    def parse_location(self, location_str):
        """Parsira lokaciju"""
        # BeogradOpština VračarCvetni trgDesanke Maksimović
        data = {
            'city': None,
            'municipality': None,
            'neighborhood': None,
            'full': location_str
        }
        
        if 'Beograd' in location_str:
            data['city'] = 'Beograd'
            
            # Pronađi opštinu
            for mun in self.municipality_avg_prices.keys():
                if mun in location_str:
                    data['municipality'] = mun
                    break
                    
        return data
    
    def estimate_fair_price(self, area, location, floor_info, title):
        """Procenjuje fer cenu"""
        # Bazna cena po m²
        municipality = location.get('municipality')
        if municipality and municipality in self.municipality_avg_prices:
            base_price_per_m2 = self.municipality_avg_prices[municipality]
        elif location.get('city') == 'Beograd':
            base_price_per_m2 = 2300  # Prosek za Beograd
        else:
            return None
            
        # Faktori
        price_per_m2 = base_price_per_m2
        
        # Sprat
        floor = floor_info.get('floor')
        if floor is not None:
            if floor == 0:  # Prizemlje
                price_per_m2 *= 0.85
            elif floor == -1:  # Suteren
                price_per_m2 *= 0.70
            elif floor == floor_info.get('total_floors'):  # Poslednji
                price_per_m2 *= 0.95
                
        # Stanje (iz naslova)
        title_lower = title.lower()
        if 'lux' in title_lower or 'luksuzan' in title_lower:
            price_per_m2 *= 1.15
        elif 'renoviran' in title_lower:
            price_per_m2 *= 1.10
        elif 'hitno' in title_lower:
            price_per_m2 *= 0.90
            
        return price_per_m2 * area
    
    def calculate_investment_score(self, price, area, location, discount, floor_info):
        """Kalkuliše investment score (0-100)"""
        score = 0
        
        # Popust (max 30 poena)
        score += min(30, discount * 150)
        
        # Lokacija (max 30 poena)
        municipality = location.get('municipality')
        if municipality in ['Vračar', 'Stari grad', 'Savski venac']:
            score += 30
        elif municipality in ['Novi Beograd', 'Zvezdara']:
            score += 25
        elif municipality in ['Voždovac', 'Čukarica']:
            score += 20
        else:
            score += 10
            
        # Likvidnost - idealna površina (max 20 poena)
        if 40 <= area <= 65:
            score += 20  # Najpopularniji
        elif 25 <= area <= 40 or 65 <= area <= 85:
            score += 15
        else:
            score += 5
            
        # Sprat (max 20 poena)
        floor = floor_info.get('floor')
        if floor == 1 or floor == 2:
            score += 20  # Idealni spratovi
        elif floor == 0:
            score += 5   # Prizemlje
        else:
            score += 10
            
        return min(100, max(0, score))


def main():
    print("🏠 NAPREDNA ANALIZA NEKRETNINA")
    print("=" * 80)
    
    # Učitaj podatke
    with open('test_results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    analyzer = AdvancedAnalyzer()
    properties = data['search_results']
    
    # Analiziraj sve nekretnine
    analyzed = []
    for prop in properties:
        result = analyzer.analyze_property(prop)
        if result:
            analyzed.append(result)
    
    print(f"\n✅ Analizirano {len(analyzed)} nekretnina")
    
    # Sortiraj po score
    analyzed.sort(key=lambda x: x['score'], reverse=True)
    
    # Prikaži TOP prilike
    print("\n🏆 TOP INVESTICIONE PRILIKE:")
    print("=" * 80)
    
    for i, prop in enumerate(analyzed[:5], 1):
        print(f"\n{i}. {prop['title'][:60]}...")
        print(f"   📍 Lokacija: {prop['location']['city']}, {prop['location']['municipality'] or 'Nepoznata opština'}")
        print(f"   💰 Cena: €{prop['price']:,.0f} (€{prop['price_per_m2']:,.0f}/m²)")
        print(f"   📏 Površina: {prop['area']} m², {prop['rooms']} soba")
        
        if prop['floor_info']['floor'] is not None:
            print(f"   🏢 Sprat: {prop['floor_info']['floor']}/{prop['floor_info']['total_floors']}")
        
        print(f"\n   📊 ANALIZA:")
        print(f"      Procenjena vrednost: €{prop['fair_price']:,.0f}")
        
        if prop['discount'] > 0:
            print(f"      ✅ POTCENJENA za {prop['discount']*100:.0f}% (€{prop['discount_amount']:,.0f})")
        else:
            print(f"      ❌ PRECENJENA za {abs(prop['discount'])*100:.0f}%")
            
        print(f"      Investment Score: {prop['score']}/100")
        
        # ROI procena
        monthly_rent = prop['price'] * 0.004  # 0.4% mesečno
        yearly_roi = (monthly_rent * 12) / prop['price'] * 100
        print(f"\n   💸 PROCENA IZDAVANJA:")
        print(f"      Mesečna kirija: €{monthly_rent:.0f}")
        print(f"      Godišnji ROI: {yearly_roi:.1f}%")
        
        print(f"\n   🔗 {prop['link'][:70]}...")
        print("-" * 80)
    
    # Statistike po opštinama
    print("\n📊 STATISTIKE PO OPŠTINAMA:")
    by_municipality = {}
    for prop in analyzed:
        mun = prop['location'].get('municipality', 'Nepoznato')
        if mun not in by_municipality:
            by_municipality[mun] = {
                'count': 0,
                'prices': [],
                'discounts': []
            }
        by_municipality[mun]['count'] += 1
        by_municipality[mun]['prices'].append(prop['price_per_m2'])
        by_municipality[mun]['discounts'].append(prop['discount'])
    
    for mun, data in sorted(by_municipality.items()):
        if data['prices']:
            avg_price = sum(data['prices']) / len(data['prices'])
            avg_discount = sum(data['discounts']) / len(data['discounts'])
            print(f"\n{mun}:")
            print(f"  Broj nekretnina: {data['count']}")
            print(f"  Prosečna cena: €{avg_price:,.0f}/m²")
            if avg_discount > 0:
                print(f"  Prosečan popust: {avg_discount*100:.0f}%")
            else:
                print(f"  Prosečno precenjeno: {abs(avg_discount)*100:.0f}%")
    
    # Preporuke
    print("\n💡 PREPORUKE:")
    
    good_deals = [p for p in analyzed if p['discount'] > 0.05]
    if good_deals:
        print(f"✅ Pronađeno {len(good_deals)} potencijalno dobrih ponuda (5%+ ispod tržišne cene)")
        best = good_deals[0]
        print(f"   Najbolja: {best['title'][:50]}... - {best['discount']*100:.0f}% popust")
    else:
        print("❌ Trenutno nema značajno potcenjenih nekretnina u ovom uzorku")
        print("   Preporučujem da prikupiš više podataka sa: python3 find_deals.py --scrape")


if __name__ == "__main__":
    main()