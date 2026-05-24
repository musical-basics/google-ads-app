import sys
import os
import time
import urllib.parse as urlparse
from playwright.sync_api import sync_playwright

# Setup imports
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

CAMPAIGN_A = {
    "name": "belgium_original_yt",
    "budget": "9.00",
    "utm_campaign": "belgium_original_yt",
    "videos": [
        "73-DQLkHgmw",  # V4 AD15s horizontal
        "Q0UWYfaM-Zw",  # V5 portrait fixed audio
        "4knXOmkKUrg"   # V4 AD15s portrait
    ],
    "ad_groups": [
        {
            "name": "subscribers_and_viewers",
            "utm_content": "subscribers",
            "audience": "MB Belgium Concert (YouTube subscribers)"
        },
        {
            "name": "video_viewers_only",
            "utm_content": "video_viewers",
            "audience": "MB Belgium Concert (video viewers only)"
        }
    ]
}

CAMPAIGN_B = {
    "name": "belgium_new_creative_yt",
    "budget": "9.00",
    "utm_campaign": "belgium_new_creative_yt",
    "videos": [
        "1oR8bPstNtk",  # new horizontal
        "_ecW9Khci7o",  # new long portrait
        "eSvZxFWvPno"   # new short portrait
    ],
    "ad_groups": [
        {
            "name": "subscribers_and_viewers",
            "utm_content": "subscribers",
            "audience": "MB Belgium Concert (YouTube subscribers)"
        },
        {
            "name": "video_viewers_only",
            "utm_content": "video_viewers",
            "audience": "MB Belgium Concert (video viewers only)"
        }
    ]
}

# Assets configuration
FINAL_URL = "https://belgium.musicalbasics.com"
BUSINESS_NAME = "MusicalBasics"
CALL_TO_ACTION = "Book now"

HEADLINES = [
    "Belgium Piano Concert",
    "Live in Zaventem June 11",
    "Musical Basics Live",
    "Solo Piano, June 11 2026",
    "Reserve Your Seat Today"
]

LONG_HEADLINES = [
    "Lionel Yu plays solo piano live in Zaventem, Belgium. June 11, 2026."
]

DESCRIPTIONS = [
    "Reserve your seat for a one-night solo piano concert near Brussels.",
    "100 seats, June 11 only. Standard €29, VIP €59.",
    "From the Musical Basics channel. An evening of classical piano."
]

def wait_for_user(prompt_msg):
    print("\n" + "="*60)
    print(prompt_msg)
    print("="*60)
    return input("Press [Enter] when ready to continue (or type 'skip' to skip this step): ").strip().lower()

def try_fill(page, selector, value, desc):
    try:
        print(f"Trying to fill {desc}...")
        page.wait_for_selector(selector, timeout=5000)
        page.fill(selector, value)
        print(f"✅ Filled {desc} with '{value}'")
        return True
    except Exception as e:
        print(f"❌ Could not auto-fill {desc}: {e}")
        print(f"👉 Please fill manually: '{value}'")
        return False

def try_click(page, selector, desc):
    try:
        print(f"Trying to click {desc}...")
        page.wait_for_selector(selector, timeout=5000)
        page.click(selector)
        print(f"✅ Clicked {desc}")
        return True
    except Exception as e:
        print(f"❌ Could not click {desc}: {e}")
        return False

def print_ad_copy_guide(campaign_name, utm_content, videos):
    print("\n--- AD COPY & ASSET REFERENCE ---")
    print(f"Campaign: {campaign_name}")
    print(f"Ad Group UTM Content: {utm_content}")
    print(f"Final URL Suffix: utm_source=google&utm_medium=video&utm_campaign={campaign_name}&utm_content={utm_content}")
    print(f"Final URL: {FINAL_URL}?utm_source=google&utm_medium=video&utm_campaign={campaign_name}&utm_content={utm_content}")
    print("Videos to add:")
    for v in videos:
        print(f"  - https://www.youtube.com/watch?v={v}")
    print(f"Business Name: {BUSINESS_NAME}")
    print(f"Call To Action: {CALL_TO_ACTION}")
    print("Headlines (up to 5):")
    for h in HEADLINES:
        print(f"  - {h}")
    print("Long Headline:")
    print(f"  - {LONG_HEADLINES[0]}")
    print("Descriptions:")
    for d in DESCRIPTIONS:
        print(f"  - {d}")
    print("---------------------------------\n")

