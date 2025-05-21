import requests
import sys
import time
from datetime import datetime
import uuid
import json

class MatchReportTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.shooter_id = None
        self.match_id = None
        self.score_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

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

    def test_match_report_with_score_ids(self):
        """Test that match report includes score IDs"""
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
        
        if not success:
            return False, {}
        
        # Verify the match report contains score IDs
        print("\n🔍 Verifying match report contains score IDs...")
        
        if "shooters" not in response:
            print("❌ shooters missing from match report")
            return False, {}
        
        if len(response["shooters"]) == 0:
            print("❌ No shooters found in match report")
            return False, {}
        
        # Check the shooter's scores
        shooter_id = self.shooter_id
        if shooter_id not in response["shooters"]:
            print(f"❌ Shooter {shooter_id} not found in match report")
            return False, {}
        
        shooter_data = response["shooters"][shooter_id]
        
        if "scores" not in shooter_data:
            print("❌ scores missing from shooter data")
            return False, {}
        
        if len(shooter_data["scores"]) == 0:
            print("❌ No scores found for shooter")
            return False, {}
        
        # Find the score
        score_found = False
        score_id_found = False
        score_id = None
        
        for key, score_data in shooter_data["scores"].items():
            score_found = True
            print(f"Found score with key: {key}")
            
            if "score" in score_data and "id" in score_data["score"]:
                score_id = score_data["score"]["id"]
                score_id_found = True
                print(f"✅ Score ID found: {score_id}")
                break
        
        if not score_found:
            print("❌ No scores found in match report")
            return False, {}
        
        if not score_id_found:
            print("❌ Score ID not found in match report")
            return False, {}
        
        # Verify the score ID matches the one we created
        if score_id != self.score_id:
            print(f"❌ Score ID mismatch: {score_id} != {self.score_id}")
            return False, {}
        
        print(f"✅ Score ID in match report matches the created score ID")
        return True, {"score_id": score_id}

    def test_get_score_by_id(self, score_id):
        """Test getting a score by ID"""
        if not score_id:
            print("❌ Cannot get score: score_id is missing")
            return False, {}
        
        success, response = self.run_test(
            "Get Score by ID",
            "GET",
            f"scores/{score_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False, {}
        
        # Verify the score ID matches
        if response.get('id') != score_id:
            print(f"❌ Retrieved score ID mismatch: {response.get('id')} != {score_id}")
            return False, {}
        
        print(f"✅ Successfully retrieved score using ID from match report")
        return True, response

    def test_update_score_by_id(self, score_id):
        """Test updating a score by ID"""
        if not score_id or not self.shooter_id or not self.match_id:
            print("❌ Cannot update score: score_id, shooter_id, or match_id is missing")
            return False, {}
        
        success, response = self.run_test(
            "Update Score by ID",
            "PUT",
            f"scores/{score_id}",
            200,
            data={
                "shooter_id": self.shooter_id,
                "match_id": self.match_id,
                "caliber": ".22",
                "match_type_instance": "NMC1",
                "stages": [
                    {
                        "name": "SF",
                        "score": 96,  # Updated score
                        "x_count": 4   # Updated X count
                    },
                    {
                        "name": "TF",
                        "score": 98,
                        "x_count": 5
                    },
                    {
                        "name": "RF",
                        "score": 99,
                        "x_count": 6
                    }
                ]
            },
            token=self.admin_token
        )
        
        if not success:
            return False, {}
        
        # Verify the score ID matches
        if response.get('id') != score_id:
            print(f"❌ Updated score ID mismatch: {response.get('id')} != {score_id}")
            return False, {}
        
        print(f"✅ Successfully updated score using ID from match report")
        return True, response

def main():
    # Get the backend URL from the environment
    backend_url = "https://ecc4b2e5-4738-47d7-aabd-fec160cafe64.preview.emergentagent.com"
    
    # Setup
    tester = MatchReportTester(backend_url)
    
    # Run tests
    print("\n===== TESTING MATCH REPORT WITH SCORE IDS =====\n")
    
    # Authentication Tests
    admin_login_success, _ = tester.test_admin_login()
    if not admin_login_success:
        print("❌ Admin login failed, stopping tests")
        return 1
    
    # Create test data
    shooter_success, _ = tester.test_add_shooter()
    if not shooter_success:
        print("❌ Adding shooter failed, stopping tests")
        return 1
    
    match_success, _ = tester.test_add_match()
    if not match_success:
        print("❌ Adding match failed, stopping tests")
        return 1
    
    score_success, _ = tester.test_add_score()
    if not score_success:
        print("❌ Adding score failed, stopping tests")
        return 1
    
    # Test match report with score IDs
    match_report_success, match_report_data = tester.test_match_report_with_score_ids()
    if not match_report_success:
        print("❌ Match report test failed, stopping tests")
        return 1
    
    # Get the score ID from the match report
    score_id = match_report_data.get('score_id')
    
    # Test getting a score by ID
    get_score_success, _ = tester.test_get_score_by_id(score_id)
    if not get_score_success:
        print("❌ Getting score by ID failed")
        return 1
    
    # Test updating a score by ID
    update_score_success, _ = tester.test_update_score_by_id(score_id)
    if not update_score_success:
        print("❌ Updating score by ID failed")
        return 1
    
    # Print summary
    print("\n===== TEST SUMMARY =====")
    print("✅ Match report includes score IDs")
    print("✅ Score IDs can be used with GET /api/scores/{score_id}")
    print("✅ Score IDs can be used with PUT /api/scores/{score_id}")
    print("✅ All tests passed successfully")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())