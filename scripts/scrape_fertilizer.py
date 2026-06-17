import os
import sys
import psycopg2
from datetime import datetime

def get_db_connection():
    postgres_url = os.environ.get("POSTGRES_URL")
    if not postgres_url:
        print("POSTGRES_URL not set!")
        sys.exit(1)
    return psycopg2.connect(postgres_url)

def scrape_fertilizers():
    print("Starting Nightly Fertilizer Scraper...")
    
    # In a real app, we would use requests + BeautifulSoup to parse the Dept of Fertilizers website.
    # For Phase 4 demo, we simulate the scraped data.
    fertilizers = [
        {"type": "DAP", "price": 1350.00, "url": "https://fert.nic.in"},
        {"type": "Urea", "price": 266.50, "url": "https://fert.nic.in"},
        {"type": "MOP", "price": 1700.00, "url": "https://fert.nic.in"}
    ]
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    success_count = 0
    today = datetime.now().date()
    
    for fert in fertilizers:
        try:
            query = """
                INSERT INTO fertilizer_prices (fertilizer_type, price_per_bag, source_url, recorded_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (fertilizer_type, recorded_at) 
                DO UPDATE SET 
                    price_per_bag = EXCLUDED.price_per_bag;
            """
            cur.execute(query, (
                fert['type'],
                fert['price'],
                fert['url'],
                today
            ))
            conn.commit()
            success_count += 1
            print(f"✅ Upserted: {fert['type']} @ ₹{fert['price']}/bag")
            
        except Exception as e:
            print(f"❌ Error inserting {fert['type']}: {str(e)}")
            conn.rollback()
            
    cur.close()
    conn.close()
    print(f"Scraping complete. Successfully upserted {success_count} records.")

if __name__ == "__main__":
    scrape_fertilizers()
