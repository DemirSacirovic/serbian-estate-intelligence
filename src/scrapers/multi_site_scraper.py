"""
Multi-Site Scraper - Zillow model za Srbiju
Skrejpuje sve relevantne sajtove i detektuje prevare
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import hashlib
from typing import Dict, List, Optional
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiSiteScraper:
    """Scraper za sve srpske sajtove nekretnina"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Duplikati tracker
        self.seen_properties = {}  # hash -> property data
        self.duplicate_groups = {}  # group_id -> [property_ids]
        
    def scrape_all_sites(self, city: str, property_type: str = "prodaja-stanova") -> Dict:
        """Skrejpuje sve sajtove za dati grad"""
        all_results = {
            'city': city,
            'timestamp': datetime.now().isoformat(),
            'sites': {},
            'duplicates': [],
            'fraud_alerts': [],
            'best_deals': []
        }
        
        # 1. Halooglasi
        logger.info(f"Scraping halooglasi.com - {city}")
        halo_results = self._scrape_halooglasi(city, property_type)
        all_results['sites']['halooglasi'] = halo_results
        
        # 2. Nekretnine.rs  
        logger.info(f"Scraping nekretnine.rs - {city}")
        nekretnine_results = self._scrape_nekretnine_rs(city, property_type)
        all_results['sites']['nekretnine.rs'] = nekretnine_results
        
        # 3. 4zida.rs
        logger.info(f"Scraping 4zida.rs - {city}")
        cetiri_zida_results = self._scrape_4zida(city, property_type)
        all_results['sites']['4zida'] = cetiri_zida_results
        
        # 4. CityExpert
        logger.info(f"Scraping cityexpert.rs - {city}")
        cityexpert_results = self._scrape_cityexpert(city, property_type)
        all_results['sites']['cityexpert'] = cityexpert_results
        
        # Analiziraj duplikate i prevare
        all_results['duplicates'] = self._find_duplicates()
        all_results['fraud_alerts'] = self._detect_fraud()
        all_results['best_deals'] = self._find_best_deals()
        
        return all_results
    
    def _scrape_halooglasi(self, city: str, property_type: str, pages: int = 5) -> List[Dict]:
        """Skrejpuje halooglasi.com"""
        results = []
        city_slug = self._get_city_slug(city, 'halooglasi')
        
        for page in range(1, pages + 1):
            url = f"https://www.halooglasi.com/nekretnine/{property_type}/{city_slug}?page={page}"
            
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                listings = soup.find_all('div', class_='product-item')
                
                for listing in listings:
                    prop = self._parse_halooglasi_listing(listing)
                    if prop:
                        prop['source'] = 'halooglasi'
                        prop['source_trust'] = 0.9
                        self._add_to_seen(prop)
                        results.append(prop)
                
                time.sleep(2)  # Be nice
                
            except Exception as e:
                logger.error(f"Error scraping halooglasi page {page}: {str(e)}")
        
        return results
    
    def _scrape_nekretnine_rs(self, city: str, property_type: str, pages: int = 5) -> List[Dict]:
        """Skrejpuje nekretnine.rs"""
        results = []
        city_id = self._get_city_id(city, 'nekretnine.rs')
        
        for page in range(1, pages + 1):
            url = f"https://www.nekretnine.rs/stambeni-objekti/stanovi/lista/po-stranici/20/stranica/{page}"
            params = {
                'tip': 'prodaja',
                'grad_id': city_id,
                'cena_od': '10000',
                'cena_do': '1000000'
            }
            
            try:
                response = self.session.get(url, params=params, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                listings = soup.find_all('div', class_='offer-wrapper')
                
                for listing in listings:
                    prop = self._parse_nekretnine_listing(listing)
                    if prop:
                        prop['source'] = 'nekretnine.rs'
                        prop['source_trust'] = 0.85
                        self._add_to_seen(prop)
                        results.append(prop)
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping nekretnine.rs page {page}: {str(e)}")
        
        return results
    
    def _scrape_4zida(self, city: str, property_type: str, pages: int = 5) -> List[Dict]:
        """Skrejpuje 4zida.rs"""
        results = []
        
        for page in range(1, pages + 1):
            url = f"https://www.4zida.rs/prodaja-stanova/{city.lower()}?strana={page}"
            
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                listings = soup.find_all('div', class_='ed-card')
                
                for listing in listings:
                    prop = self._parse_4zida_listing(listing)
                    if prop:
                        prop['source'] = '4zida'
                        prop['source_trust'] = 0.8
                        self._add_to_seen(prop)
                        results.append(prop)
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping 4zida page {page}: {str(e)}")
        
        return results
    
    def _scrape_cityexpert(self, city: str, property_type: str, pages: int = 5) -> List[Dict]:
        """Skrejpuje cityexpert.rs"""
        results = []
        
        for page in range(1, pages + 1):
            url = f"https://cityexpert.rs/prodaja/stanova/{city.lower()}"
            params = {'strana': page}
            
            try:
                response = self.session.get(url, params=params, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                listings = soup.find_all('div', class_='property-card')
                
                for listing in listings:
                    prop = self._parse_cityexpert_listing(listing)
                    if prop:
                        prop['source'] = 'cityexpert'
                        prop['source_trust'] = 0.85
                        self._add_to_seen(prop)
                        results.append(prop)
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error scraping cityexpert page {page}: {str(e)}")
        
        return results
    
    def _parse_halooglasi_listing(self, listing) -> Optional[Dict]:
        """Parsira halooglasi listing"""
        try:
            title = listing.find('h3', class_='product-title')
            if not title:
                return None
                
            price_elem = listing.find('div', class_='central-feature')
            price = self._extract_price(price_elem.get_text()) if price_elem else None
            
            location = listing.find('ul', class_='subtitle-places')
            location_text = location.get_text(strip=True) if location else ""
            
            features = []
            feature_list = listing.find('ul', class_='product-features')
            if feature_list:
                features = [li.get_text(strip=True) for li in feature_list.find_all('li')]
            
            area = self._extract_area(features)
            rooms = self._extract_rooms(features)
            
            link = title.find('a')['href'] if title.find('a') else ""
            if not link.startswith('http'):
                link = 'https://www.halooglasi.com' + link
            
            return {
                'title': title.get_text(strip=True),
                'price': price,
                'location': location_text,
                'area': area,
                'rooms': rooms,
                'features': features,
                'link': link,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing halooglasi listing: {str(e)}")
            return None
    
    def _parse_nekretnine_listing(self, listing) -> Optional[Dict]:
        """Parsira nekretnine.rs listing"""
        try:
            title = listing.find('h2')
            if not title:
                return None
                
            price_elem = listing.find('p', class_='offer-price')
            price = self._extract_price(price_elem.get_text()) if price_elem else None
            
            location = listing.find('p', class_='offer-location')
            location_text = location.get_text(strip=True) if location else ""
            
            # Površina i sobe
            area_elem = listing.find('p', class_='offer-price offer-price--invert')
            area_text = area_elem.get_text() if area_elem else ""
            area = self._extract_area_from_text(area_text)
            
            rooms_text = listing.get_text()
            rooms = self._extract_rooms_from_text(rooms_text)
            
            link = listing.find('a')['href'] if listing.find('a') else ""
            if not link.startswith('http'):
                link = 'https://www.nekretnine.rs' + link
            
            return {
                'title': title.get_text(strip=True),
                'price': price,
                'location': location_text,
                'area': area,
                'rooms': rooms,
                'link': link,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing nekretnine.rs listing: {str(e)}")
            return None
    
    def _add_to_seen(self, property_data: Dict):
        """Dodaje nekretninu u seen tracker za duplikate"""
        # Generiši hash na osnovu lokacije, površine i broja soba
        key_parts = [
            str(property_data.get('area', '')),
            str(property_data.get('rooms', '')),
            property_data.get('location', '')[:30]  # Prvih 30 karaktera lokacije
        ]
        
        hash_key = hashlib.md5(''.join(key_parts).encode()).hexdigest()
        
        if hash_key not in self.seen_properties:
            self.seen_properties[hash_key] = []
        
        self.seen_properties[hash_key].append(property_data)
    
    def _find_duplicates(self) -> List[Dict]:
        """Pronalazi duplikate između sajtova"""
        duplicates = []
        
        for hash_key, properties in self.seen_properties.items():
            if len(properties) > 1:
                # Ista nekretnina na više sajtova
                prices = [p['price'] for p in properties if p['price']]
                
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    price_diff = (max_price - min_price) / min_price if min_price > 0 else 0
                    
                    duplicate_info = {
                        'properties': properties,
                        'min_price': min_price,
                        'max_price': max_price,
                        'price_difference': price_diff,
                        'recommended_price': min_price * 0.95,  # 5% ispod najniže
                        'sources': [p['source'] for p in properties]
                    }
                    
                    duplicates.append(duplicate_info)
        
        return duplicates
    
    def _detect_fraud(self) -> List[Dict]:
        """Detektuje potencijalne prevare"""
        fraud_alerts = []
        
        for properties in self.seen_properties.values():
            for prop in properties:
                alerts = []
                
                # 1. "Hitno" u naslovu
                if 'hitno' in prop.get('title', '').lower():
                    alerts.append({
                        'type': 'fake_urgency',
                        'message': 'Oglas sadrži "hitno" - često znak nerealne cene'
                    })
                
                # 2. Previše buzzwords
                title = prop.get('title', '').lower()
                buzzwords = ['lux', 'ekskluziv', 'jedinstven', 'neponovljiv', 'specijal']
                buzzword_count = sum(1 for word in buzzwords if word in title)
                if buzzword_count >= 2:
                    alerts.append({
                        'type': 'overselling',
                        'message': f'Previše reklamnih reči ({buzzword_count}) - verovatno precenjeno'
                    })
                
                # 3. Sumnjivo niska cena
                if prop.get('price') and prop.get('area'):
                    price_per_m2 = prop['price'] / prop['area']
                    
                    # Za Beograd
                    if 'beograd' in prop.get('location', '').lower():
                        if price_per_m2 < 800:
                            alerts.append({
                                'type': 'too_cheap',
                                'message': f'Sumnjivo niska cena: €{price_per_m2:.0f}/m² za Beograd'
                            })
                
                if alerts:
                    fraud_alerts.append({
                        'property': prop,
                        'alerts': alerts
                    })
        
        return fraud_alerts
    
    def _find_best_deals(self) -> List[Dict]:
        """Pronalazi najbolje ponude kros-referencirajući sajtove"""
        best_deals = []
        
        # Analiziraj duplikate
        for dup in self._find_duplicates():
            if dup['price_difference'] > 0.1:  # Razlika veća od 10%
                # Uzmi najjeftiniju verziju
                cheapest = min(dup['properties'], key=lambda x: x['price'] or float('inf'))
                
                deal = {
                    'property': cheapest,
                    'reason': f"Ista nekretnina €{dup['max_price']-dup['min_price']:,.0f} jeftinija na {cheapest['source']}",
                    'savings': dup['max_price'] - dup['min_price'],
                    'other_prices': {p['source']: p['price'] for p in dup['properties']}
                }
                
                best_deals.append(deal)
        
        return best_deals
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Ekstraktuje cenu iz teksta"""
        text = text.replace('.', '').replace(',', '')
        
        # EUR
        eur_match = re.search(r'(\d+)\s*€', text)
        if eur_match:
            return float(eur_match.group(1))
        
        # RSD
        rsd_match = re.search(r'(\d+)\s*(?:RSD|din)', text, re.IGNORECASE)
        if rsd_match:
            return float(rsd_match.group(1)) / 117  # Konverzija u EUR
        
        return None
    
    def _extract_area(self, features: List[str]) -> Optional[float]:
        """Ekstraktuje površinu iz feature liste"""
        for feature in features:
            if 'm2' in feature or 'm²' in feature:
                match = re.search(r'(\d+(?:\.\d+)?)', feature)
                if match:
                    return float(match.group(1))
        return None
    
    def _extract_area_from_text(self, text: str) -> Optional[float]:
        """Ekstraktuje površinu iz teksta"""
        match = re.search(r'(\d+(?:\.\d+)?)\s*m[2²]', text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_rooms(self, features: List[str]) -> Optional[float]:
        """Ekstraktuje broj soba iz feature liste"""
        for feature in features:
            if 'sob' in feature.lower():
                match = re.search(r'(\d+(?:\.\d+)?)', feature)
                if match:
                    return float(match.group(1))
        return None
    
    def _extract_rooms_from_text(self, text: str) -> Optional[float]:
        """Ekstraktuje broj soba iz teksta"""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:soba|soban)',
            r'(?:jedno|dvo|tro|četvoro)(?:soban|sobni)',
            r'garsonjera'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'jedno' in text.lower():
                    return 1.0
                elif 'dvo' in text.lower():
                    return 2.0
                elif 'tro' in text.lower():
                    return 3.0
                elif 'četvoro' in text.lower():
                    return 4.0
                elif 'garson' in text.lower():
                    return 0.5
                else:
                    try:
                        return float(match.group(1))
                    except:
                        pass
        return None
    
    def _get_city_slug(self, city: str, site: str) -> str:
        """Vraća slug grada za dati sajt"""
        slugs = {
            'halooglasi': {
                'Beograd': 'beograd',
                'Novi Sad': 'novi-sad',
                'Novi Pazar': 'novi-pazar',
                'Zlatibor': 'zlatibor',
                'Niš': 'nis'
            }
        }
        return slugs.get(site, {}).get(city, city.lower())
    
    def _get_city_id(self, city: str, site: str) -> str:
        """Vraća ID grada za dati sajt"""
        ids = {
            'nekretnine.rs': {
                'Beograd': '1',
                'Novi Sad': '2',
                'Novi Pazar': '20',
                'Zlatibor': '427',
                'Niš': '3'
            }
        }
        return ids.get(site, {}).get(city, '1')
    
    def _parse_4zida_listing(self, listing) -> Optional[Dict]:
        """Parsira 4zida listing"""
        # Implementacija slična kao za druge sajtove
        return None
    
    def _parse_cityexpert_listing(self, listing) -> Optional[Dict]:
        """Parsira cityexpert listing"""
        # Implementacija slična kao za druge sajtove
        return None


if __name__ == "__main__":
    scraper = MultiSiteScraper()
    
    # Skeniraj gradove
    cities = ['Beograd', 'Novi Sad', 'Novi Pazar', 'Zlatibor']
    
    for city in cities:
        print(f"\n🏙️  Skeniram {city}...")
        results = scraper.scrape_all_sites(city)
        
        # Sačuvaj rezultate
        filename = f"data/{city.lower()}_multi_site_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {city} završen. Pronađeno:")
        print(f"   - {sum(len(site) for site in results['sites'].values())} ukupno oglasa")
        print(f"   - {len(results['duplicates'])} duplikata")
        print(f"   - {len(results['fraud_alerts'])} sumjivih oglasa")
        print(f"   - {len(results['best_deals'])} dobrih ponuda")
        print(f"   Sačuvano u: {filename}")