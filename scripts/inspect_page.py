import sys
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    profile_dir = os.path.join(HERE, "..", "chrome_profile")
    with sync_playwright() as p:
        print("Launching browser to inspect...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            viewport=None,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        print(f"Current page URL: {page.url}")
        print("Waiting for page load...")
        page.wait_for_timeout(5000)
        
        # Let's inspect inputs and texts
        print("--- INPUT FIELDS ---")
        inputs = page.locator("input").all()
        for idx, inp in enumerate(inputs):
            try:
                placeholder = inp.get_attribute("placeholder") or ""
                label = inp.get_attribute("aria-label") or ""
                inp_id = inp.get_attribute("id") or ""
                inp_class = inp.get_attribute("class") or ""
                print(f"Input {idx}: ID={inp_id}, Label='{label}', Placeholder='{placeholder}', Class='{inp_class}'")
            except Exception as e:
                pass
                
        print("\n--- BUTTONS ---")
        buttons = page.locator("button").all()
        for idx, btn in enumerate(buttons[:30]):  # limit to 30
            try:
                text = btn.inner_text().strip().replace("\n", " ")
                btn_class = btn.get_attribute("class") or ""
                print(f"Button {idx}: Text='{text}', Class='{btn_class}'")
            except Exception as e:
                pass
                
        print("\n--- RADIO BUTTONS / CHECKBOXES ---")
        radios = page.locator("material-radio, material-checkbox, [role='radio'], [role='checkbox']").all()
        for idx, rad in enumerate(radios):
            try:
                text = rad.inner_text().strip().replace("\n", " ")
                role = rad.get_attribute("role") or rad.tag_name
                print(f"Option {idx}: Role={role}, Text='{text}'")
            except Exception as e:
                pass

        print("\nScreenshot captured as 'inspect.png'")
        page.screenshot(path="inspect.png")
        
        input("Press Enter to close browser...")
        context.close()

if __name__ == "__main__":
    main()
