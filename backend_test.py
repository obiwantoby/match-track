
import requests
import sys
import time
from datetime import datetime
import uuid

class ShootingMatchAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.user_token = None
        self.shooter_id = None
        self.match_id = None
        self.score_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
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
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test login with admin credentials"""
        # Convert to form data format required by OAuth2 password flow
        url = f"{self.base_url}/api/auth/token"
        data = {
            'username': 'admin@example.com',
            'password': 'admin123'
        }
        
        print(f"\n🔍 Testing Admin Login...")
        try:
            response = requests.post(url, data=data)
            success = response.status_code == 200
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                response_data = response.json()
                self.admin_token = response_data.get('access_token')
                return True, response_data
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_register_user(self):
        """Test registering a new user"""
        username = f"testuser_{int(time.time())}"
        email = f"{username}@example.com"
        password = "Test123!"
        
        success, response = self.run_test(
            "Register User",
            "POST",
            "auth/register",
            200,
            data={
                "username": username,
                "email": email,
                "password": password,
                "role": "reporter"
            }
        )
        
        if success:
            # Now try to login with the new user
            url = f"{self.base_url}/api/auth/token"
            data = {
                'username': email,
                'password': password
            }
            
            print(f"🔍 Testing Login with new user...")
            try:
                response = requests.post(url, data=data)
                success = response.status_code == 200
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    response_data = response.json()
                    self.user_token = response_data.get('access_token')
                    return True, response_data
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    print(f"Response: {response.text}")
                    return False, {}
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                return False, {}
        
        return False, {}

    def test_add_shooter(self):
        """Test adding a new shooter"""
        shooter_name = f"Test Shooter {int(time.time())}"
        
        success, response = self.run_test(
            "Add Shooter",
            "POST",
            "shooters",
            200,
            data={
                "name": shooter_name,
                "nra_number": "12345",
                "cmp_number": "67890"
            },
            token=self.admin_token
        )
        
        if success:
            self.shooter_id = response.get('id')
            return True, response
        
        return False, {}

    def test_add_match(self):
        """Test adding a new match"""
        match_name = f"Test Match {int(time.time())}"
        
        success, response = self.run_test(
            "Add Match",
            "POST",
            "matches",
            200,
            data={
                "name": match_name,
                "date": datetime.now().isoformat(),
                "location": "Test Range",
                "match_types": [
                    {
                        "type": "NMC",
                        "instance_name": "NMC1",
                        "calibers": [".22", "CF"]
                    }
                ],
                "aggregate_type": "None"
            },
            token=self.admin_token
        )
        
        if success:
            self.match_id = response.get('id')
            return True, response
        
        return False, {}

    def test_add_score(self):
        """Test adding a score for a shooter in a match"""
        if not self.shooter_id or not self.match_id:
            print("❌ Cannot add score: shooter_id or match_id is missing")
            return False, {}
        
        success, response = self.run_test(
            "Add Score",
            "POST",
            "scores",
            200,
            data={
                "shooter_id": self.shooter_id,
                "match_id": self.match_id,
                "caliber": ".22",
                "match_type_instance": "NMC1",
                "stages": [
                    {
                        "name": "SF",
                        "score": 95,
                        "x_count": 3
                    },
                    {
                        "name": "TF",
                        "score": 97,
                        "x_count": 4
                    },
                    {
                        "name": "RF",
                        "score": 98,
                        "x_count": 5
                    }
                ]
            },
            token=self.admin_token
        )
        
        if success:
            self.score_id = response.get('id')
            return True, response
        
        return False, {}

    def test_view_match_report(self):
        """Test viewing a match report"""
        if not self.match_id:
            print("❌ Cannot view match report: match_id is missing")
            return False, {}
        
        success, response = self.run_test(
            "View Match Report",
            "GET",
            f"match-report/{self.match_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_view_shooter_report(self):
        """Test viewing a shooter report"""
        if not self.shooter_id:
            print("❌ Cannot view shooter report: shooter_id is missing")
            return False, {}
        
        success, response = self.run_test(
            "View Shooter Report",
            "GET",
            f"shooter-report/{self.shooter_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

def main():
    # Get the backend URL from the environment
    backend_url = "https://06840937-4331-432f-b73a-db2e1d4be260.preview.emergentagent.com"
    
    # Setup
    tester = ShootingMatchAPITester(backend_url)
    
    # Run tests
    print("\n===== TESTING SHOOTING MATCH SCORE MANAGEMENT API =====\n")
    
    # Test 1: Admin Login
    admin_login_success, _ = tester.test_admin_login()
    if not admin_login_success:
        print("❌ Admin login failed, stopping tests")
        return 1
    
    # Test 2: Register User
    register_success, _ = tester.test_register_user()
    if not register_success:
        print("❌ User registration failed")
    
    # Test 3: Add Shooter
    shooter_success, _ = tester.test_add_shooter()
    if not shooter_success:
        print("❌ Adding shooter failed")
    
    # Test 4: Add Match
    match_success, _ = tester.test_add_match()
    if not match_success:
        print("❌ Adding match failed")
    
    # Test 5: Add Score
    if shooter_success and match_success:
        score_success, _ = tester.test_add_score()
        if not score_success:
            print("❌ Adding score failed")
    
    # Test 6: View Match Report
    if match_success:
        match_report_success, _ = tester.test_view_match_report()
        if not match_report_success:
            print("❌ Viewing match report failed")
    
    # Test 7: View Shooter Report
    if shooter_success:
        shooter_report_success, _ = tester.test_view_shooter_report()
        if not shooter_report_success:
            print("❌ Viewing shooter report failed")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
