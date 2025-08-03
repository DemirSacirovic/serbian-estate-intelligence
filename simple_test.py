#!/usr/bin/env python3
"""
Jednostavan test bez dodatnih biblioteka
"""
import json

print("🏠 SERBIAN ESTATE INTELLIGENCE - JEDNOSTAVAN TEST")
print("=" * 60)

# Učitaj test rezultate
with open('test_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

properties = data['search_results']
print(f"\n✅ Učitano {len(properties)} nekretnina iz test_results.json")

# Analiziraj cene
print("\n📊 ANALIZA CENA:")
print("-" * 40)

prices = []
for prop in properties:
    # Izvuci cenu
    price_str = prop.get('price', '')
    if '€' in price_str:
        # Ukloni € i tačke, pretvori u broj
        price_num = float(price_str.replace('€', '').replace('.', '').strip())
        prices.append(price_num)
        
        # Izvuci površinu
        area = None
        for feature in prop.get('features', []):
            if 'm2' in feature:
                area = float(feature.replace('m2Kvadratura', '').strip())
                break
        
        if area:
            price_per_m2 = price_num / area
            print(f"\n{prop['title'][:50]}...")
            print(f"  💰 Cena: €{price_num:,.0f}")
            print(f"  📏 Površina: {area} m²")
            print(f"  💵 Cena po m²: €{price_per_m2:,.0f}")

# Prosečna cena
if prices:
    avg_price = sum(prices) / len(prices)
    print(f"\n📈 STATISTIKE:")
    print(f"  Prosečna cena: €{avg_price:,.0f}")
    print(f"  Najjeftinija: €{min(prices):,.0f}")
    print(f"  Najskuplja: €{max(prices):,.0f}")

# Pronađi potencijalne ponude
print("\n🎯 POTENCIJALNE DOBRE PONUDE:")
print("(stanovi ispod €2,500/m²)")
print("-" * 40)

good_deals = []
for prop in properties:
    price_str = prop.get('price', '')
    if '€' in price_str:
        price_num = float(price_str.replace('€', '').replace('.', '').strip())
        
        # Površina
        area = None
        for feature in prop.get('features', []):
            if 'm2' in feature:
                area = float(feature.replace('m2Kvadratura', '').strip())
                break
        
        if area:
            price_per_m2 = price_num / area
            if price_per_m2 < 2500:  # Ispod €2,500/m²
                good_deals.append({
                    'title': prop['title'],
                    'price': price_num,
                    'area': area,
                    'price_per_m2': price_per_m2,
                    'link': prop['link']
                })

# Sortiraj po ceni po m²
good_deals.sort(key=lambda x: x['price_per_m2'])

for i, deal in enumerate(good_deals[:5], 1):
    print(f"\n{i}. {deal['title'][:50]}...")
    print(f"   💰 €{deal['price']:,.0f} ({deal['area']}m²)")
    print(f"   💵 €{deal['price_per_m2']:,.0f}/m²")
    print(f"   🔗 {deal['link'][:50]}...")

print("\n✅ Test završen!")
print("\n💡 Sledeći korak: Instaliraj pip i SQLAlchemy za punu funkcionalnost:")
print("   sudo apt-get install python3-pip")
print("   pip3 install -r requirements.txt")