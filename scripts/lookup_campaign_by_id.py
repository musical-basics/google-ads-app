"""Resolve a Google Ads campaign by id."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

cid = sys.argv[1] if len(sys.argv) > 1 else "23871037379"
client = get_client()
svc = client.get_service("GoogleAdsService")
rows = svc.search(
    customer_id=customer_id(),
    query=f"SELECT campaign.id, campaign.name, campaign.status FROM campaign WHERE campaign.id = {cid}",
)
for r in rows:
    print(r.campaign.id, "|", r.campaign.name, "|", r.campaign.status.name)
