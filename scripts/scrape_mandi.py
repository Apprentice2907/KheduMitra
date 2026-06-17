import os
import sys
import asyncio
from datetime import datetime
import psycopg2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.agmarknet_service import agmarknet_service

def get_db_connection():
    postgres_url = os.environ.get("POSTGRES_URL")
    if not postgres_url:
        print("POSTGRES_URL not set!")
        sys.exit(1)
    return psycopg2.connect(postgres_url)

async def scrape_and_ingest():
    print("Starting Nightly Mandi Scraper...")
    
    # In a real scenario, we would loop over a master list of states/commodities
    # For this demo, we'll fetch a few key commodities for Gujarat
    targets = [
        {"state": "Gujarat", "district": "Jamnagar", "commodity": "Cotton"},
        {"state": "Gujarat", "district": "Rajkot", "commodity": "Wheat"},
        {"state": "Gujarat", "district": "Amreli", "commodity": "Groundnut"}
    ]
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    success_count = 0
    today = datetime.now().date()
    
    for target in targets:
        print(f"Fetching {target['commodity']} in {target['district']}, {target['state']}...")
        try:
            data = await agmarknet_service.get_mandi_price(
                target['state'], target['district'], target['commodity']
            )
            
            if data:
                # Upsert into PostgreSQL
                query = """
                    INSERT INTO mandi_prices (state, district, commodity, min_price, max_price, modal_price, arrival_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (state, district, commodity, arrival_date) 
                    DO UPDATE SET 
                        min_price = EXCLUDED.min_price,
                        max_price = EXCLUDED.max_price,
                        modal_price = EXCLUDED.modal_price;
                """
                cur.execute(query, (
                    data['state'],
                    data['district'],
                    data['commodity'],
                    data['min_price'],
                    data['max_price'],
                    data['modal_price'],
                    today
                ))
                conn.commit()
                success_count += 1
                print(f"✅ Upserted: {data['commodity']} @ {data['modal_price']}")
            else:
                print(f"⚠️ No data found for {target['commodity']} in {target['district']}")
                
        except Exception as e:
            print(f"❌ Error fetching {target['commodity']}: {str(e)}")
            conn.rollback()
            
    cur.close()
    conn.close()
    print(f"Scraping complete. Successfully upserted {success_count} records.")

if __name__ == "__main__":
    asyncio.run(scrape_and_ingest())
