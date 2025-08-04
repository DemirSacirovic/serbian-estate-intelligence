#!/usr/bin/env python3
"""
Estate Hunter Pro - Kompletni automatizovani sistem
Kombinuje sve komponente u jedan moćan alat
"""
import sys
sys.path.append('src')

from scrapers.multi_site_scraper import MultiSiteScraper
from analysis.serbian_zestimate import SerbianZestimate
from tracking.price_tracker import PriceTracker
from notifications.telegram_bot import TelegramNotifier
from notifications.deal_notifier import DealNotifier

import json
import time
import logging
from datetime import datetime
from typing import List, Dict
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EstateHunterPro:
    """Profesionalni lov na nekretnine - sve u jednom"""
    
    def __init__(self):
        self.scraper = MultiSiteScraper()
        self.estimator = SerbianZestimate()
        self.tracker = PriceTracker()
        self.telegram = TelegramNotifier()
        self.email_notifier = DealNotifier()
        
        # Učitaj konfiguraciju
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Učitava konfiguraciju"""
        config_file = 'config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default config
        return {
            'cities': ['Beograd', 'Novi Sad', 'Novi Pazar'],
            'min_discount': 0.10,
            'min_desperation_score': 60,
            'max_price': 200000,
            'min_area': 30,
            'max_area': 120,
            'preferred_municipalities': ['Vračar', 'Novi Beograd', 'Centar'],
            'notifications': {
                'telegram': True,
                'email': False,
                'min_rating': 'A'
            }
        }
    
    def run_complete_hunt(self):
        """Pokreće kompletan proces lova"""
        logger.info("🏹 ESTATE HUNTER PRO - Početak lova")
        start_time = time.time()
        
        all_opportunities = []
        market_stats = {
            'total_scanned': 0,
            'total_deals': 0,
            'price_drops': 0,
            'desperate_sellers': 0
        }
        
        # 1. Multi-site scraping za sve gradove
        for city in self.config['cities']:
            logger.info(f"\n📍 Obrađujem {city}...")
            
            city_data = self.scraper.scrape_all_sites(city)
            all_listings = []
            
            # Spoji sve listinge
            for site, listings in city_data['sites'].items():
                all_listings.extend(listings)
            
            market_stats['total_scanned'] += len(all_listings)
            
            # 2. Analiziraj svaku nekretninu
            for listing in all_listings:
                opportunity = self._analyze_listing(listing, city)
                
                if opportunity:
                    # 3. Prati cenu
                    self.tracker.track_property(listing)
                    
                    # 4. Proveri da li zadovoljava kriterijume
                    if self._meets_criteria(opportunity):
                        all_opportunities.append(opportunity)
                        market_stats['total_deals'] += 1
            
            # Pauza između gradova
            time.sleep(3)
        
        # 5. Analiziraj price history
        price_drops = self.tracker.get_price_drops()
        desperate_sellers = self.tracker.get_desperate_sellers()
        
        market_stats['price_drops'] = len(price_drops)
        market_stats['desperate_sellers'] = len(desperate_sellers)
        
        # 6. Kombinuj sve prilike
        all_opportunities = self._merge_with_history(
            all_opportunities, price_drops, desperate_sellers
        )
        
        # 7. Rangiraj prilike
        ranked_opportunities = self._rank_opportunities(all_opportunities)
        
        # 8. Generiši izveštaj
        report = self._generate_report(ranked_opportunities, market_stats)
        
        # 9. Pošalji notifikacije
        self._send_notifications(ranked_opportunities[:10], report)
        
        # 10. Sačuvaj rezultate
        self._save_results(ranked_opportunities, report)
        
        duration = time.time() - start_time
        logger.info(f"\n✅ Lov završen za {duration:.0f} sekundi")
        logger.info(f"📊 Pronađeno {len(ranked_opportunities)} prilika!")
        
        return ranked_opportunities
    
    def _analyze_listing(self, listing: Dict, city: str) -> Optional[Dict]:
        """Analizira pojedinačnu nekretninu"""
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
        
        # Ekstraktuj dodatne podatke
        property_data['municipality'] = self._extract_municipality(
            property_data['location'], city
        )
        
        # Preskoci ako nema osnovne podatke
        if not property_data['price'] or not property_data['area']:
            return None
        
        # Proceni vrednost
        estimate = self.estimator.calculate_zestimate(property_data)
        
        if not estimate:
            return None
        
        # Kreiraj opportunity objekat
        opportunity = {
            'property': property_data,
            'estimate': estimate,
            'score': self._calculate_opportunity_score(property_data, estimate),
            'alerts': []
        }
        
        # Dodaj alerts
        if estimate.get('discount', 0) > 0.20:
            opportunity['alerts'].append('HIGH_DISCOUNT')
        
        if 'hitno' in property_data['title'].lower():
            opportunity['alerts'].append('URGENT_SALE')
        
        return opportunity
    
    def _meets_criteria(self, opportunity: Dict) -> bool:
        """Proverava da li prilika zadovoljava kriterijume"""
        prop = opportunity['property']
        est = opportunity['estimate']
        
        # Cena
        if prop['price'] > self.config['max_price']:
            return False
        
        # Površina
        if (prop['area'] < self.config['min_area'] or 
            prop['area'] > self.config['max_area']):
            return False
        
        # Popust
        if est.get('discount', 0) < self.config['min_discount']:
            return False
        
        # Rating
        min_rating = self.config['notifications']['min_rating']
        if self._rating_to_score(est.get('investment_rating', 'C')) < self._rating_to_score(min_rating):
            return False
        
        return True
    
    def _merge_with_history(self, opportunities: List[Dict], 
                           price_drops: List[Dict], 
                           desperate_sellers: List[Dict]) -> List[Dict]:
        """Spaja trenutne prilike sa istorijskim podacima"""
        # Napravi mapu za brže pretraživanje
        opp_map = {}
        for opp in opportunities:
            key = f"{opp['property']['area']}_{opp['property']['city']}"
            opp_map[key] = opp
        
        # Dodaj price drop info
        for drop in price_drops:
            key = f"{drop['property']['area']}_{drop['property'].get('city', '')}"
            if key in opp_map:
                opp_map[key]['price_history'] = drop
                opp_map[key]['alerts'].append('PRICE_DROP')
        
        # Dodaj desperate seller info
        for seller in desperate_sellers:
            key = f"{seller['property']['area']}_{seller['property'].get('city', '')}"
            if key in opp_map:
                opp_map[key]['desperation'] = seller
                opp_map[key]['alerts'].append('DESPERATE_SELLER')
                # Boost score za očajne prodavce
                opp_map[key]['score'] *= 1.5
        
        return list(opp_map.values())
    
    def _rank_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """Rangira prilike po vrednosti"""
        # Sortiraj po score-u
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        # Dodaj rang
        for i, opp in enumerate(opportunities, 1):
            opp['rank'] = i
        
        return opportunities
    
    def _calculate_opportunity_score(self, property_data: Dict, estimate: Dict) -> float:
        """Kalkuliše score za priliku (0-100)"""
        score = 0
        
        # Popust (max 40 poena)
        discount = estimate.get('discount', 0)
        score += min(40, discount * 200)
        
        # Investment rating (max 30 poena)
        rating_score = self._rating_to_score(estimate.get('investment_rating', 'C'))
        score += (rating_score / 100) * 30
        
        # Lokacija (max 20 poena)
        if property_data.get('municipality') in self.config['preferred_municipalities']:
            score += 20
        elif property_data.get('city') in ['Beograd', 'Novi Sad']:
            score += 15
        else:
            score += 10
        
        # Likvidnost (max 10 poena)
        area = property_data.get('area', 0)
        if 40 <= area <= 70:
            score += 10
        elif 30 <= area <= 90:
            score += 7
        else:
            score += 3
        
        return score
    
    def _rating_to_score(self, rating: str) -> int:
        """Konvertuje rating u score"""
        scores = {'AAA': 100, 'AA': 90, 'A': 80, 'B': 70, 'C': 60}
        return scores.get(rating, 50)
    
    def _extract_municipality(self, location: str, city: str) -> str:
        """Ekstraktuje opštinu"""
        municipalities = {
            'Beograd': [
                'Vračar', 'Stari grad', 'Savski venac', 'Novi Beograd',
                'Zvezdara', 'Voždovac', 'Čukarica', 'Rakovica', 'Zemun',
                'Palilula', 'Dedinje', 'Senjak'
            ],
            'Novi Sad': [
                'Centar', 'Stari grad', 'Liman', 'Grbavica', 'Novo naselje'
            ]
        }
        
        for mun in municipalities.get(city, []):
            if mun.lower() in location.lower():
                return mun
        
        return ''
    
    def _generate_report(self, opportunities: List[Dict], stats: Dict) -> Dict:
        """Generiše detaljan izveštaj"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
            'top_opportunities': opportunities[:20],
            'by_city': {},
            'by_discount': {
                'extreme': [],  # >25%
                'high': [],     # 20-25%
                'good': [],     # 15-20%
                'moderate': []  # 10-15%
            },
            'alerts': {
                'price_drops': [],
                'desperate_sellers': [],
                'urgent_sales': []
            }
        }
        
        # Grupiši po gradovima
        for opp in opportunities:
            city = opp['property']['city']
            if city not in report['by_city']:
                report['by_city'][city] = []
            report['by_city'][city].append(opp)
        
        # Grupiši po popustu
        for opp in opportunities:
            discount = opp['estimate'].get('discount', 0)
            if discount > 0.25:
                report['by_discount']['extreme'].append(opp)
            elif discount > 0.20:
                report['by_discount']['high'].append(opp)
            elif discount > 0.15:
                report['by_discount']['good'].append(opp)
            elif discount > 0.10:
                report['by_discount']['moderate'].append(opp)
        
        # Izdvoj alerts
        for opp in opportunities:
            if 'PRICE_DROP' in opp.get('alerts', []):
                report['alerts']['price_drops'].append(opp)
            if 'DESPERATE_SELLER' in opp.get('alerts', []):
                report['alerts']['desperate_sellers'].append(opp)
            if 'URGENT_SALE' in opp.get('alerts', []):
                report['alerts']['urgent_sales'].append(opp)
        
        return report
    
    def _send_notifications(self, top_opportunities: List[Dict], report: Dict):
        """Šalje notifikacije"""
        if not self.config['notifications']['telegram']:
            return
        
        # Pošalji top prilike
        for opp in top_opportunities[:3]:
            self.telegram.send_deal_alert({
                'property': opp['property'],
                'estimate': opp['estimate'],
                'savings': opp['estimate']['estimated_value'] - opp['property']['price']
            })
            time.sleep(1)  # Da ne spam-ujemo
        
        # Pošalji desperate sellers
        for opp in report['alerts']['desperate_sellers'][:2]:
            if 'desperation' in opp:
                self.telegram.send_desperate_seller_alert(opp['desperation'])
                time.sleep(1)
        
        # Daily summary
        summary_stats = {
            'total_scanned': report['stats']['total_scanned'],
            'avg_discount': sum(o['estimate'].get('discount', 0) for o in top_opportunities) / len(top_opportunities) if top_opportunities else 0
        }
        
        self.telegram.send_daily_summary(top_opportunities[:5], summary_stats)
    
    def _save_results(self, opportunities: List[Dict], report: Dict):
        """Čuva rezultate"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Glavni rezultati
        results_file = f"data/hunt_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'opportunities': opportunities[:50],
                'report': report
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Rezultati sačuvani u: {results_file}")
        
        # Top 10 u zasebnom fajlu za brzi pregled
        top10_file = f"data/top10_{timestamp}.json"
        with open(top10_file, 'w', encoding='utf-8') as f:
            json.dump(opportunities[:10], f, ensure_ascii=False, indent=2)


def main():
    """Glavni program"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Estate Hunter Pro - Profesionalni lov na nekretnine'
    )
    parser.add_argument('--config', type=str, help='Putanja do config fajla')
    parser.add_argument('--test', action='store_true', help='Test mode')
    
    args = parser.parse_args()
    
    # ASCII Art
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║           ESTATE HUNTER PRO v2.0                  ║
    ║     Serbian Real Estate Intelligence System       ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    hunter = EstateHunterPro()
    
    if args.test:
        print("🧪 TEST MODE - Samo Beograd, max 2 stranice")
        hunter.config['cities'] = ['Beograd']
    
    # Pokreni lov
    opportunities = hunter.run_complete_hunt()
    
    # Prikaži top 5
    print("\n🏆 TOP 5 PRILIKA:")
    print("=" * 80)
    
    for opp in opportunities[:5]:
        prop = opp['property']
        est = opp['estimate']
        
        print(f"\n#{opp['rank']}. {prop['title'][:60]}...")
        print(f"   📍 {prop['city']}, {prop.get('municipality', '?')}")
        print(f"   💰 €{prop['price']:,.0f} (popust {est.get('discount', 0)*100:.0f}%)")
        print(f"   📏 {prop['area']}m², {prop.get('rooms', '?')} soba")
        print(f"   ⭐ Rating: {est.get('investment_rating', '?')} | Score: {opp['score']:.0f}")
        
        if opp.get('alerts'):
            print(f"   🚨 Alerts: {', '.join(opp['alerts'])}")
        
        print(f"   🔗 {prop['link'][:60]}...")
    
    print("\n✅ Lov završen! Proverite data/ folder za detaljne rezultate.")


if __name__ == "__main__":
    main()