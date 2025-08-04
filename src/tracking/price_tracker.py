"""
Price Tracker - Prati promene cena nekretnina kroz vreme
Ključno za identifikaciju očajnih prodavaca
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib
import logging

logger = logging.getLogger(__name__)


class PriceTracker:
    """Prati istoriju cena i detektuje obrasce"""
    
    def __init__(self, data_dir: str = "data/price_history"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.history_file = os.path.join(data_dir, "price_history.json")
        self.alerts_file = os.path.join(data_dir, "price_alerts.json")
        self._load_history()
    
    def _load_history(self):
        """Učitava postojeću istoriju"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
        else:
            self.history = {}
    
    def _save_history(self):
        """Čuva istoriju"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def track_property(self, property_data: Dict):
        """Prati cenu nekretnine"""
        # Generiši jedinstveni ID
        prop_id = self._generate_property_id(property_data)
        
        # Trenutna cena i vreme
        current_price = property_data.get('price')
        current_time = datetime.now().isoformat()
        
        if not current_price:
            return
        
        # Inicijalizuj istoriju ako ne postoji
        if prop_id not in self.history:
            self.history[prop_id] = {
                'property_info': {
                    'title': property_data.get('title'),
                    'location': property_data.get('location'),
                    'area': property_data.get('area'),
                    'rooms': property_data.get('rooms'),
                    'link': property_data.get('link')
                },
                'price_history': [],
                'first_seen': current_time,
                'last_seen': current_time,
                'total_drops': 0,
                'total_increases': 0,
                'max_price': current_price,
                'min_price': current_price
            }
        
        # Ažuriraj istoriju
        history = self.history[prop_id]
        price_history = history['price_history']
        
        # Proveri da li se cena promenila
        if not price_history or price_history[-1]['price'] != current_price:
            price_change = {
                'price': current_price,
                'timestamp': current_time,
                'source': property_data.get('source', 'unknown')
            }
            
            # Izračunaj promenu
            if price_history:
                last_price = price_history[-1]['price']
                change_amount = current_price - last_price
                change_percent = (change_amount / last_price) * 100
                
                price_change['change_amount'] = change_amount
                price_change['change_percent'] = change_percent
                
                # Ažuriraj statistike
                if change_amount < 0:
                    history['total_drops'] += 1
                else:
                    history['total_increases'] += 1
            
            price_history.append(price_change)
        
        # Ažuriraj min/max
        history['max_price'] = max(history['max_price'], current_price)
        history['min_price'] = min(history['min_price'], current_price)
        history['last_seen'] = current_time
        
        self._save_history()
    
    def _generate_property_id(self, property_data: Dict) -> str:
        """Generiše jedinstveni ID za nekretninu"""
        # Kombinuj ključne karakteristike
        key_parts = [
            str(property_data.get('area', '')),
            str(property_data.get('rooms', '')),
            property_data.get('city', ''),
            property_data.get('municipality', ''),
            # Uzmi samo početak naslova (bez "HITNO" itd)
            property_data.get('title', '')[:30]
        ]
        
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_price_drops(self, min_drop_percent: float = 5.0) -> List[Dict]:
        """Vraća nekretnine čija je cena pala"""
        drops = []
        
        for prop_id, data in self.history.items():
            if len(data['price_history']) < 2:
                continue
            
            # Ukupan pad od prvog do poslednjeg
            first_price = data['price_history'][0]['price']
            last_price = data['price_history'][-1]['price']
            total_drop_percent = ((first_price - last_price) / first_price) * 100
            
            if total_drop_percent >= min_drop_percent:
                drop_info = {
                    'property': data['property_info'],
                    'current_price': last_price,
                    'original_price': first_price,
                    'total_drop_percent': total_drop_percent,
                    'total_drop_amount': first_price - last_price,
                    'days_on_market': self._calculate_days_on_market(data),
                    'price_changes': len(data['price_history']) - 1,
                    'desperation_score': self._calculate_desperation_score(data)
                }
                drops.append(drop_info)
        
        # Sortiraj po desperation score
        drops.sort(key=lambda x: x['desperation_score'], reverse=True)
        
        return drops
    
    def _calculate_days_on_market(self, history_data: Dict) -> int:
        """Kalkuliše koliko dana je nekretnina na tržištu"""
        first_seen = datetime.fromisoformat(history_data['first_seen'])
        last_seen = datetime.fromisoformat(history_data['last_seen'])
        return (last_seen - first_seen).days
    
    def _calculate_desperation_score(self, history_data: Dict) -> float:
        """
        Kalkuliše koliko je prodavac očajan (0-100)
        Viši score = veća šansa za dobru ponudu
        """
        score = 0
        
        # Broj smanjenja cene
        drops = history_data['total_drops']
        score += min(30, drops * 10)  # Max 30 poena
        
        # Vreme na tržištu
        days = self._calculate_days_on_market(history_data)
        if days > 90:
            score += 20
        elif days > 60:
            score += 15
        elif days > 30:
            score += 10
        
        # Ukupan pad cene
        if history_data['price_history']:
            first = history_data['price_history'][0]['price']
            last = history_data['price_history'][-1]['price']
            drop_percent = ((first - last) / first) * 100
            score += min(30, drop_percent)  # Max 30 poena
        
        # Učestalost promena
        if len(history_data['price_history']) > 1 and days > 0:
            changes_per_month = (len(history_data['price_history']) / days) * 30
            if changes_per_month > 3:
                score += 20  # Često menja = očajan
        
        return min(100, score)
    
    def get_desperate_sellers(self, min_score: float = 60) -> List[Dict]:
        """Pronalazi očajne prodavce"""
        desperate = []
        
        for prop_id, data in self.history.items():
            score = self._calculate_desperation_score(data)
            
            if score >= min_score:
                desperate.append({
                    'property': data['property_info'],
                    'desperation_score': score,
                    'current_price': data['price_history'][-1]['price'] if data['price_history'] else None,
                    'days_on_market': self._calculate_days_on_market(data),
                    'total_drops': data['total_drops'],
                    'recommendation': self._get_negotiation_recommendation(data, score)
                })
        
        desperate.sort(key=lambda x: x['desperation_score'], reverse=True)
        return desperate
    
    def _get_negotiation_recommendation(self, history_data: Dict, desperation_score: float) -> Dict:
        """Daje preporuke za pregovaranje"""
        last_price = history_data['price_history'][-1]['price'] if history_data['price_history'] else 0
        
        # Bazna preporuka
        if desperation_score >= 80:
            suggested_offer = last_price * 0.80  # 20% ispod
            strategy = "AGRESIVNO - Prodavac je vrlo očajan"
        elif desperation_score >= 60:
            suggested_offer = last_price * 0.85  # 15% ispod
            strategy = "UMERENO - Dobra pozicija za pregovaranje"
        else:
            suggested_offer = last_price * 0.90  # 10% ispod
            strategy = "OPREZNO - Prodavac još nije dovoljno motivisan"
        
        return {
            'suggested_offer': suggested_offer,
            'minimum_offer': last_price * 0.75,  # Nikad ispod 75%
            'maximum_offer': last_price * 0.95,  # Nikad više od 95%
            'strategy': strategy,
            'talking_points': self._get_talking_points(history_data)
        }
    
    def _get_talking_points(self, history_data: Dict) -> List[str]:
        """Generiše argumente za pregovaranje"""
        points = []
        
        days = self._calculate_days_on_market(history_data)
        if days > 60:
            points.append(f"Nekretnina je na tržištu već {days} dana")
        
        if history_data['total_drops'] > 2:
            points.append(f"Cena je već spuštana {history_data['total_drops']} puta")
        
        if history_data['price_history']:
            total_drop = history_data['max_price'] - history_data['min_price']
            if total_drop > 10000:
                points.append(f"Ukupno spuštanje cene: €{total_drop:,.0f}")
        
        # Sezonski faktori
        month = datetime.now().month
        if month in [11, 12, 1, 2]:
            points.append("Zimski period - manja potražnja")
        
        return points
    
    def generate_alert_report(self) -> Dict:
        """Generiše izveštaj o price drop alertima"""
        drops = self.get_price_drops(min_drop_percent=5.0)
        desperate = self.get_desperate_sellers(min_score=60)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tracked': len(self.history),
            'price_drops': {
                'count': len(drops),
                'total_savings': sum(d['total_drop_amount'] for d in drops),
                'top_drops': drops[:10]
            },
            'desperate_sellers': {
                'count': len(desperate),
                'top_opportunities': desperate[:5]
            },
            'market_insights': self._generate_market_insights()
        }
        
        # Sačuvaj alerts
        with open(self.alerts_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
    
    def _generate_market_insights(self) -> Dict:
        """Generiše uvide u tržište na osnovu praćenja"""
        total_properties = len(self.history)
        properties_with_drops = sum(1 for p in self.history.values() if p['total_drops'] > 0)
        
        avg_days_on_market = 0
        total_days = 0
        count = 0
        
        for data in self.history.values():
            days = self._calculate_days_on_market(data)
            if days > 0:
                total_days += days
                count += 1
        
        if count > 0:
            avg_days_on_market = total_days / count
        
        return {
            'properties_tracked': total_properties,
            'properties_with_price_drops': properties_with_drops,
            'drop_percentage': (properties_with_drops / total_properties * 100) if total_properties > 0 else 0,
            'average_days_on_market': avg_days_on_market,
            'market_condition': self._assess_market_condition(properties_with_drops, total_properties)
        }
    
    def _assess_market_condition(self, drops: int, total: int) -> str:
        """Procenjuje stanje tržišta"""
        if total == 0:
            return "Nedovoljno podataka"
        
        drop_rate = drops / total
        
        if drop_rate > 0.5:
            return "BUYER'S MARKET - Odlično vreme za kupovinu!"
        elif drop_rate > 0.3:
            return "BALANSOVANO - Dobra prilika za pregovaranje"
        else:
            return "SELLER'S MARKET - Cene su stabilne"


# Test
if __name__ == "__main__":
    tracker = PriceTracker()
    
    # Simuliraj praćenje
    test_property = {
        'title': 'Stan na Vračaru 65m2',
        'price': 150000,
        'area': 65,
        'rooms': 2,
        'city': 'Beograd',
        'municipality': 'Vračar',
        'link': 'https://example.com/stan1'
    }
    
    # Dan 1
    tracker.track_property(test_property)
    
    # Dan 15 - prva promena
    test_property['price'] = 145000
    tracker.track_property(test_property)
    
    # Dan 30 - druga promena
    test_property['price'] = 140000
    tracker.track_property(test_property)
    
    # Dan 45 - očajan
    test_property['price'] = 130000
    tracker.track_property(test_property)
    
    # Generiši izveštaj
    report = tracker.generate_alert_report()
    
    print("📊 PRICE TRACKING REPORT")
    print("=" * 60)
    print(f"Ukupno praćeno: {report['total_tracked']} nekretnina")
    print(f"Sa padom cene: {report['price_drops']['count']}")
    print(f"Ukupna ušteda: €{report['price_drops']['total_savings']:,.0f}")
    
    print("\n🔥 OČAJNI PRODAVCI:")
    for seller in report['desperate_sellers']['top_opportunities']:
        print(f"\n- {seller['property']['title']}")
        print(f"  Desperation Score: {seller['desperation_score']}/100")
        print(f"  Trenutna cena: €{seller['current_price']:,.0f}")
        print(f"  Preporuka: {seller['recommendation']['strategy']}")
        print(f"  Predloži: €{seller['recommendation']['suggested_offer']:,.0f}")