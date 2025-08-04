#!/usr/bin/env python3
"""
Estate Hunter Dashboard - Pregled rezultata
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import glob


class Dashboard:
    """Prikazuje rezultate Estate Hunter-a"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
    
    def show_latest_results(self):
        """Prikazuje najnovije rezultate"""
        # Pronađi najnoviji fajl
        result_files = glob.glob(os.path.join(self.data_dir, "hunt_results_*.json"))
        
        if not result_files:
            print("❌ Nema rezultata. Pokreni estate_hunter_pro.py prvo!")
            return
        
        latest_file = max(result_files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        opportunities = data.get('opportunities', [])
        report = data.get('report', {})
        
        # Header
        print("\n" + "="*80)
        print("🏠 ESTATE HUNTER DASHBOARD")
        print("="*80)
        print(f"📅 Poslednja analiza: {datetime.fromtimestamp(os.path.getctime(latest_file)).strftime('%d.%m.%Y %H:%M')}")
        print(f"📊 Pronađeno prilika: {len(opportunities)}")
        print(f"🔍 Skenirano oglasa: {report.get('stats', {}).get('total_scanned', 0)}")
        
        # Top 10
        print("\n🏆 TOP 10 INVESTICIONIH PRILIKA:")
        print("-"*80)
        
        for i, opp in enumerate(opportunities[:10], 1):
            self._print_opportunity(i, opp)
        
        # Statistike po gradovima
        print("\n📊 STATISTIKE PO GRADOVIMA:")
        print("-"*80)
        
        by_city = report.get('by_city', {})
        for city, city_opps in by_city.items():
            if city_opps:
                avg_discount = sum(o['estimate'].get('discount', 0) for o in city_opps) / len(city_opps)
                print(f"\n{city}:")
                print(f"  Prilika: {len(city_opps)}")
                print(f"  Prosečan popust: {avg_discount*100:.0f}%")
                
                # Top 3 za grad
                for j, opp in enumerate(city_opps[:3], 1):
                    prop = opp['property']
                    print(f"  {j}. {prop['title'][:40]}... - €{prop['price']:,} ({opp['estimate'].get('discount', 0)*100:.0f}%)")
        
        # Alerts
        alerts = report.get('alerts', {})
        if any(alerts.values()):
            print("\n🚨 VAŽNA UPOZORENJA:")
            print("-"*80)
            
            if alerts.get('price_drops'):
                print(f"\n💸 Pad cene ({len(alerts['price_drops'])} nekretnina):")
                for opp in alerts['price_drops'][:3]:
                    prop = opp['property']
                    print(f"  • {prop['title'][:50]}... - {prop['city']}")
            
            if alerts.get('desperate_sellers'):
                print(f"\n🔥 Očajni prodavci ({len(alerts['desperate_sellers'])} nekretnina):")
                for opp in alerts['desperate_sellers'][:3]:
                    prop = opp['property']
                    desp = opp.get('desperation', {})
                    print(f"  • {prop['title'][:50]}... - Score: {desp.get('desperation_score', 0)}/100")
        
        # Investment insights
        print("\n💡 INVESTICIONI UVIDI:")
        print("-"*80)
        
        extreme_deals = report.get('by_discount', {}).get('extreme', [])
        if extreme_deals:
            print(f"🌟 Ekstremni popusti (>25%): {len(extreme_deals)} nekretnina")
            best = extreme_deals[0]
            print(f"   Najbolja: {best['property']['title'][:50]}... - {best['estimate'].get('discount', 0)*100:.0f}% popust")
        
        # Preporuke
        self._print_recommendations(opportunities, report)
    
    def _print_opportunity(self, rank: int, opp: Dict):
        """Prikazuje pojedinačnu priliku"""
        prop = opp['property']
        est = opp['estimate']
        
        # Emoji na osnovu score-a
        if opp['score'] > 80:
            emoji = "🔥"
        elif opp['score'] > 60:
            emoji = "⭐"
        else:
            emoji = "💫"
        
        print(f"\n{emoji} #{rank}. {prop['title'][:60]}...")
        print(f"   📍 {prop['city']}, {prop.get('municipality', 'Nepoznato')}")
        print(f"   💰 Cena: €{prop['price']:,}")
        print(f"   📊 Procena: €{est.get('estimated_value', 0):,} ({est.get('discount', 0)*100:+.0f}%)")
        print(f"   📏 {prop.get('area', '?')}m², {prop.get('rooms', '?')} soba")
        print(f"   ⭐ Rating: {est.get('investment_rating', '?')} | Score: {opp['score']:.0f}")
        
        if opp.get('alerts'):
            print(f"   🚨 {', '.join(opp['alerts'])}")
        
        # ROI procena
        monthly_rent = prop['price'] * 0.004
        yearly_roi = (monthly_rent * 12) / prop['price'] * 100
        print(f"   💸 Est. kirija: €{monthly_rent:.0f}/mes ({yearly_roi:.1f}% ROI)")
    
    def _print_recommendations(self, opportunities: List[Dict], report: Dict):
        """Prikazuje preporuke"""
        print("\n📋 PREPORUKE:")
        
        # 1. Najbolja za flip
        flip_candidates = [o for o in opportunities if o['estimate'].get('discount', 0) > 0.15 and o['property']['area'] < 80]
        if flip_candidates:
            best_flip = flip_candidates[0]
            savings = best_flip['estimate']['estimated_value'] - best_flip['property']['price']
            print(f"\n🔄 Najbolja za FLIP:")
            print(f"   {best_flip['property']['title'][:50]}...")
            print(f"   Kupi za: €{best_flip['property']['price']:,}")
            print(f"   Prodaj za: €{best_flip['estimate']['estimated_value']:,}")
            print(f"   Profit: €{savings:,} ({best_flip['estimate']['discount']*100:.0f}%)")
        
        # 2. Najbolja za izdavanje
        rent_candidates = [o for o in opportunities if 40 <= o['property'].get('area', 0) <= 70]
        if rent_candidates:
            # Sortiraj po ROI
            rent_candidates.sort(key=lambda x: x['property']['price'], reverse=False)
            best_rent = rent_candidates[0]
            monthly = best_rent['property']['price'] * 0.004
            print(f"\n🏠 Najbolja za IZDAVANJE:")
            print(f"   {best_rent['property']['title'][:50]}...")
            print(f"   Cena: €{best_rent['property']['price']:,}")
            print(f"   Mesečna kirija: €{monthly:.0f}")
            print(f"   Godišnji ROI: {(monthly*12)/best_rent['property']['price']*100:.1f}%")
        
        # 3. Grad sa najvećim potencijalom
        by_city = report.get('by_city', {})
        if by_city:
            best_city = max(by_city.items(), key=lambda x: len(x[1]))
            print(f"\n🌆 Fokusiraj se na: {best_city[0]} ({len(best_city[1])} prilika)")
    
    def show_price_history(self):
        """Prikazuje istoriju cena"""
        history_file = os.path.join(self.data_dir, "price_history", "price_history.json")
        
        if not os.path.exists(history_file):
            print("❌ Nema istorije cena još uvek.")
            return
        
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        print("\n📈 ISTORIJA CENA")
        print("="*80)
        
        # Pronađi nekretnine sa najvećim padom
        drops = []
        for prop_id, data in history.items():
            if len(data['price_history']) > 1:
                first = data['price_history'][0]['price']
                last = data['price_history'][-1]['price']
                drop = (first - last) / first * 100
                
                if drop > 5:
                    drops.append({
                        'property': data['property_info'],
                        'drop_percent': drop,
                        'drop_amount': first - last,
                        'changes': len(data['price_history']) - 1,
                        'days': (datetime.fromisoformat(data['last_seen']) - 
                                datetime.fromisoformat(data['first_seen'])).days
                    })
        
        drops.sort(key=lambda x: x['drop_percent'], reverse=True)
        
        print(f"Praćeno nekretnina: {len(history)}")
        print(f"Sa padom cene: {len(drops)}")
        
        if drops:
            print("\n🔻 NAJVEĆI PADOVI CENA:")
            for i, drop in enumerate(drops[:10], 1):
                prop = drop['property']
                print(f"\n{i}. {prop['title'][:50]}...")
                print(f"   📍 {prop.get('location', 'Nepoznato')}")
                print(f"   📉 Pad: {drop['drop_percent']:.0f}% (€{drop['drop_amount']:,.0f})")
                print(f"   📅 Period: {drop['days']} dana, {drop['changes']} promena")


def main():
    """Glavni program"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Estate Hunter Dashboard')
    parser.add_argument('--history', action='store_true', help='Prikaži istoriju cena')
    
    args = parser.parse_args()
    
    dashboard = Dashboard()
    
    if args.history:
        dashboard.show_price_history()
    else:
        dashboard.show_latest_results()
    
    print("\n💡 Pokreni estate_hunter_pro.py za novu analizu")
    print("📱 Podesi Telegram bot za instant notifikacije")


if __name__ == "__main__":
    main()