# Google Ads Browser Automation Gotchas

Documented during the manual UI automation setup of the Belgium Concert campaign (May 2026).
These are hard-won lessons from using Playwright and Javascript to interact with the complex, dynamic, and custom-styled Google Ads UI interface.

---

## 1. Scrollable Containers (Steppers vs Standalone)

**Problem:** Google Ads UI runs inside nested scrollable containers. Traditional window-level scrolling (`window.scrollTo` or `window.scrollBy`) does not scroll the actual panels, making elements appear hidden/unclickable.

**Gotcha:** The scrollable containers differ depending on the wizard context:
- **Campaign Creation Wizard:** The main container is `div.stepper-content`.
- **Standalone Ad Group/Ad Wizard:** The main container is `div.scrollable-content`.

**Fix:** Query for scrollable elements programmatically and scroll the correct container:
```javascript
// Programmatic container scroll helper
const container = document.querySelector('.stepper-content') || document.querySelector('.scrollable-content');
if (container) {
  container.scrollTop = 1200; // scroll to position
}
```

---

## 2. Dynamic Component IDs

**Problem:** Input fields (like text boxes) use dynamic, randomly-generated IDs on every page load (e.g. `a718EE814-8546-4EE6-952C-20E8F5FD8E45--0`). Hardcoding IDs will consistently fail.

**Fix:** Target inputs using label associations or surrounding parent elements. Use `aria-labelledby` or locate the label element first and find the associated input:
```javascript
const fillInput = (labelText, value) => {
  const inp = Array.from(document.querySelectorAll('input')).find(el => {
    const refId = el.getAttribute('aria-labelledby');
    const labelEl = refId ? document.getElementById(refId) : null;
    const actualLabel = labelEl ? labelEl.innerText.trim() : '';
    const ariaLabel = el.getAttribute('aria-label') || '';
    return actualLabel.includes(labelText) || ariaLabel.includes(labelText);
  });
  if (inp) {
    inp.focus();
    inp.value = value;
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    inp.dispatchEvent(new Event('change', { bubbles: true }));
  }
};
```

---

## 3. Location and Language Autocomplete targeting

**Problem:** Simply typing text (e.g. "Belgium") in location or language search inputs does not select them. You must wait for the suggestion dropdown to appear and click the specific row or matching button.

**Gotchas:**
- **Locations:** The target button is usually a nested `<material-button>` containing the text "Include" (class `material-button.add`).
- **Languages:** Selecting an autocomplete option automatically adds it to the list and clears the input box.

**Fix:** Type the query character-by-character to trigger the autocomplete suggestion list, wait 2 seconds, and then click the option/Include button:
```javascript
// Type text and select include button
input.focus();
input.value = "Belgium";
input.dispatchEvent(new Event('input', { bubbles: true }));
// Wait for suggestions
await new Promise(r => setTimeout(r, 2000));
const includeBtn = document.querySelector('material-button.add');
if (includeBtn) {
  includeBtn.click();
}
```

---

## 4. YouTube Video Asset Selection

**Problem:** In "Video views" responsive/multi-format ads, you can add up to 5 videos. Pasting the YouTube URL into the video search box triggers a suggestion dropdown which must be clicked.

**Gotcha:** Clicking the suggestion adds the video to the selected list and clears the input box, resetting it for the next URL entry.

**Fix:** Paste each URL sequentially, wait for the suggestion popup, and click the suggestion item (often has class `.suggestion-item` or matches option roles):
```javascript
const items = Array.from(document.querySelectorAll('.suggestion-item, [class*="suggestion"], [role="option"]'))
  .filter(el => el.offsetParent !== null && el.innerText.trim() !== '');
if (items.length > 0) {
  items[0].click(); // Selects and adds the video
}
```

---

## 5. Parent-Child Text Match in Nested Zippies

**Problem:** In advanced panels (like `Ad URL options` which contains `Tracking Template` and `Final URL suffix`), locating inputs by looking up parent containers containing the text can mistakenly match the first input in the container (e.g., `Tracking Template`) because at a high ancestor level, the container contains both texts.

**Fix:** Inspect inputs inside the zippy and check if their immediate `material-input` parent text contains the exact label, or select them by index or exact label-to-input association:
```javascript
const zippy = document.querySelector('zippy');
const inputs = Array.from(zippy.querySelectorAll('input'));
// inputs[0] -> Tracking Template
// inputs[1] -> Final URL suffix
```

---

## 6. Sensitive Action Authentication Prompts

**Problem:** Performing actions like saving an ad group or publishing a campaign sometimes triggers Google's "Confirm it's you" account verification modal.

