import sys
import os
import time
import traceback
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

def print_help():
    print("\n--- Playwright REPL Commands ---")
    print("  goto <url>             - Navigate to URL")
    print("  click <text>           - Click element containing text")
    print("  click_sel <selector>   - Click element matching CSS selector")
    print("  fill <selector> <val>  - Fill element matching selector with value")
    print("  type <value>           - Type text into active element")
    print("  press <key>            - Press a key (e.g. Enter, Tab, ArrowDown)")
    print("  eval <js_code>         - Evaluate arbitrary JS in page context")
    print("  wait <seconds>         - Wait for N seconds")
    print("  screenshot             - Save screenshot as 'inspect.png'")
    print("  url                    - Print current URL")
    print("  dump                   - Dump input fields, buttons, and text elements")
    print("  help                   - Print this help message")
    print("  exit                   - Close browser and exit")
    print("--------------------------------\n")

def main():
    profile_dir = os.path.join(HERE, "..", "chrome_profile")
    with sync_playwright() as p:
        print("Launching persistent Chrome browser...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            viewport=None,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--start-maximized"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        print("Browser launched.")
        print_help()
        
        # Navigate to Google Ads initially
        print("Navigating to https://ads.google.com ...")
        page.goto("https://ads.google.com")
        
        while True:
            try:
                cmd_line = input("REPL> ").strip()
                if not cmd_line:
                    continue
                
                parts = cmd_line.split(" ", 1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if cmd == "exit":
                    break
                elif cmd == "help":
                    print_help()
                elif cmd == "goto":
                    print(f"Navigating to {arg}...")
                    page.goto(arg)
                    print(f"URL is now: {page.url}")
                elif cmd == "click":
                    print(f"Clicking element with text: '{arg}'...")
                    # Try to locate by text
                    loc = page.get_by_text(arg).first
                    loc.click(timeout=5000, force=True)
                    print("✅ Clicked.")
                elif cmd == "click_sel":
                    print(f"Clicking selector: '{arg}'...")
                    page.click(arg, timeout=5000, force=True)
                    print("✅ Clicked.")
                elif cmd == "fill":
                    # Parse selector and value
                    subparts = arg.split(" ", 1)
                    if len(subparts) < 2:
                        print("Usage: fill <selector> <value>")
                        continue
                    sel, val = subparts[0], subparts[1]
                    print(f"Filling '{sel}' with '{val}'...")
                    page.fill(sel, val, timeout=5000)
                    print("✅ Filled.")
                elif cmd == "eval":
                    print(f"Evaluating script: '{arg}'...")
                    res = page.evaluate(arg)
                    print(f"Result: {res}")
                elif cmd == "type":
                    print(f"Typing '{arg}'...")
                    page.keyboard.type(arg)
                    print("✅ Typed.")
                elif cmd == "press":
                    print(f"Pressing key '{arg}'...")
                    page.keyboard.press(arg)
                    print("✅ Pressed.")
                elif cmd == "wait":
                    sec = float(arg) if arg else 1.0
                    print(f"Waiting {sec}s...")
                    page.wait_for_timeout(sec * 1000)
                elif cmd == "screenshot":
                    path = "inspect.png"
                    print(f"Capturing screenshot to {path}...")
                    page.screenshot(path=path)
                    print("✅ Screenshot captured.")
                elif cmd == "url":
                    print(f"Current URL: {page.url}")
                elif cmd == "dump":
                    print("--- Page Info ---")
                    print(f"URL: {page.url}")
                    print(f"Title: {page.title()}")
                    print("--- Inputs ---")
                    for idx, inp in enumerate(page.locator("input").all()[:15]):
                        try:
                            print(f"  Input {idx}: ID={inp.get_attribute('id')}, Name={inp.get_attribute('name')}, Placeholder={inp.get_attribute('placeholder')}, Label={inp.get_attribute('aria-label')}")
                        except: pass
                    print("--- Buttons ---")
                    for idx, btn in enumerate(page.locator("button").all()[:15]):
                        try:
                            print(f"  Button {idx}: Text='{btn.inner_text().strip().replace('\n', ' ')}', Class={btn.get_attribute('class')}")
                        except: pass
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")
                    
            except Exception as e:
                print("❌ Error executing command:")
                traceback.print_exc()
                
        context.close()
    print("Browser closed.")

if __name__ == "__main__":
    main()
