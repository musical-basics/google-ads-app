# Bug Fix: Google Ads API `USER_PERMISSION_DENIED` on First Connect

**Date:** 2026-05-22  
**Affects:** `GOOGLE_ADS_LOGIN_CUSTOMER_ID` in `.env.local` and Vercel env  

---

## Symptom

Every API call to Google Ads returned:

```
authorization_error: USER_PERMISSION_DENIED
User doesn't have permission to access customer.
Note: If you're accessing a client customer, the manager's customer id must
be set in the 'login-customer-id' header.
```

This happened even though `list_accessible_customers()` confirmed the
refresh token could see **both** accounts:
- `customers/3152829803` (Lionel Yu Concerts — the advertiser)
- `customers/6692309699` (MusicalBasics — the MCC/Manager)

---

## Root Cause

`GOOGLE_ADS_LOGIN_CUSTOMER_ID` was set to the **MCC account** (`6692309699`),
following the Google Ads API docs' instruction to "use your manager account ID
as the login customer ID when accessing sub-accounts."

However, that routing only works when:
1. The OAuth-authenticated user is an **admin of the MCC**, AND
2. The target customer (`GOOGLE_ADS_CUSTOMER_ID`) is a **sub-account under that MCC**.

In our case, the refresh token was minted with a Google account that has
**direct access** to `3152829803` (Lionel Yu Concerts) as a standalone user,
**not** as a manager-delegated admin of the MCC. The MCC path therefore fails
with `PERMISSION_DENIED` even though the direct path succeeds.

---

## Failed Attempts

1. **Re-minting refresh token with `lionel@musicalbasics.com`** — same error.
   Account has direct access to the advertiser but not MCC-delegated access.
2. **Re-minting with `musicalbasics@gmail.com`** — same error for same reason.
3. **Removing `login_customer_id` entirely** — also fails because Google
   requires it when the customer is a sub-account in any MCC hierarchy.

---

## Fix

Set `GOOGLE_ADS_LOGIN_CUSTOMER_ID` to the **advertiser account itself**
(`3152829803`) instead of the MCC:

```env
# WRONG — causes USER_PERMISSION_DENIED when token doesn't have MCC admin access
GOOGLE_ADS_LOGIN_CUSTOMER_ID=6692309699

# CORRECT — login as the advertiser account directly
GOOGLE_ADS_LOGIN_CUSTOMER_ID=3152829803
GOOGLE_ADS_CUSTOMER_ID=3152829803
```

When `login_customer_id == customer_id`, the API authenticates the call
as the advertiser itself rather than routing through the MCC. This works
as long as the OAuth user has direct access to that advertiser account.

Confirmed working via `scripts/test_connection.py` — returned:

```
✅ Google Ads API connection is LIVE. Ready to proceed!
── Campaigns found: 1
  [ENABLED] Belgium Campaign May 13 (id=23837741178)
```

---

## Notes for Future Campaigns

- If you ever need MCC-level access (e.g. listing all sub-accounts from the
  manager), you'll need a refresh token minted by an account that is an **admin
  of the MCC** (`669-230-9699`), not just a user of the sub-account.
- The `list_accessible_customers()` call succeeds regardless — it just lists
  what the token can touch. It does NOT mean the login_customer_id routing works.
- To debug: always call `list_accessible_customers()` first, then try querying
  each returned customer ID directly before assuming MCC routing is needed.