**Gotcha:** Since Playwright browser control is launched locally on the user's machine (using `headless=False`), the user can see this popup on their screen. However, auth popups can be blocked by standard popup settings or require 2FA/password input.

**Fix:** Alert the user to complete the authentication prompt manually in the open browser window on their screen, and then tell the agent when it is done to resume automation.

---

## 7. Use a Persistent REPL Instead of One-Shot Scripts

**Problem:** Playwright scripts launched as one-shot processes lose browser context between calls. Each re-launch re-opens a new browser window and loses the logged-in session.

**Fix:** Run Playwright in **REPL mode** — a persistent interactive process that keeps the browser open. The agent sends commands via `manage_task(send_input=...)` to the running REPL and reads stdout for results.

```python
# repl.py — minimal persistent Playwright REPL
import asyncio, sys
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("READY", flush=True)
        for line in sys.stdin:
            line = line.strip()
            if line == "screenshot":
                await page.screenshot(path="inspect.png")
                print("screenshot saved", flush=True)
            elif line == "dump":
                print(await page.content(), flush=True)
            elif line.startswith("eval "):
                expr = line[5:]
                result = await page.evaluate(expr)
                print(result, flush=True)
            elif line.startswith("navigate "):
                url = line[9:]
                await page.goto(url)
                print("navigated", flush=True)
asyncio.run(main())
```

**Key advantage:** The browser stays logged into Google Ads for the entire session. The agent can keep running `eval` commands to inspect and interact with the live page without ever re-authenticating.

---

## 8. Headful Browser — Login Must Be Done by the User

**Problem:** Google Ads blocks headless Playwright (or any automation that looks non-human) with a "This browser or app may not be secure" warning on the Google login page.

**Gotcha:** Even if login succeeds, Google's security systems detect the automation fingerprint and may force repeated 2FA prompts or account lockouts.

**Fix:**
1. Launch the REPL with `headless=False` so a real visible Chrome window opens.
2. Navigate to `https://ads.google.com` in the REPL.
3. **Stop and let the user log in manually** in that browser window.
4. Once the user confirms they're logged in, resume automation via eval commands.

The browser's cookies persist for the entire REPL session after manual login — no re-login needed for subsequent pages within the same domain.

---

## 9. Angular Material Inputs Require Both `input` + `change` Events

**Problem:** Setting `input.value = "some text"` and dispatching only `input` or `change` does not always register the value in Angular forms. The field looks filled visually but the Angular model doesn't update, so validation fails or the value is lost on next navigation.

**Fix:** Always dispatch both events after setting `.value`, and also trigger a `blur` event to force Angular's change detection cycle:

```javascript
inp.focus();
inp.value = newValue;
inp.dispatchEvent(new Event('input', { bubbles: true }));
inp.dispatchEvent(new Event('change', { bubbles: true }));
inp.blur();
```

For dropdowns or select components built on `<material-select>`, you often need to click the element, wait for the dropdown to render, then click the desired option item by text match.

---

## 10. Standalone Ad Creation Has a Different URL and DOM Structure

**Problem:** The Google Ads "new campaign" wizard and the standalone "add ad" / "add ad group" flows use completely different page layouts, scrollable containers, and form structures — even though they look visually similar.

**Gotcha:**
- In the **campaign wizard**, the URL contains `/campaigns/create` and the container is `div.stepper-content`.
- In the **standalone ad creation** (e.g., navigating to an existing ad group and adding a new ad), the URL pattern is `/adgroups/{id}/ads/new` and the container is `div.scrollable-content`.
- The field order, presence of accordions, and button labels can differ between the two flows.

**Fix:** After creating a campaign, navigate directly to the campaign's ad group and use the standalone flow. Don't try to automate across a wizard step boundary — complete each step inside its own page context.

---

## 11. Audience Selection Panel — Collapsed by Default

**Problem:** The "Audience" panel in the ad group editor is a collapsed `<zippy>` or `<material-expansion-panel>` by default. Trying to interact with audience inputs before expanding the panel finds no visible elements.

**Gotcha:** `offsetParent !== null` is a good visibility proxy for most elements, but expansion panels internally have `display: none` on their content when collapsed, meaning all inner inputs will have `offsetParent === null`.

**Fix:** Find the panel header and click it to expand before targeting any inner fields:

```javascript
const audiencePanel = Array.from(document.querySelectorAll('material-expansion-panel, zippy'))
  .find(el => el.innerText.includes('Audience') && el.offsetParent !== null);
if (audiencePanel) {
  const header = audiencePanel.querySelector('.panel-header, .zippy-header, [role="button"]');
  if (header) header.click();
  await new Promise(r => setTimeout(r, 800)); // wait for animation
}
```

---

## 12. `Ad URL options` Zippy — Must Be Explicitly Opened

