import os
import psycopg2
from app.core.config import settings

def run_eval_analysis():
    print("Connecting to Supabase to fetch A/B eval logs...")
    try:
        conn = psycopg2.connect(settings.SUPABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM eval_log")
        total = cur.fetchone()[0]
        
        if total == 0:
            print("No evaluation logs found.")
            return
            
        cur.execute("SELECT AVG(length_diff), AVG(overlap_score) FROM eval_log")
        avg_len_diff, avg_overlap = cur.fetchone()
        
        print(f"--- A/B Evaluation Summary ---")
        print(f"Total Evaluated Requests: {total}")
        print(f"Average Length Difference: {avg_len_diff:.2f} characters")
        print(f"Average Jaccard Overlap Score: {avg_overlap:.2f}")
        
    except Exception as e:
        print(f"Error fetching eval logs: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    run_eval_analysis()
