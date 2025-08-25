import requests
import json
import os
from datetime import datetime, timedelta, timezone

# Configuration
SETUP_URL = "https://beds24.com/api/v2/authentication/setup"
TOKEN_URL = "https://beds24.com/api/v2/authentication/token"
DETAILS_URL = "https://beds24.com/api/v2/authentication/details"

# File names
INVITE_CODE_FILE = "beds24_invite_code.json"
REFRESH_TOKEN_FILE = "beds24_refresh_token.json"
AUTH_TOKEN_FILE = "beds24_auth_token.json"

class Beds24AuthManager:
    def __init__(self):
        self.invite_code_data = self._load_file(INVITE_CODE_FILE)
        self.refresh_token_data = self._load_file(REFRESH_TOKEN_FILE)
        self.auth_token_data = self._load_file(AUTH_TOKEN_FILE)
    
    def _load_file(self, filename):
        """Load JSON data from file, return empty dict if file doesn't exist or is empty"""
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_file(self, filename, data):
        """Save data to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except IOError:
            return False
    
    def _has_not_expired(self, data):
        """Check if token/credentials have not expired using UTC time"""
        if not data or 'expiration' not in data:
            return False

        try:
            # Parse the ISO 8601 datetime string
            expiration_date = datetime.fromisoformat(data['expiration'])

            # Make expiration_date timezone-aware (UTC) if it's naive
            if expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=timezone.utc)

            # Compare with current UTC time
            return datetime.now(timezone.utc) < expiration_date
        except (ValueError, TypeError) as e:
            print(f"Error parsing expiration date: {str(e)}")
            return False
    
    def _get_token_details(self, token):
        """Get information about a token using the details endpoint"""
        headers = {
            "accept": "application/json",
            "token": token
        }
        
        try:
            response = requests.get(DETAILS_URL, headers=headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting token details: {str(e)}")
        
        return None
    
    def setup_with_invite_code(self, invite_code, expiration_days=30):
        """Generate initial tokens using invite code"""
        if not invite_code:
            return False

        headers = {"accept": "application/json", "code": invite_code}

        try:
            response = requests.get(SETUP_URL, headers=headers)
            response.raise_for_status()
            token_data = response.json()

            # Calculate expiration dates using UTC
            expires_in = token_data.get("expiresIn", 86400)  # Default 24 hours
            current_utc = datetime.now(timezone.utc)
            auth_expiration = current_utc + timedelta(seconds=expires_in)
            refresh_expiration = current_utc + timedelta(days=expiration_days)

            # Save auth token
            auth_data = {
                "access_token": token_data["token"],
                "created": current_utc.isoformat(),
                "expiration": auth_expiration.isoformat()
            }
            self._save_file(AUTH_TOKEN_FILE, auth_data)

            # Save refresh token
            refresh_data = {
                "refresh_token": token_data["refreshToken"],
                "created": current_utc.isoformat(),
                "expiration": refresh_expiration.isoformat()
            }
            self._save_file(REFRESH_TOKEN_FILE, refresh_data)

            # Remove invite code after successful setup
            if os.path.exists(INVITE_CODE_FILE):
                os.remove(INVITE_CODE_FILE)

            print("✅ Setup completed successfully")
            return True

        except Exception as e:
            print(f"❌ Setup failed: {str(e)}")
            return False

    def refresh_auth_token(self):
        """Refresh access token using refresh token"""
        if not self.refresh_token_data or not self._has_not_expired(self.refresh_token_data):
            print("❌ No valid refresh token available")
            return False

        refresh_token = self.refresh_token_data.get("refresh_token")
        if not refresh_token:
            return False

        # Use GET request with refreshToken header (not POST with JSON body)
        headers = {
            "accept": "application/json",
            "refreshToken": refresh_token
        }

        try:
            response = requests.get(TOKEN_URL, headers=headers)
            response.raise_for_status()
            token_data = response.json()

            # Check if new tokens are in response
            if "token" not in token_data:
                print("❌ No access token in refresh response")
                return False

            expires_in = token_data.get("expiresIn", 86400)
            current_utc = datetime.now(timezone.utc)
            expiration = current_utc + timedelta(seconds=expires_in)

            # Update auth token
            auth_data = {
                "access_token": token_data["token"],
                "created": current_utc.isoformat(),
                "expiration": expiration.isoformat(),
            }
            self._save_file(AUTH_TOKEN_FILE, auth_data)
            self.auth_token_data = auth_data

            # Verify new token is valid
            if self.validate_token(auth_data["access_token"]):
                print("✅ Token refresh completed successfully")
                return True
            else:
                print("❌ New token failed validation")
                return False

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                print("❌ Refresh token rejected - may be invalid/expired")
            else:
                print(f"❌ Token refresh failed: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Token refresh failed: {str(e)}")
            return False
    
    def get_valid_token(self):
        """Get a valid access token, refreshing if necessary"""
        # Check if we have a valid auth token
        if self.auth_token_data and self._has_not_expired(self.auth_token_data):
            print("✅ Using existing valid auth token")
            return self.auth_token_data.get("access_token")
        
        # Try to refresh the auth token if it's expired but we have a valid refresh token
        if self.refresh_token_data and self._has_not_expired(self.refresh_token_data):
            print("🔄 Auth token expired, attempting refresh using refresh token")
            if self.refresh_auth_token():
                return self.auth_token_data.get("access_token")
        
        print("❌ No valid authentication method available")
        return None
    
    def check_token_status(self):
        """Check the status of all tokens and return their state"""
        status = {
            'auth_token': {
                'exists': bool(self.auth_token_data),
                'valid': self.auth_token_data and self._has_not_expired(self.auth_token_data),
                'expired': self.auth_token_data and not self._has_not_expired(self.auth_token_data)
            },
            'refresh_token': {
                'exists': bool(self.refresh_token_data),
                'valid': self.refresh_token_data and self._has_not_expired(self.refresh_token_data),
                'expired': self.refresh_token_data and not self._has_not_expired(self.refresh_token_data)
            },
            'invite_code': {
                'exists': bool(self.invite_code_data),
                'valid': self.invite_code_data and self._has_not_expired(self.invite_code_data),
                'expired': self.invite_code_data and not self._has_not_expired(self.invite_code_data)
            }
        }
        return status

    def validate_token(self, token):
        """Validate a token using the details endpoint"""
        details = self._get_token_details(token)
        if details and details.get("validToken", False):
            return True
        return False

# Example usage
if __name__ == "__main__":
    auth_manager = Beds24AuthManager()
    
    # Check token status
    status = auth_manager.check_token_status()
    print("Token Status:", json.dumps(status, indent=2))
    
    # Check if we need to set up with an invite code
    if (status['auth_token']['expired'] and 
        status['refresh_token']['expired'] and 
        status['invite_code']['exists'] and 
        status['invite_code']['valid']):
        
        print("🔑 Starting setup with invite code...")
        invite_code = auth_manager.invite_code_data.get("invite_code")
        auth_manager.setup_with_invite_code(invite_code)
    
    # Get a valid token
    token = auth_manager.get_valid_token()
    
    if token:
        print(f"✅ Valid token obtained: {token[:15]}...")
        
        # Validate the token
        if auth_manager.validate_token(token):
            print("✅ Token validation successful")
        else:
            print("❌ Token validation failed")
    else:
        print("❌ Failed to obtain valid token")
        # Check if we need to use an invite code for initial setup
        status = auth_manager.check_token_status()
        if (status['invite_code']['exists'] and status['invite_code']['valid'] and
            not status['refresh_token']['exists']):
            print("🔑 Attempting initial setup with invite code...")
            invite_code = auth_manager.invite_code_data.get("invite_code")
            if auth_manager.setup_with_invite_code(invite_code):
                token = auth_manager.get_valid_token()
                if token:
                    print(f"✅ Valid token obtained after setup: {token[:15]}...")