**Problem:** The "Ad URL options" section (containing Final URL suffix and Tracking Template at the ad level) is inside a collapsed `<zippy>` that looks like a link/button. It is NOT open by default.

**Gotcha:** The zippy trigger is a `<div>` or `<a>` with text "Ad URL options (optional)" — not a standard `<button>`. Standard `.click()` on the zippy content container doesn't toggle it; you must click the header anchor.

**Fix:**
```javascript
const adUrlOptions = Array.from(document.querySelectorAll('div, span, a, [role="button"]'))
  .find(el => el.innerText && el.innerText.trim().includes('Ad URL options') 
    && el.offsetParent !== null && el.innerText.length < 50);
if (adUrlOptions) adUrlOptions.click();
await new Promise(r => setTimeout(r, 600));
// Now the Final URL suffix and Tracking Template inputs are visible
```

---

## 13. Screenshot-Based Debugging Is the Ground Truth

**Problem:** `dump` (printing page HTML) gives the full DOM but it's thousands of lines — hard to interpret in a chat-style flow. Eval expressions returning complex objects can also be truncated.

**Best practice:** At every major decision point (before filling a form section, after clicking a button, before saving), call `screenshot` and view the resulting `inspect.png`. This instantly tells you:
- Whether you're on the right page/step
- Whether a modal or auth prompt appeared
- Whether the form filled correctly
- Whether an error toast appeared after a save

Screenshots are much cheaper to interpret than DOM dumps and surface unexpected states (modals, network errors, unsaved warnings) that DOM queries alone would miss.

---

## 14. Google Ads Uses Shadow DOM for Some Custom Elements

**Problem:** Some Google Ads components (particularly `<material-button>`, `<material-input>`, `<material-checkbox>`) render their actual interactive elements inside a Shadow DOM. Standard `document.querySelectorAll` does NOT traverse Shadow DOM.

**Gotcha:** You might find the outer custom element but clicking it does nothing because the real `<button>` or `<input>` is inside `element.shadowRoot`.

**Fix:** Use the outer element's `.click()` method (which the custom element forwards to its shadow content) OR use Playwright's `page.click(selector)` which automatically pierces shadow roots. In eval scripts:

```javascript
// Works for material-button — the element handles the click internally
const btn = document.querySelector('material-button.save-button');
if (btn) btn.click(); // dispatches through shadow DOM
```

For reading values from shadow DOM inputs, access `element.shadowRoot.querySelector('input').value`.

---

## 15. The Right Order for the Automation Stack

Lesson from iterating through multiple broken approaches:

| Layer | Tool | Use for |
|---|---|---|
| Browser control | Playwright (headful, REPL) | Keeping session alive, navigation |
| DOM inspection | `eval` via REPL stdin | Finding elements, checking state |
| Form filling | `eval` + `.value` + events | Inputs, checkboxes, dropdowns |
| Click handling | `eval` + `.click()` | Buttons, links, accordion headers |
| Verification | `screenshot` → view file | Visual ground truth before saves |
| Auth | Manual user action | Google login, 2FA, verification prompts |

**Do NOT:**
- Use Playwright's `page.fill()` or `page.type()` via the REPL — the REPL `eval` mode is simpler and more reliable for complex Angular forms.
- Run one-shot scripts for multi-step flows — context is lost between invocations.
- Rely on `document.getElementById(dynamicId)` — IDs regenerate on every page load.

---

## 16. `eval` in REPL Must Return Serializable Values

**Problem:** When using `page.evaluate()` (or the REPL eval equivalent), returning DOM nodes, circular references, or non-serializable objects causes a serialization error and returns `undefined` or throws.

**Fix:** Always map DOM queries to plain objects or primitives before returning:

```javascript
// BAD — returns DOM nodes which can't be serialized
return document.querySelectorAll('input');

// GOOD — maps to serializable plain objects
return Array.from(document.querySelectorAll('input')).map(el => ({
  label: el.getAttribute('aria-label') || '',
  value: el.value,
  visible: el.offsetParent !== null
}));
```

---

## 17. Demand Gen Ad Group: "Video views" vs "Conversions" Sub-type Matters

**Problem:** When creating a new ad in a Demand Gen ad group, you are prompted to choose the ad sub-type. Choosing the wrong sub-type gives you a different form with different available fields (e.g., no multi-video input).

**Key distinction:**
- **"Video views" sub-type** → Multi-video format, up to 5 URLs, portrait + landscape variants supported
- **"Conversions" or "Awareness" sub-type** → Single video or image carousel format

**Fix:** In the ad creation flow, always select "Video views" for the Belgium concert campaign. After selecting, verify the form shows the multi-URL video input (labelled "Search for a video or paste the URL from YouTube").
