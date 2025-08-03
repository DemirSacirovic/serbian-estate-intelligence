#!/usr/bin/env python3
"""
Find Deals - Glavni script za pronalaženje potcenjenih nekretnina
"""
import sys
import os
import argparse
from datetime import datetime

sys.path.append('src')

from database.db_manager import DatabaseManager
from scrapers.scrape_manager import ScrapeManager
from processors.data_processor import DataProcessor
from analysis.deal_finder import DealFinder
from analysis.realistic_deal_finder import RealisticDealFinder
from notifications.deal_notifier import DealNotifier


def run_full_analysis(email_recipient: str = None, discount_threshold: float = 0.15):
    """Pokreće kompletnu analizu: scraping -> processing -> analiza -> notifikacije"""
    
    print("🚀 Serbian Estate Intelligence - Deal Finder")
    print("=" * 50)
    
    # 1. Scraping novih podataka
    print("\n📡 KORAK 1: Prikupljanje novih oglasa...")
    scraper = ScrapeManager()
    
    # Skeniraj samo prodaju stanova u Beogradu (za početak)
    new_properties = scraper.scrape_multiple_pages(
        property_type="prodaja-stanova",
        location="beograd",
        max_pages=5  # Prvih 5 stranica
    )
    
    print(f"✓ Prikupljeno {len(new_properties)} novih oglasa")
    
    # 2. Procesiranje podataka
    print("\n🔧 KORAK 2: Procesiranje podataka...")
    processor = DataProcessor()
    processed = processor.process_batch(new_properties)
    
    # Dodaj tip nekretnine
    for prop in processed:
        prop['property_type'] = 'stan'
        prop['listing_type'] = 'prodaja'
    
    print(f"✓ Procesirano {len(processed)} nekretnina")
    
    # 3. Čuvanje u bazu
    print("\n💾 KORAK 3: Čuvanje u bazu...")
    db = DatabaseManager()
    saved_count = db.insert_batch(processed)
    print(f"✓ Sačuvano {saved_count} nekretnina")
    
    # 4. Analiza i pronalaženje ponuda
    print(f"\n🔍 KORAK 4: Tražim nekretnine sa min {discount_threshold*100}% popusta...")
    finder = DealFinder(db)
    deals = finder.find_underpriced_properties(discount_threshold=discount_threshold)
    
    print(f"✓ Pronađeno {len(deals)} potcenjenih nekretnina!")
    
    # 5. Prikaz rezultata
    print("\n🏠 TOP 10 PONUDA:")
    print("=" * 100)
    
    for i, deal in enumerate(deals[:10], 1):
        print(f"\n{i}. {deal['property']['title']}")
        print(f"   📍 Lokacija: {deal['property']['city']}, {deal['property']['municipality']}")
        print(f"   💰 Cena: €{deal['current_price']:,.0f} (fer cena: €{deal['fair_price']:,.0f})")
        print(f"   📉 Popust: {deal['discount']*100:.1f}% (ušteda: €{deal['discount_amount']:,.0f})")
        print(f"   📏 Površina: {deal['property']['area_m2']} m²")
        print(f"   🏠 Sobe: {deal['property']['rooms']}")
        print(f"   ⭐ Score: {deal['score']}/100")
        print(f"   🔗 Link: {deal['property']['link']}")
    
    # 6. Tržišni uvidi
    print("\n📊 TRŽIŠNI UVIDI - BEOGRAD:")
    print("=" * 50)
    insights = finder.get_market_insights('Beograd')
    print(f"Ukupno aktivnih oglasa: {insights['total_properties']}")
    print(f"Prosečna cena: €{insights['avg_price']:,.0f}")
    print(f"Prosečna cena po m²: €{insights['avg_price_per_m2']:,.0f}")
    print(f"\nNajjeftinije opštine (po m²):")
    for municipality, price_per_m2 in insights['best_municipalities_to_invest']:
        print(f"  - {municipality}: €{price_per_m2:.0f}/m²")
    
    # 7. Slanje notifikacija
    if email_recipient and deals:
        print(f"\n📧 KORAK 5: Slanje notifikacija na {email_recipient}...")
        notifier = DealNotifier()
        notifier.send_deal_alert(deals, email_recipient)
        print("✓ Notifikacija poslata!")
    
    # 8. Čuvanje rezultata
    results_file = f"data/deals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_deals': len(deals),
            'discount_threshold': discount_threshold,
            'deals': deals[:20],  # Top 20
            'market_insights': insights
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Rezultati sačuvani u: {results_file}")
    
    return deals


