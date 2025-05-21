
import requests
import sys
from datetime import datetime

class AuthAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.text:
                    try:
                        return success, response.json()
                    except:
                        return success, response.text
                return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self, email, password):
        """Test login and get token"""
        # For login, we need to use form data instead of JSON
        url = f"{self.base_url}/auth/token"
        data = {"username": email, "password": password}
        
        print(f"\n🔍 Testing Login for {email}...")
        try:
            response = requests.post(
                url, 
                data=data,  # Use form data
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            success = response.status_code == 200
            if success:
                self.tests_passed += 1
                print(f"✅ Login Passed - Status: {response.status_code}")
                response_data = response.json()
                self.token = response_data.get('access_token')
                print(f"✅ Token received: {self.token[:10]}...")
                return True, response_data
            else:
                print(f"❌ Login Failed - Expected 200, got {response.status_code}")
                if response.text:
                    print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Login Failed - Error: {str(e)}")
            return False, {}

    def test_me_endpoint(self):
        """Test the /me endpoint to verify authentication"""
        return self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )

def main():
    # Get backend URL from environment variable or use default
    import os
    backend_url = "https://54bdef35-ae60-4161-ae24-d2c0da9aaead.preview.emergentagent.com/api"
    
    # Setup
    tester = AuthAPITester(backend_url)
    
    # Test login with admin credentials - using the correct password found in server.py
    login_success, login_data = tester.test_login("admin@example.com", "admin123")
    if not login_success:
        print("❌ Login failed, stopping tests")
        return 1
    
    # Test /me endpoint to verify authentication
    me_success, me_data = tester.test_me_endpoint()
    if not me_success:
        print("❌ Authentication verification failed")
        return 1
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
