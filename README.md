# Beds24 Authentication Manager

This repository contains a Python-based authentication manager for the Beds24 API
, designed to handle setup, token refresh, and validation seamlessly.

It provides a robust system for managing invite codes, access tokens, and refresh tokens, with intelligent fallback logic to ensure you always have a valid token available.

🚀 Features

Automated Token Handling

Supports initial setup with invite code

Refreshes expired access tokens using a valid refresh token

Validates tokens directly via the Beds24 API

Fallback Logic

Always attempts to reuse an existing valid access token first

If the access token is expired, tries to refresh using refresh token

If both tokens are invalid/expired but an invite code exists → runs setup again

If no valid method is available, gracefully fails with clear logs

File-Based Token Storage

Tokens and invite codes are stored locally as JSON files for persistence

Expiration dates are tracked in UTC

Auto-removes invite code once it has been used successfully

Resilient & Safe

JSON load/save is exception-safe

Handles missing/corrupted files gracefully

Provides clear console output for debugging

📂 File Structure

To work correctly, the manager expects the following files in the project root:

.
├── beds24_auth_manager.py        # Authentication manager (this script)
├── beds24_invite_code.json       # Contains initial invite code
├── beds24_refresh_token.json     # Stores refresh token + expiration
├── beds24_auth_token.json        # Stores access token + expiration

🔑 Example JSON Files
beds24_invite_code.json
{
  "invite_code": "ETxQfanX3EMlcqB...ZT+ilpGLSZRMmQ==",
  "created": "2025-08-20T20:56:21.098586+00:00",
  "expiration": "2025-08-22T20:56:21.098586+00:00"
}

beds24_refresh_token.json
{
  "refresh_token": "8L+T7VUx.....gpj1qBzgMXQ==",
  "created": "2025-08-21T10:52:19.004462+00:00",
  "expiration": "2025-09-20T10:52:19.004462+00:00"
}

beds24_auth_token.json
{
  "access_token": "szCbu......ieIijoVYTAw==",
  "created": "2025-08-21T10:52:19.004462+00:00",
  "expiration": "2025-08-22T10:52:19.004462+00:00"
}

🔁 Token Lifecycle & Fallback Logic

Check existing auth token

If valid → reuse it immediately

If expired → continue

Refresh token

If refresh token is valid → generate new access token

If refresh token is expired → continue

Invite code

If invite code exists and is valid → perform setup

If invite code has expired → fail

No valid method

Return None and log a clear error

🛠 Usage
from beds24_auth_manager import Beds24AuthManager

auth_manager = Beds24AuthManager()

# Get a valid access token (handles all fallback logic automatically)
token = auth_manager.get_valid_token()

if token:
    print("✅ Token ready:", token[:15], "...")
else:
    print("❌ No valid authentication available")

✅ Strengths of this Implementation

Automatic recovery from expired tokens without manual intervention

UTC-based expiration tracking avoids timezone pitfalls

Graceful error handling for network errors, JSON issues, or API failures

Clear separation of concerns (setup, refresh, validate, persistence)

Debug-friendly logging at every step of the lifecycle

📋 Example Console Output
Token Status: {
  "auth_token": { "exists": true, "valid": false, "expired": true },
  "refresh_token": { "exists": true, "valid": true, "expired": false },
  "invite_code": { "exists": false, "valid": false, "expired": false }
}
🔄 Auth token expired, attempting refresh using refresh token
✅ Token refresh completed successfully
✅ Valid token obtained: eyJhbGcOi123...
✅ Token validation successful