def realistic_analysis():
    """Realistična analiza tržišta nekretnina"""
    print("🏠 REALNA ANALIZA SRPSKOG TRŽIŠTA NEKRETNINA")
    print("=" * 60)
    
    db = DatabaseManager()
    finder = RealisticDealFinder(db)
    
    # Pronađi realne ponude
    print("\n🔍 Tražim STVARNO potcenjene nekretnine (min 10% ispod tržišne cene)...")
    deals = finder.find_real_deals(min_discount=0.10)
    
    if not deals:
        print("❌ Trenutno nema pronađenih realnih ponuda.")
        print("💡 Pokrenite sa --scrape za nove podatke.")
        return
    
    print(f"\n✅ Pronađeno {len(deals)} REALNIH ponuda!\n")
    
    # Top 5 najboljih investicija
    print("🏆 TOP 5 INVESTICIONIH PRILIKA:")
    print("=" * 60)
    
    for i, deal in enumerate(deals[:5], 1):
        print(f"\n{i}. {deal['property']['title']}")
        print(f"   📍 Lokacija: {deal['property']['city']}, {deal['property']['municipality']}")
        if deal['property'].get('neighborhood'):
            print(f"      Kvart: {deal['property']['neighborhood']}")
        
        print(f"\n   💰 FINANSIJE:")
        print(f"      Traži se: €{deal['current_price']:,.0f}")
        print(f"      Realna vrednost: €{deal['market_value']:,.0f}")
        print(f"      Vaša ušteda: €{deal['discount_amount']:,.0f} ({deal['discount']*100:.0f}%)")
        print(f"      Cena po m²: €{deal['price_per_m2']:.0f}")
        
        print(f"\n   🏠 KARAKTERISTIKE:")
        print(f"      Površina: {deal['property']['area_m2']} m²")
        print(f"      Broj soba: {deal['property']['rooms']}")
        if deal['property'].get('floor') is not None:
            print(f"      Sprat: {deal['property']['floor']}/{deal['property'].get('total_floors', '?')}")
        
        print(f"\n   📊 INVESTICIONA ANALIZA:")
        print(f"      Score: {deal['investment_score']}/100")
        print(f"      Broj sličnih nekretnina: {deal['similar_properties_count']}")
        
        print(f"\n   💡 RAZLOZI NIŽE CENE:")
        for reason in deal['reasons']:
            print(f"      • {reason}")
        
        # Procena ROI za izdavanje
        estimated_rent = deal['current_price'] * 0.004  # 0.4% mesečno je realno u Srbiji
        yearly_roi = (estimated_rent * 12) / deal['current_price'] * 100
        print(f"\n   💸 PROCENA IZDAVANJA:")
        print(f"      Mesečna kirija: €{estimated_rent:.0f}")
        print(f"      Godišnji ROI: {yearly_roi:.1f}%")
        
        print(f"\n   🔗 Link: {deal['property']['link']}")
        print("\n" + "-" * 60)
    
    # Analiza po opštinama
    print("\n📊 ANALIZA PO OPŠTINAMA:")
    by_municipality = {}
    for deal in deals:
        mun = deal['property'].get('municipality', 'Nepoznato')
        if mun not in by_municipality:
            by_municipality[mun] = []
        by_municipality[mun].append(deal)
    
    for municipality, mun_deals in sorted(by_municipality.items(), 
                                         key=lambda x: len(x[1]), reverse=True)[:5]:
        avg_discount = sum(d['discount'] for d in mun_deals) / len(mun_deals)
        print(f"\n   {municipality}: {len(mun_deals)} ponuda")
        print(f"   Prosečan popust: {avg_discount*100:.0f}%")


def quick_analysis():
    """Brza analiza postojećih podataka u bazi"""
    print("🔍 Brza analiza postojećih podataka...\n")
    
    db = DatabaseManager()
    finder = DealFinder(db)
    
    # Pronađi ponude
    deals = finder.find_underpriced_properties(discount_threshold=0.10)  # 10% popust
    
    if not deals:
        print("❌ Nema pronađenih ponuda. Pokrenite sa --scrape za nove podatke.")
        return
    
    print(f"✓ Pronađeno {len(deals)} ponuda sa min 10% popusta!\n")
    
    # Grupiši po opštinama
    by_municipality = {}
    for deal in deals:
        mun = deal['property'].get('municipality', 'Nepoznato')
        if mun not in by_municipality:
            by_municipality[mun] = []
        by_municipality[mun].append(deal)
    
    # Prikaz po opštinama
    for municipality, mun_deals in sorted(by_municipality.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n📍 {municipality} ({len(mun_deals)} ponuda):")
        for deal in mun_deals[:3]:  # Top 3 po opštini
            print(f"  - {deal['property']['title'][:50]}...")
            print(f"    €{deal['current_price']:,.0f} ({deal['discount']*100:.0f}% popust)")
            print(f"    {deal['property']['area_m2']}m², Score: {deal['score']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Pronađi potcenjene nekretnine')
    parser.add_argument('--scrape', action='store_true', help='Pokreni scraping novih podataka')
    parser.add_argument('--email', type=str, help='Email za slanje notifikacija')
    parser.add_argument('--discount', type=float, default=0.15, help='Minimalni popust (0.15 = 15%)')
    parser.add_argument('--quick', action='store_true', help='Brza analiza postojećih podataka')
    parser.add_argument('--real', action='store_true', help='Realistična analiza sa detaljnim faktorima')
    
    args = parser.parse_args()
    
    if args.real:
        realistic_analysis()
    elif args.quick:
        quick_analysis()
    elif args.scrape:
        run_full_analysis(args.email, args.discount)
    else:
        # Default - realna analiza
        realistic_analysis()
        print("\n💡 Opcije:")
        print("   --real   : Realna analiza (default)")
        print("   --scrape : Prikupi nove podatke")
        print("   --quick  : Brza osnovna analiza")
        print("   --help   : Sve opcije")