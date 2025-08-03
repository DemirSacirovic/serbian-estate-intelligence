#!/usr/bin/env python3
"""
Zillow Hunter - Kompletni sistem za pronalaženje potcenjenih nekretnina u Srbiji
Kombinuje multi-site scraping, Zestimate analizu i fraud detection
"""
import sys
sys.path.append('src')

from scrapers.multi_site_scraper import MultiSiteScraper
from analysis.serbian_zestimate import SerbianZestimate
from notifications.deal_notifier import DealNotifier
import json
from datetime import datetime
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZillowHunter:
    """Glavni orchestrator za lov na nekretnine"""
    
    def __init__(self):
        self.scraper = MultiSiteScraper()
        self.estimator = SerbianZestimate()
        self.notifier = DealNotifier()
        self.results = []
        
    def hunt_deals(self, cities: List[str] = None, min_discount: float = 0.10):
        """
        Glavni proces lova na dobre ponude
        
        Args:
            cities: Lista gradova za skeniranje
            min_discount: Minimalni popust za alert (0.10 = 10%)
        """
        if not cities:
            cities = ['Beograd', 'Novi Sad', 'Novi Pazar', 'Zlatibor']
        
        print("🏹 ZILLOW HUNTER - Lov na potcenjene nekretnine")
        print("=" * 80)
        print(f"Gradovi: {', '.join(cities)}")
        print(f"Minimalni popust: {min_discount*100:.0f}%")
        print("=" * 80)
        
        all_deals = []
        fraud_alerts = []
        
        for city in cities:
            print(f"\n🏙️  {city}")
            print("-" * 40)
            
            # 1. Multi-site scraping
            print("📡 Skeniram sve sajtove...")
            city_data = self.scraper.scrape_all_sites(city)
            
            # Statistike
            total_listings = sum(len(site) for site in city_data['sites'].values())
            print(f"   ✓ {total_listings} oglasa")
            print(f"   ✓ {len(city_data['duplicates'])} duplikata")
            print(f"   ✓ {len(city_data['fraud_alerts'])} sumljivih")
            
            # 2. Zestimate analiza za sve nekretnine
            print("\n💰 Analiziram vrednosti...")
            analyzed_count = 0
            
            for site_name, listings in city_data['sites'].items():
                for listing in listings:
                    # Pripremi podatke
                    property_data = {
                        'title': listing.get('title', ''),
                        'price': listing.get('price'),
                        'area': listing.get('area'),
                        'rooms': listing.get('rooms'),
                        'city': city,
                        'location': listing.get('location', ''),
                        'features': listing.get('features', []),
                        'link': listing.get('link'),
                        'source': listing.get('source')
                    }
                    
                    # Pokušaj da ekstraktuješ opštinu
                    property_data['municipality'] = self._extract_municipality(
                        property_data['location'], city
                    )
                    
                    # Proceni vrednost
                    estimate = self.estimator.calculate_zestimate(property_data)
                    
                    if estimate and estimate.get('discount'):
                        analyzed_count += 1
                        
                        # Ako je dobra ponuda
                        if estimate['discount'] >= min_discount:
                            deal = {
                                'property': property_data,
                                'estimate': estimate,
                                'savings': estimate['estimated_value'] - property_data['price'],
                                'found_on': [listing['source']]
                            }
                            
                            # Proveri da li je duplikat
                            self._merge_or_add_deal(all_deals, deal)
            
            print(f"   ✓ Analizirano {analyzed_count} nekretnina")
            
            # 3. Dodaj fraud alerts
            fraud_alerts.extend(city_data['fraud_alerts'])
            
            # Pauza između gradova
            time.sleep(3)
        
        # 4. Sortiraj po investment rating i discount
        all_deals.sort(key=lambda x: (
            self._rating_to_score(x['estimate']['investment_rating']),
            x['estimate']['discount']
        ), reverse=True)
        
        # 5. Prikaži rezultate
        self._display_results(all_deals, fraud_alerts)
        
        # 6. Sačuvaj rezultate
        self._save_results(all_deals, fraud_alerts)
        
        # 7. Pošalji notifikacije za najbolje ponude
        if all_deals:
            top_deals = all_deals[:10]
            self._send_notifications(top_deals)
        
        return all_deals
    
    def _extract_municipality(self, location: str, city: str) -> str:
        """Ekstraktuje opštinu iz lokacije"""
        # Lista opština po gradovima
        municipalities = {
            'Beograd': [
                'Vračar', 'Stari grad', 'Savski venac', 'Novi Beograd',
                'Zvezdara', 'Voždovac', 'Čukarica', 'Rakovica', 'Zemun',
                'Palilula', 'Dedinje', 'Senjak'
            ],
            'Novi Sad': [
                'Centar', 'Stari grad', 'Liman', 'Grbavica', 'Novo naselje',
                'Detelinara', 'Klisa', 'Podbara'
            ]
        }
        
        city_municipalities = municipalities.get(city, [])
        
        for municipality in city_municipalities:
            if municipality.lower() in location.lower():
                return municipality
        
        return ''
    
    def _merge_or_add_deal(self, deals: List[Dict], new_deal: Dict):
        """Spaja duplikate ili dodaje novu ponudu"""
        # Proveri da li već postoji
        for existing in deals:
            if (abs(existing['property']['area'] - new_deal['property']['area']) < 2 and
                existing['property']['city'] == new_deal['property']['city'] and
                existing['property'].get('municipality') == new_deal['property'].get('municipality')):
                
                # Duplikat - dodaj source
                existing['found_on'].extend(new_deal['found_on'])
                
                # Ažuriraj cenu ako je niža
                if new_deal['property']['price'] < existing['property']['price']:
                    existing['property']['price'] = new_deal['property']['price']
                    existing['property']['link'] = new_deal['property']['link']
                    existing['estimate'] = new_deal['estimate']
                    existing['savings'] = new_deal['savings']
                
                return
        
        # Nova ponuda
        deals.append(new_deal)
    
    def _rating_to_score(self, rating: str) -> int:
        """Konvertuje rating u numerički score"""
        scores = {'AAA': 100, 'AA': 90, 'A': 80, 'B': 70, 'C': 60}
        return scores.get(rating, 50)
    
    def _display_results(self, deals: List[Dict], fraud_alerts: List[Dict]):
        """Prikazuje rezultate analize"""
        print("\n" + "=" * 80)
        print("📊 REZULTATI ANALIZE")
        print("=" * 80)
        
        if not deals:
            print("\n❌ Nema pronađenih ponuda sa zadatim kriterijumima.")
            return
        
        print(f"\n✅ Pronađeno {len(deals)} potencijalno dobrih ponuda!")
        
        # Top 10 ponuda
        print("\n🏆 TOP 10 INVESTICIONIH PRILIKA:")
        print("-" * 80)
        
        for i, deal in enumerate(deals[:10], 1):
            prop = deal['property']
            est = deal['estimate']
            
            print(f"\n{i}. {prop['title'][:60]}...")
            print(f"   📍 {prop['city']}, {prop.get('municipality', 'Nepoznata opština')}")
            print(f"   📏 {prop['area']}m², {prop.get('rooms', '?')} soba")
            
            print(f"\n   💰 FINANSIJSKA ANALIZA:")
            print(f"      Traži se: €{prop['price']:,.0f}")
            print(f"      Zestimate: €{est['estimated_value']:,.0f}")
            print(f"      Popust: {est['discount']*100:.0f}% (€{deal['savings']:,.0f})")
            print(f"      Rating: {est['investment_rating']} | Confidence: {est['confidence_score']}%")
            
            print(f"\n   📈 TRŽIŠNI TREND:")
            trend = est['market_trend']
            print(f"      {trend['direction'].upper()} - {trend['yearly_change']*100:.0f}% godišnje")
            print(f"      Prognoza: {trend['forecast']}")
            
            print(f"\n   🔍 PRONAĐENO NA:")
            print(f"      {', '.join(deal['found_on'])}")
            
            print(f"\n   🔗 {prop['link'][:70]}...")
            print("-" * 80)
        
        # Fraud alerts
        if fraud_alerts:
            print(f"\n⚠️  UPOZORENJA O PREVARAMA ({len(fraud_alerts)}):")
            print("-" * 80)
            
            for alert in fraud_alerts[:5]:
                print(f"\n❗ {alert['alerts'][0]['type']}")
                print(f"   {alert['property']['title'][:60]}...")
                for a in alert['alerts']:
                    print(f"   - {a['message']}")
        
        # Statistike po gradovima
        print("\n📊 STATISTIKE PO GRADOVIMA:")
        print("-" * 80)
        
        by_city = {}
        for deal in deals:
            city = deal['property']['city']
            if city not in by_city:
                by_city[city] = {'count': 0, 'avg_discount': [], 'ratings': []}
            
            by_city[city]['count'] += 1
            by_city[city]['avg_discount'].append(deal['estimate']['discount'])
            by_city[city]['ratings'].append(deal['estimate']['investment_rating'])
        
        for city, stats in by_city.items():
            avg_disc = sum(stats['avg_discount']) / len(stats['avg_discount']) * 100
            print(f"\n{city}:")
            print(f"  Ponuda: {stats['count']}")
            print(f"  Prosečan popust: {avg_disc:.0f}%")
            print(f"  Najbolji rating: {max(stats['ratings'])}")
    
    def _save_results(self, deals: List[Dict], fraud_alerts: List[Dict]):
        """Čuva rezultate u JSON"""
        filename = f"data/zillow_hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_deals': len(deals),
            'deals': deals[:50],  # Top 50
            'fraud_alerts': fraud_alerts,
            'summary': {
                'by_city': {},
                'by_rating': {}
            }
        }
        
        # Sumiranje
        for deal in deals:
            city = deal['property']['city']
            rating = deal['estimate']['investment_rating']
            
            if city not in data['summary']['by_city']:
                data['summary']['by_city'][city] = 0
            data['summary']['by_city'][city] += 1
            
            if rating not in data['summary']['by_rating']:
                data['summary']['by_rating'][rating] = 0
            data['summary']['by_rating'][rating] += 1
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Rezultati sačuvani u: {filename}")
    
    def _send_notifications(self, top_deals: List[Dict]):
        """Šalje notifikacije za najbolje ponude"""
        # Konvertuj u format za notifier
        formatted_deals = []
        
        for deal in top_deals:
            formatted_deals.append({
                'property': deal['property'],
                'current_price': deal['property']['price'],
                'fair_price': deal['estimate']['estimated_value'],
                'discount': deal['estimate']['discount'],
                'discount_amount': deal['savings'],
                'score': self._rating_to_score(deal['estimate']['investment_rating'])
            })
        
        # Pošalji (prikaži preview)
        print("\n📧 NOTIFIKACIJA PREVIEW:")
        print("-" * 80)
        self.notifier.send_deal_alert(formatted_deals, 'investor@example.com')


def main():
    """Glavni program"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Zillow Hunter - Pronađi potcenjene nekretnine')
    parser.add_argument('--cities', nargs='+', help='Gradovi za skeniranje', 
                       default=['Beograd', 'Novi Sad', 'Novi Pazar'])
    parser.add_argument('--discount', type=float, default=0.10, 
                       help='Minimalni popust (0.10 = 10%)')
    parser.add_argument('--email', type=str, help='Email za notifikacije')
    
    args = parser.parse_args()
    
    # Pokreni lov
    hunter = ZillowHunter()
    deals = hunter.hunt_deals(cities=args.cities, min_discount=args.discount)
    
    print(f"\n🎯 Lov završen! Pronađeno {len(deals)} potencijalnih prilika.")
    
    if deals:
        print("\n💡 PREPORUKE:")
        print("1. Proveri top 3 ponude uživo")
        print("2. Konsultuj advokata za papire")
        print("3. Pregovaraj za dodatnih 5-10% popusta")
        print("4. Deluj brzo - dobre ponude ne traju dugo!")


if __name__ == "__main__":
    main()