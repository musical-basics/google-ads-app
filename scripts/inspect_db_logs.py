"""
Check if any analytics logs are present in Supabase, grouped by event name.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
    load_dotenv(os.path.join(HERE, "..", "..", "belgium-concert-landing-page", ".env.local"))
except ImportError:
    pass

from supabase import create_client, ClientOptions

def main():
    url = os.environ.get("ANALYTICS_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("ANALYTICS_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("Error: Supabase credentials missing.")
        return
        
    print(f"Connecting to Supabase at: {url}")
    supabase_client = create_client(url, key, options=ClientOptions(schema="concert_analytics"))
    
    try:
        # Get count of logs grouped by event name
        res = supabase_client.table("analytics_logs").select("event_name").execute()
        rows = res.data or []
        
        print(f"Total rows in concert_analytics.analytics_logs: {len(rows)}")
        
        counts = {}
        for r in rows:
            name = r.get("event_name")
            counts[name] = counts.get(name, 0) + 1
            
        print("\nEvent name counts:")
        for name, count in counts.items():
            print(f"  - {name}: {count}")
            
        # Let's check the most recent 5 rows with GCLID
        res_gclid = supabase_client.table("analytics_logs").select("*").execute()
        gclid_rows = [r for r in (res_gclid.data or []) if (r.get("metadata") or {}).get("gclid")]
        
        print(f"\nTotal rows with GCLID: {len(gclid_rows)}")
        if gclid_rows:
            print("\nRecent rows with GCLID:")
            for r in gclid_rows[-5:]:
                print(f"  Created: {r.get('created_at')} | Event: {r.get('event_name')} | GCLID: {r.get('metadata', {}).get('gclid')}")
                
    except Exception as e:
        print(f"Error querying Supabase: {e}")

if __name__ == "__main__":
    main()
