# Campaign Comparison: Belgium May 13 vs. Belgium May 2026

This document records the structural and targeting differences identified between the original, low-performing campaign setup (`Belgium Campaign May 13`) and the higher-performing campaign setup (`Belgium Concert - New Creative (May 2026)`).

---

## 1. Summary of Findings

| Feature | Belgium Campaign May 13 (Low Quality) | Belgium Concert - New Creative (May 2026) (High Quality) |
| :--- | :--- | :--- |
| **Campaign ID** | `23837741178` | `23871037379` |
| **Bidding Strategy** | `TARGET_SPEND` (Maximize Clicks) | `MAXIMIZE_CONVERSIONS` |
| **Google Search Network** | Enabled (`True`) | Enabled (`True`) |
| **Search Partners Network** | Enabled (`True`) | Enabled (`True`) |
| **Display Content Network** | Enabled (`True`) | Disabled (`False`) |
| **Location Target Scope** | Campaign-level only | Campaign-level + Explicit Ad Group targets |

---

## 2. Key Differences and Impact

### A. Bidding Strategy (Clicks vs. Conversions)
*   **May 13 Campaign (`TARGET_SPEND`)**: Optimized to get the maximum number of clicks for the lowest possible cost. This forced Google's algorithm to target bottom-of-the-barrel ad inventory (junk placements) because those clicks are cheap, regardless of whether those users had any interest in buying concert tickets.
*   **May 2026 Campaign (`MAXIMIZE_CONVERSIONS`)**: Optimized to target users who are most likely to convert (join the waitlist or view tickets). This forces the algorithm to ignore cheap accidental clicks and focus on high-intent users.

### B. Network Placements (Display Network Leakage)
*   **May 13 Campaign (`Display Network = True`)**: Allowed ads to serve outside Google on third-party mobile apps (games, utilities) and partner sites. This led to massive accidental clicks and low-intent traffic, resulting in the user reporting traffic that "wasn't even coming from YouTube."
*   **May 2026 Campaign (`Display Network = False`)**: Restricted ads strictly to Google's premium owned-and-operated inventory: **YouTube (Watch pages, Shorts, Home Feed)**, **Gmail**, and **Google Discover**.

### C. Geotargeting Strictness
*   **May 2026 Campaign**: Includes explicit `LOCATION (TARGETED)` criterion added directly to the ad groups targeting Belgium (`2056`), ensuring that the ad groups enforce geographic limits on top of campaign-level targeting.

---

## 3. Best Practices for Future Setups

1.  **Always use Maximize Conversions** instead of Maximize Clicks (`TARGET_SPEND`) for concert ticket or email list campaigns.
2.  **Turn off Content Network (Display Ads)** for Demand Gen campaigns unless specifically running cheap retargeting banners.
3.  Keep placements restricted to **YouTube, Gmail, and Discover** for warm audience retargeting.