def run_campaign_wizard(page, campaign):
    print(f"\n🚀 Starting Wizard for Campaign: {campaign['name']} 🚀")
    
    # 1. Detect ocid
    current_url = page.url
    ocid = None
    parsed = urlparse.urlparse(current_url)
    params = urlparse.parse_qs(parsed.query)
    if 'ocid' in params:
        ocid = params['ocid'][0]
    
    new_campaign_url = "https://ads.google.com/aw/campaigns/new"
    if ocid:
        new_campaign_url += f"?ocid={ocid}"
        
    print(f"Navigating to campaign creation: {new_campaign_url}")
    page.goto(new_campaign_url)
    
    print("\nStep 1: Selecting Campaign Objective and Type")
    print("Please select:")
    print("  1. 'Create a campaign without a goal's guidance' (bottom right option)")
    print("  2. 'Video' as the campaign type")
    print("  3. Subtype: 'Video views' (default)")
    print("  4. Click 'Continue'")
    
    ans = wait_for_user("Verify you are on the main campaign settings page (with Campaign Name, Budget, etc.)")
    if ans == 'skip':
        return
        
    # Let's try to fill the campaign name
    # Google Ads campaign name input field has aria-label="Campaign name" or similar selector
    # Let's try a few selectors
    name_selectors = [
        "input[aria-label='Campaign name']",
        "input[placeholder='Campaign name']",
        "input[name='campaignName']",
        "input.input-area"
    ]
    name_filled = False
    for sel in name_selectors:
        if try_fill(page, sel, campaign['name'], "Campaign Name"):
            name_filled = True
            break
            
    # Try to set Budget
    budget_value = campaign['budget']
    print(f"Campaign Daily Budget target: ${budget_value}")
    print("Please configure:")
    print(f"  - Campaign Name: {campaign['name']}")
    print(f"  - Budget type: Daily")
    print(f"  - Daily amount: ${budget_value}")
    print("  - Bid Strategy: Maximum CPV (default for Video views)")
    
    print("\nTargeting locations to configure:")
    print("  - Belgium (country)")
    print("  - Luxembourg (country)")
    print("  - Hauts-de-France (region of France)")
    print("Languages to select:")
    print("  - English, Dutch, French")
    
    ans = wait_for_user("Set locations, languages, and click 'Next' to go to Ad Group settings")
    if ans == 'skip':
        return
        
    # Ad Group 1
    print("\n--- Ad Group 1 Setup ---")
    ag1 = campaign['ad_groups'][0]
    print(f"Please name the Ad Group: {ag1['name']}")
    print(f"Under 'Audience', search and select: {ag1['audience']}")
    print(f"Expand 'Ad group URL options' and paste the Final URL Suffix:")
    print(f"  utm_source=google&utm_medium=video&utm_campaign={campaign['utm_campaign']}&utm_content={ag1['utm_content']}")
    
    print_ad_copy_guide(campaign['name'], ag1['utm_content'], campaign['videos'])
    
    ans = wait_for_user("Create the ads for Ad Group 1 and click 'Next' or create Ad Group 2")
    if ans == 'skip':
        return

    # Ad Group 2
    print("\n--- Ad Group 2 Setup ---")
    ag2 = campaign['ad_groups'][1]
    print(f"Please add a second Ad Group named: {ag2['name']}")
    print(f"Under 'Audience', search and select: {ag2['audience']}")
    print(f"Expand 'Ad group URL options' and paste the Final URL Suffix:")
    print(f"  utm_source=google&utm_medium=video&utm_campaign={campaign['utm_campaign']}&utm_content={ag2['utm_content']}")
    
    print_ad_copy_guide(campaign['name'], ag2['utm_content'], campaign['videos'])
    
    ans = wait_for_user("Configure ads for Ad Group 2, review the campaign, and publish it")
    print(f"✅ Wizard for {campaign['name']} complete!")

def main():
    profile_dir = os.path.join(HERE, "..", "chrome_profile")
    print(f"Using Chrome profile directory: {profile_dir}")
    
    with sync_playwright() as p:
        print("Launching persistent Chrome browser...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            viewport=None,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized"
            ]
        )
        
        # Get the first page
        page = context.pages[0] if context.pages else context.new_page()
        
        print("\nOpening Google Ads...")
        page.goto("https://ads.google.com")
        
        print("\n" + "#"*70)
        print("ACTION REQUIRED:")
        print("1. In the opened browser window, log in to your Google Ads account.")
        print("2. Switch to account: 315-282-9803 ('Lionel Yu Concerts').")
        print("3. Verify you can see the Google Ads campaign dashboard.")
        print("#"*70 + "\n")
        
        input("Press [Enter] here in the terminal once you are logged in and ready...")
        
        while True:
            print("\nCampaign Creation Menu:")
            print(f"1. Create Campaign A: {CAMPAIGN_A['name']} (Original Creative)")
            print(f"2. Create Campaign B: {CAMPAIGN_B['name']} (New Creative)")
            print("3. Exit")
            choice = input("Enter choice (1, 2, or 3): ").strip()
            
            if choice == "1":
                run_campaign_wizard(page, CAMPAIGN_A)
            elif choice == "2":
                run_campaign_wizard(page, CAMPAIGN_B)
            elif choice == "3":
                break
            else:
                print("Invalid choice.")
                
        print("Closing browser...")
        context.close()
    print("Done!")

if __name__ == "__main__":
    main()
