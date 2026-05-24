import sys
from playwright.sync_api import sync_playwright

def main():
    print("Launching Chromium...")
    with sync_playwright() as p:
        # Launch browser in non-headless mode so the user can see it
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print("Navigating to Google Ads...")
        page.goto("https://ads.google.com")
        print("Browser is open. Waiting for user input to close...")
        input("Press Enter to close the browser...")
        browser.close()
    print("Done!")

if __name__ == "__main__":
    main()
