
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
        self.user_id = None
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
                    self.user_id = response_data.get('user_id')
                    return True, response_data
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    print(f"Response: {response.text}")
                    return False, {}
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                return False, {}
        
        return False, {}

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.admin_token:
            print("❌ Cannot get user info: admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_users(self):
        """Test getting all users (admin only)"""
        if not self.admin_token:
            print("❌ Cannot get users: admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get All Users",
            "GET",
            "users",
            200,
            token=self.admin_token
        )
        
        return success, response

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

    def test_get_shooters(self):
        """Test getting all shooters"""
        if not self.admin_token:
            print("❌ Cannot get shooters: admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get All Shooters",
            "GET",
            "shooters",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_shooter(self):
        """Test getting a specific shooter"""
        if not self.shooter_id or not self.admin_token:
            print("❌ Cannot get shooter: shooter_id or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Shooter",
            "GET",
            f"shooters/{self.shooter_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

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
        
    def test_add_match_with_subtotals(self):
        """Test adding a new match with subtotal configuration"""
        match_name = f"Test Match with Subtotals {int(time.time())}"
        
        success, response = self.run_test(
            "Add Match with Subtotals",
            "POST",
            "matches",
            200,
            data={
                "name": match_name,
                "date": datetime.now().isoformat(),
                "location": "Test Range with Subtotals",
                "match_types": [
                    {
                        "type": "900",
                        "instance_name": "900_1",
                        "calibers": [".22", "CF", ".45"]
                    }
                ],
                "aggregate_type": "None"
            },
            token=self.admin_token
        )
        
        if success:
            self.match_id_with_subtotals = response.get('id')
            print(f"✅ Created match with subtotals, ID: {self.match_id_with_subtotals}")
            return True, response
        
        return False, {}

    def test_get_matches(self):
        """Test getting all matches"""
        if not self.admin_token:
            print("❌ Cannot get matches: admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get All Matches",
            "GET",
            "matches",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_match(self):
        """Test getting a specific match"""
        if not self.match_id or not self.admin_token:
            print("❌ Cannot get match: match_id or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Match",
            "GET",
            f"matches/{self.match_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_match_types(self):
        """Test getting all match types"""
        if not self.admin_token:
            print("❌ Cannot get match types: admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Match Types",
            "GET",
            "match-types",
            200,
            token=self.admin_token
        )
        
        # Verify the structure of match types, especially for 900-point aggregate
        if success:
            print("\n🔍 Verifying match types structure...")
            
            # Check if all match types are present
            expected_types = ["NMC", "600", "900", "Presidents"]
            for match_type in expected_types:
                if match_type not in response:
                    print(f"❌ Match type {match_type} is missing from response")
                    success = False
            
            # Verify 900-point aggregate structure
            if "900" in response:
                nine_hundred = response["900"]
                
                # Check entry stages
                if "entry_stages" not in nine_hundred:
                    print("❌ entry_stages missing from 900-point match type")
                    success = False
                elif set(nine_hundred["entry_stages"]) != {"SF1", "SF2", "TF1", "TF2", "RF1", "RF2"}:
                    print(f"❌ Incorrect entry_stages for 900-point match type: {nine_hundred['entry_stages']}")
                    success = False
                
                # Check subtotal stages
                if "subtotal_stages" not in nine_hundred:
                    print("❌ subtotal_stages missing from 900-point match type")
                    success = False
                elif set(nine_hundred["subtotal_stages"]) != {"SFNMC", "TFNMC", "RFNMC"}:
                    print(f"❌ Incorrect subtotal_stages for 900-point match type: {nine_hundred['subtotal_stages']}")
                    success = False
                
                # Check subtotal mappings
                if "subtotal_mappings" not in nine_hundred:
                    print("❌ subtotal_mappings missing from 900-point match type")
                    success = False
                else:
                    mappings = nine_hundred["subtotal_mappings"]
                    expected_mappings = {
                        "SFNMC": ["SF1", "SF2"],
                        "TFNMC": ["TF1", "TF2"],
                        "RFNMC": ["RF1", "RF2"]
                    }
                    
                    for subtotal, stages in expected_mappings.items():
                        if subtotal not in mappings:
                            print(f"❌ Subtotal {subtotal} missing from subtotal_mappings")
                            success = False
                        elif set(mappings[subtotal]) != set(stages):
                            print(f"❌ Incorrect mapping for {subtotal}: {mappings[subtotal]}")
                            success = False
            else:
                print("❌ 900-point match type is missing from response")
                success = False
            
            if success:
                print("✅ Match types structure verified successfully")
        
        return success, response

    def test_get_match_config(self):
        """Test getting match configuration"""
        if not self.match_id or not self.admin_token:
            print("❌ Cannot get match config: match_id or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Match Config",
            "GET",
            f"match-config/{self.match_id}",
            200,
            token=self.admin_token
        )
        
        return success, response
        
    def test_get_match_config_with_subtotals(self):
        """Test getting match configuration with subtotals"""
        if not hasattr(self, 'match_id_with_subtotals') or not self.match_id_with_subtotals or not self.admin_token:
            print("❌ Cannot get match config with subtotals: match_id_with_subtotals or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Match Config with Subtotals",
            "GET",
            f"match-config/{self.match_id_with_subtotals}",
            200,
            token=self.admin_token
        )
        
        # Verify the structure of match configuration with subtotals
        if success:
            print("\n🔍 Verifying match configuration with subtotals...")
            
            # Check if match types are present
            if "match_types" not in response:
                print("❌ match_types missing from match configuration")
                success = False
            else:
                match_types = response["match_types"]
                
                # Find the 900-point match type
                nine_hundred_match = None
                for match_type in match_types:
                    if match_type.get("type") == "900":
                        nine_hundred_match = match_type
                        break
                
                if not nine_hundred_match:
                    print("❌ 900-point match type not found in match configuration")
                    success = False
                else:
                    # Check entry stages
                    if "entry_stages" not in nine_hundred_match:
                        print("❌ entry_stages missing from 900-point match type configuration")
                        success = False
                    elif set(nine_hundred_match["entry_stages"]) != {"SF1", "SF2", "TF1", "TF2", "RF1", "RF2"}:
                        print(f"❌ Incorrect entry_stages for 900-point match type: {nine_hundred_match['entry_stages']}")
                        success = False
                    
                    # Check subtotal stages
                    if "subtotal_stages" not in nine_hundred_match:
                        print("❌ subtotal_stages missing from 900-point match type configuration")
                        success = False
                    elif set(nine_hundred_match["subtotal_stages"]) != {"SFNMC", "TFNMC", "RFNMC"}:
                        print(f"❌ Incorrect subtotal_stages for 900-point match type: {nine_hundred_match['subtotal_stages']}")
                        success = False
                    
                    # Check subtotal mappings
                    if "subtotal_mappings" not in nine_hundred_match:
                        print("❌ subtotal_mappings missing from 900-point match type configuration")
                        success = False
                    else:
                        mappings = nine_hundred_match["subtotal_mappings"]
                        expected_mappings = {
                            "SFNMC": ["SF1", "SF2"],
                            "TFNMC": ["TF1", "TF2"],
                            "RFNMC": ["RF1", "RF2"]
                        }
                        
                        for subtotal, stages in expected_mappings.items():
                            if subtotal not in mappings:
                                print(f"❌ Subtotal {subtotal} missing from subtotal_mappings")
                                success = False
                            elif set(mappings[subtotal]) != set(stages):
                                print(f"❌ Incorrect mapping for {subtotal}: {mappings[subtotal]}")
                                success = False
            
            if success:
                print("✅ Match configuration with subtotals verified successfully")
        
        return success, response

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
        
    def test_add_score_with_subtotals(self):
        """Test adding scores for a match with subtotals"""
        if not self.shooter_id or not hasattr(self, 'match_id_with_subtotals') or not self.match_id_with_subtotals:
            print("❌ Cannot add score with subtotals: shooter_id or match_id_with_subtotals is missing")
            return False, {}
        
        # Add score for .22 caliber
        success1, response1 = self.run_test(
            "Add Score with Subtotals (.22)",
            "POST",
            "scores",
            200,
            data={
                "shooter_id": self.shooter_id,
                "match_id": self.match_id_with_subtotals,
                "caliber": ".22",
                "match_type_instance": "900_1",
                "stages": [
                    {
                        "name": "SF1",
                        "score": 95,
                        "x_count": 3
                    },
                    {
                        "name": "SF2",
                        "score": 96,
                        "x_count": 4
                    },
                    {
                        "name": "TF1",
                        "score": 97,
                        "x_count": 5
                    },
                    {
                        "name": "TF2",
                        "score": 98,
                        "x_count": 6
                    },
                    {
                        "name": "RF1",
                        "score": 99,
                        "x_count": 7
                    },
                    {
                        "name": "RF2",
                        "score": 100,
                        "x_count": 8
                    }
                ]
            },
            token=self.admin_token
        )
        
        if success1:
            self.score_id_with_subtotals_22 = response1.get('id')
            print(f"✅ Added .22 caliber score for match with subtotals, ID: {self.score_id_with_subtotals_22}")
        else:
            return False, {}
        
        # Add score for CF caliber
        success2, response2 = self.run_test(
            "Add Score with Subtotals (CF)",
            "POST",
            "scores",
            200,
            data={
                "shooter_id": self.shooter_id,
                "match_id": self.match_id_with_subtotals,
                "caliber": "CF",
                "match_type_instance": "900_1",
                "stages": [
                    {
                        "name": "SF1",
                        "score": 94,
                        "x_count": 2
                    },
                    {
                        "name": "SF2",
                        "score": 95,
                        "x_count": 3
                    },
                    {
                        "name": "TF1",
                        "score": 96,
                        "x_count": 4
                    },
                    {
                        "name": "TF2",
                        "score": 97,
                        "x_count": 5
                    },
                    {
                        "name": "RF1",
                        "score": 98,
                        "x_count": 6
                    },
                    {
                        "name": "RF2",
                        "score": 99,
                        "x_count": 7
                    }
                ]
            },
            token=self.admin_token
        )
        
        if success2:
            self.score_id_with_subtotals_cf = response2.get('id')
            print(f"✅ Added CF caliber score for match with subtotals, ID: {self.score_id_with_subtotals_cf}")
        else:
            return False, {}
        
        return success1 and success2, {"22": response1, "CF": response2}

    def test_get_scores(self):
        """Test getting all scores"""
        if not self.admin_token:
            print("❌ Cannot get scores: admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get All Scores",
            "GET",
            "scores",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_scores_by_match(self):
        """Test getting scores by match"""
        if not self.match_id or not self.admin_token:
            print("❌ Cannot get scores by match: match_id or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Scores By Match",
            "GET",
            f"scores?match_id={self.match_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_scores_by_shooter(self):
        """Test getting scores by shooter"""
        if not self.shooter_id or not self.admin_token:
            print("❌ Cannot get scores by shooter: shooter_id or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Scores By Shooter",
            "GET",
            f"scores?shooter_id={self.shooter_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_get_score(self):
        """Test getting a specific score"""
        if not self.score_id or not self.admin_token:
            print("❌ Cannot get score: score_id or admin_token is missing")
            return False, {}
            
        success, response = self.run_test(
            "Get Score",
            "GET",
            f"scores/{self.score_id}",
            200,
            token=self.admin_token
        )
        
        return success, response

    def test_update_score(self):
        """Test updating a score"""
        if not self.score_id or not self.admin_token:
            print("❌ Cannot update score: score_id or admin_token is missing")
            return False, {}
        
        success, response = self.run_test(
            "Update Score",
            "PUT",
            f"scores/{self.score_id}",
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
        
        return success, response

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
        
    def test_view_match_report_with_subtotals(self):
        """Test viewing a match report with subtotals"""
        if not hasattr(self, 'match_id_with_subtotals') or not self.match_id_with_subtotals:
            print("❌ Cannot view match report with subtotals: match_id_with_subtotals is missing")
            return False, {}
        
        # Add a small delay to allow the database to update
        time.sleep(2)
        
        success, response = self.run_test(
            "View Match Report with Subtotals",
            "GET",
            f"match-report/{self.match_id_with_subtotals}",
            200,
            token=self.admin_token
        )
        
        # Verify the structure of match report with subtotals
        if success:
            print("\n🔍 Verifying match report with subtotals...")
            
            # Check if shooters are present
            if "shooters" not in response:
                print("❌ shooters missing from match report")
                success = False
            elif len(response["shooters"]) == 0:
                print("❌ No shooters found in match report")
                success = False
            else:
                # Check the first shooter's scores
                shooter_id = self.shooter_id
                if shooter_id not in response["shooters"]:
                    print(f"❌ Shooter {shooter_id} not found in match report")
                    success = False
                else:
                    shooter_data = response["shooters"][shooter_id]
                    
                    # Check if scores are present
                    if "scores" not in shooter_data:
                        print("❌ scores missing from shooter data")
                        success = False
                    elif len(shooter_data["scores"]) == 0:
                        print("❌ No scores found for shooter")
                        success = False
                    else:
                        # Print all available score keys for debugging
                        score_keys = list(shooter_data['scores'].keys())
                        print(f"Available score keys: {score_keys}")
                        
                        # Find the .22 caliber score key
                        key_22 = None
                        for key in score_keys:
                            if "900_1" in key and "TWENTYTWO" in key:
                                key_22 = key
                                break
                        
                        if not key_22:
                            print(f"❌ .22 caliber score not found for shooter")
                            success = False
                        else:
                            print(f"Found .22 caliber score with key: {key_22}")
                            score_data_22 = shooter_data["scores"][key_22]
                            
                            # Check if subtotals are present
                            if "subtotals" not in score_data_22:
                                print("❌ subtotals missing from .22 caliber score")
                                success = False
                            elif len(score_data_22["subtotals"]) == 0:
                                print("❌ No subtotals found for .22 caliber score")
                                success = False
                            else:
                                # Check specific subtotals
                                expected_subtotals = ["SFNMC", "TFNMC", "RFNMC"]
                                for subtotal in expected_subtotals:
                                    if subtotal not in score_data_22["subtotals"]:
                                        print(f"❌ Subtotal {subtotal} not found in .22 caliber score")
                                        success = False
                                    else:
                                        subtotal_data = score_data_22["subtotals"][subtotal]
                                        if "score" not in subtotal_data or "x_count" not in subtotal_data:
                                            print(f"❌ score or x_count missing from {subtotal} subtotal")
                                            success = False
                                
                                # Verify SFNMC subtotal calculation
                                if "SFNMC" in score_data_22["subtotals"]:
                                    sfnmc = score_data_22["subtotals"]["SFNMC"]
                                    sf1_score = 0
                                    sf2_score = 0
                                    sf1_x = 0
                                    sf2_x = 0
                                    
                                    # Find SF1 and SF2 stages in the score
                                    for stage in score_data_22["score"]["stages"]:
                                        if stage["name"] == "SF1":
                                            sf1_score = stage["score"]
                                            sf1_x = stage["x_count"]
                                        elif stage["name"] == "SF2":
                                            sf2_score = stage["score"]
                                            sf2_x = stage["x_count"]
                                    
                                    expected_score = sf1_score + sf2_score
                                    expected_x = sf1_x + sf2_x
                                    
                                    if sfnmc["score"] != expected_score:
                                        print(f"❌ Incorrect SFNMC subtotal score: expected {expected_score}, got {sfnmc['score']}")
                                        success = False
                                    
                                    if sfnmc["x_count"] != expected_x:
                                        print(f"❌ Incorrect SFNMC subtotal x_count: expected {expected_x}, got {sfnmc['x_count']}")
                                        success = False
                        
                        # Find the CF caliber score key
                        key_cf = None
                        for key in score_keys:
                            if "900_1" in key and "CENTERFIRE" in key:
                                key_cf = key
                                break
                        
                        if not key_cf:
                            print(f"❌ CF caliber score not found for shooter")
                            success = False
                        else:
                            print(f"Found CF caliber score with key: {key_cf}")
                            score_data_cf = shooter_data["scores"][key_cf]
                            
                            # Check if subtotals are present
                            if "subtotals" not in score_data_cf:
                                print("❌ subtotals missing from CF caliber score")
                                success = False
                            elif len(score_data_cf["subtotals"]) == 0:
                                print("❌ No subtotals found for CF caliber score")
                                success = False
            
            if success:
                print("✅ Match report with subtotals verified successfully")
        
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

    def test_view_shooter_averages(self):
        """Test viewing shooter averages"""
        if not self.shooter_id:
            print("❌ Cannot view shooter averages: shooter_id is missing")
            return False, {}
        
        success, response = self.run_test(
            "View Shooter Averages",
            "GET",
            f"shooter-averages/{self.shooter_id}",
            200,
            token=self.admin_token
        )
        
        return success, response
        
    def test_match_report_excel_export(self):
        """Test the Excel export of a match report"""
        if not self.match_id or not self.admin_token:
            print("❌ Cannot test Excel export: match_id or admin_token is missing")
            return False, {}
            
        print(f"\n🔍 Testing Match Report Excel Export...")
        url = f"{self.base_url}/api/match-report/{self.match_id}/excel"
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        try:
            response = requests.get(url, headers=headers)
            success = response.status_code == 200
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Verify content type is Excel
                content_type = response.headers.get('Content-Type')
                if content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                    print(f"❌ Wrong content type: {content_type}")
                    return False, {}
                
                # Verify Content-Disposition header exists and contains filename
                content_disposition = response.headers.get('Content-Disposition')
                if not content_disposition or 'attachment; filename=' not in content_disposition:
                    print(f"❌ Missing or invalid Content-Disposition header: {content_disposition}")
                    return False, {}
                
                print(f"✅ Excel file headers verified")
                
                # Save the Excel file for further testing if needed
                excel_data = response.content
                print(f"✅ Successfully downloaded Excel file ({len(excel_data)} bytes)")
                
                return True, {"content_type": content_type, "content_disposition": content_disposition}
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_reporter_permissions(self):
        """Test reporter permissions (should not be able to add/edit data)"""
        if not self.user_token:
            print("❌ Cannot test reporter permissions: user_token is missing")
            return False, {}
        
        # Try to add a shooter (should fail with 403)
        success, _ = self.run_test(
            "Reporter Add Shooter (should fail)",
            "POST",
            "shooters",
            403,
            data={
                "name": "Test Shooter",
                "nra_number": "12345",
                "cmp_number": "67890"
            },
            token=self.user_token
        )
        
        # Try to add a match (should fail with 403)
        success2, _ = self.run_test(
            "Reporter Add Match (should fail)",
            "POST",
            "matches",
            403,
            data={
                "name": "Test Match",
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
            token=self.user_token
        )
        
        # Try to add a score (should fail with 403)
        success3, _ = self.run_test(
            "Reporter Add Score (should fail)",
            "POST",
            "scores",
            403,
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
                    }
                ]
            },
            token=self.user_token
        )
        
        # Try to view users (should fail with 403)
        success4, _ = self.run_test(
            "Reporter View Users (should fail)",
            "GET",
            "users",
            403,
            token=self.user_token
        )
        
        # Reporter should be able to view data
        success5, _ = self.run_test(
            "Reporter View Shooters",
            "GET",
            "shooters",
            200,
            token=self.user_token
        )
        
        success6, _ = self.run_test(
            "Reporter View Matches",
            "GET",
            "matches",
            200,
            token=self.user_token
        )
        
        return success and success2 and success3 and success4 and success5 and success6, {}

def test_excel_export_with_missing_scores(tester):
    """Test the Excel export functionality with a focus on missing scores and average calculation"""
    print("\n===== TESTING EXCEL EXPORT WITH MISSING SCORES =====\n")
    
    # Step 1: Create two shooters for testing
    shooter_success, shooter_response = tester.test_add_shooter()
    if not shooter_success:
        print("❌ Adding first shooter failed, cannot continue Excel export test")
        return False
    
    shooter1_id = tester.shooter_id
    shooter1_name = shooter_response.get('name')
    print(f"✅ Created first test shooter with ID: {shooter1_id}")
    
    # Create a second shooter
    shooter2_name = f"Test Shooter 2 {int(time.time())}"
    success, shooter2_response = tester.run_test(
        "Add Second Shooter",
        "POST",
        "shooters",
        200,
        data={
            "name": shooter2_name,
            "nra_number": "54321",
            "cmp_number": "09876"
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding second shooter failed, cannot continue Excel export test")
        return False
    
    shooter2_id = shooter2_response.get('id')
    print(f"✅ Created second test shooter with ID: {shooter2_id}")
    
    # Step 2: Create a match with multiple match types and calibers
    match_name = f"Excel Export Test Match {int(time.time())}"
    
    success, response = tester.run_test(
        "Create Match for Excel Export Test",
        "POST",
        "matches",
        200,
        data={
            "name": match_name,
            "date": datetime.now().isoformat(),
            "location": "Test Range for Excel Export",
            "match_types": [
                {
                    "type": "NMC",
                    "instance_name": "NMC1",
                    "calibers": [".22", "CF", ".45"]
                },
                {
                    "type": "NMC",
                    "instance_name": "NMC2",
                    "calibers": [".22", "CF", ".45"]
                }
            ],
            "aggregate_type": "None"
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Creating match failed, cannot continue Excel export test")
        return False
    
    match_id = response.get('id')
    print(f"✅ Created match with ID: {match_id}")
    
    # Step 3: Add scores for the first shooter (all calibers in NMC1, only .22 in NMC2)
    # NMC1 - .22 caliber
    success, _ = tester.run_test(
        "Add Score - Shooter 1, NMC1, .22",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter1_id,
            "match_id": match_id,
            "caliber": ".22",
            "match_type_instance": "NMC1",
            "stages": [
                {"name": "SF", "score": 95, "x_count": 3},
                {"name": "TF", "score": 97, "x_count": 4},
                {"name": "RF", "score": 98, "x_count": 5}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 1, NMC1, .22 failed")
        return False
    
    # NMC1 - CF caliber
    success, _ = tester.run_test(
        "Add Score - Shooter 1, NMC1, CF",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter1_id,
            "match_id": match_id,
            "caliber": "CF",
            "match_type_instance": "NMC1",
            "stages": [
                {"name": "SF", "score": 94, "x_count": 2},
                {"name": "TF", "score": 96, "x_count": 3},
                {"name": "RF", "score": 97, "x_count": 4}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 1, NMC1, CF failed")
        return False
    
    # NMC1 - .45 caliber
    success, _ = tester.run_test(
        "Add Score - Shooter 1, NMC1, .45",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter1_id,
            "match_id": match_id,
            "caliber": ".45",
            "match_type_instance": "NMC1",
            "stages": [
                {"name": "SF", "score": 93, "x_count": 1},
                {"name": "TF", "score": 95, "x_count": 2},
                {"name": "RF", "score": 96, "x_count": 3}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 1, NMC1, .45 failed")
        return False
    
    # NMC2 - .22 caliber only (intentionally missing CF and .45 for NMC2)
    success, _ = tester.run_test(
        "Add Score - Shooter 1, NMC2, .22",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter1_id,
            "match_id": match_id,
            "caliber": ".22",
            "match_type_instance": "NMC2",
            "stages": [
                {"name": "SF", "score": 96, "x_count": 4},
                {"name": "TF", "score": 98, "x_count": 5},
                {"name": "RF", "score": 99, "x_count": 6}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 1, NMC2, .22 failed")
        return False
    
    # Step 4: Add scores for the second shooter (only .22 in NMC1, all calibers in NMC2)
    # NMC1 - .22 caliber only (intentionally missing CF and .45 for NMC1)
    success, _ = tester.run_test(
        "Add Score - Shooter 2, NMC1, .22",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter2_id,
            "match_id": match_id,
            "caliber": ".22",
            "match_type_instance": "NMC1",
            "stages": [
                {"name": "SF", "score": 92, "x_count": 2},
                {"name": "TF", "score": 94, "x_count": 3},
                {"name": "RF", "score": 95, "x_count": 4}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 2, NMC1, .22 failed")
        return False
    
    # NMC2 - .22 caliber
    success, _ = tester.run_test(
        "Add Score - Shooter 2, NMC2, .22",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter2_id,
            "match_id": match_id,
            "caliber": ".22",
            "match_type_instance": "NMC2",
            "stages": [
                {"name": "SF", "score": 93, "x_count": 3},
                {"name": "TF", "score": 95, "x_count": 4},
                {"name": "RF", "score": 96, "x_count": 5}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 2, NMC2, .22 failed")
        return False
    
    # NMC2 - CF caliber
    success, _ = tester.run_test(
        "Add Score - Shooter 2, NMC2, CF",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter2_id,
            "match_id": match_id,
            "caliber": "CF",
            "match_type_instance": "NMC2",
            "stages": [
                {"name": "SF", "score": 91, "x_count": 1},
                {"name": "TF", "score": 93, "x_count": 2},
                {"name": "RF", "score": 94, "x_count": 3}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 2, NMC2, CF failed")
        return False
    
    # NMC2 - .45 caliber
    success, _ = tester.run_test(
        "Add Score - Shooter 2, NMC2, .45",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter2_id,
            "match_id": match_id,
            "caliber": ".45",
            "match_type_instance": "NMC2",
            "stages": [
                {"name": "SF", "score": 90, "x_count": 0},
                {"name": "TF", "score": 92, "x_count": 1},
                {"name": "RF", "score": 93, "x_count": 2}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score for Shooter 2, NMC2, .45 failed")
        return False
    
    # Step 5: Add a score with 0 points (not missing) to test average calculation
    success, _ = tester.run_test(
        "Add Score with 0 points - Shooter 1, NMC2, CF",
        "POST",
        "scores",
        200,
        data={
            "shooter_id": shooter1_id,
            "match_id": match_id,
            "caliber": "CF",
            "match_type_instance": "NMC2",
            "stages": [
                {"name": "SF", "score": 0, "x_count": 0},
                {"name": "TF", "score": 0, "x_count": 0},
                {"name": "RF", "score": 0, "x_count": 0}
            ]
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score with 0 points failed")
        return False
    
    print("✅ Successfully added all test scores")
    
    # Step 6: Test the match report to verify data is correct
    success, report_response = tester.run_test(
        "View Match Report",
        "GET",
        f"match-report/{match_id}",
        200,
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Viewing match report failed")
        return False
    
    print("✅ Successfully retrieved match report")
    
    # Step 7: Test the Excel export
    print(f"\n🔍 Testing Match Report Excel Export...")
    url = f"{tester.base_url}/api/match-report/{match_id}/excel"
    headers = {'Authorization': f'Bearer {tester.admin_token}'}
    
    try:
        response = requests.get(url, headers=headers)
        success = response.status_code == 200
        
        if success:
            tester.tests_passed += 1
            print(f"✅ Passed - Status: {response.status_code}")
            
            # Verify content type is Excel
            content_type = response.headers.get('Content-Type')
            if content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                print(f"❌ Wrong content type: {content_type}")
                return False
            
            # Verify Content-Disposition header exists and contains filename
            content_disposition = response.headers.get('Content-Disposition')
            if not content_disposition or 'attachment; filename=' not in content_disposition:
                print(f"❌ Missing or invalid Content-Disposition header: {content_disposition}")
                return False
            
            print(f"✅ Excel file headers verified")
            
            # Save the Excel file for further testing
            excel_data = response.content
            print(f"✅ Successfully downloaded Excel file ({len(excel_data)} bytes)")
            
            # We can't easily parse the Excel file in this environment to verify its contents,
            # but we can verify that the file was generated and has a reasonable size
            if len(excel_data) < 1000:  # A reasonable Excel file should be at least 1KB
                print(f"❌ Excel file seems too small: {len(excel_data)} bytes")
                return False
            
            print("✅ Excel file size is reasonable")
            
            # Since we can't directly verify the Excel content, we'll rely on the match report data
            # to infer that the Excel export should be correct
            
            # Verify the match report contains both shooters
            if "shooters" not in report_response:
                print("❌ shooters missing from match report")
                return False
            
            if shooter1_id not in report_response["shooters"] or shooter2_id not in report_response["shooters"]:
                print(f"❌ Not all shooters found in match report")
                return False
            
            # Verify the first shooter has scores for all calibers in NMC1
            shooter1_data = report_response["shooters"][shooter1_id]
            if "scores" not in shooter1_data:
                print("❌ scores missing from shooter 1 data")
                return False
            
            # Count the number of scores for shooter 1
            shooter1_score_count = len(shooter1_data["scores"])
            if shooter1_score_count != 5:  # Should have 5 scores: 3 for NMC1, 2 for NMC2
                print(f"❌ Expected 5 scores for shooter 1, found {shooter1_score_count}")
                return False
            
            # Verify the second shooter has scores for all calibers in NMC2
            shooter2_data = report_response["shooters"][shooter2_id]
            if "scores" not in shooter2_data:
                print("❌ scores missing from shooter 2 data")
                return False
            
            # Count the number of scores for shooter 2
            shooter2_score_count = len(shooter2_data["scores"])
            if shooter2_score_count != 4:  # Should have 4 scores: 1 for NMC1, 3 for NMC2
                print(f"❌ Expected 4 scores for shooter 2, found {shooter2_score_count}")
                return False
            
            print("✅ Match report data verified, Excel export should be correct")
            
            # Based on our test setup, we can infer that:
            # 1. The Excel export should show "N/A" for missing scores (e.g., Shooter 1 missing .45 in NMC2)
            # 2. The average calculation should include the 0 score for Shooter 1 in NMC2 CF
            # 3. The average calculation should exclude missing scores
            
            print("\n✅ Excel export test PASSED")
            return True
        else:
            print(f"❌ Failed - Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed - Error: {str(e)}")
        return False

def test_score_editing_functionality(tester):
    """Test the score editing functionality in detail"""
    print("\n===== TESTING SCORE EDITING FUNCTIONALITY =====\n")
    
    # Step 1: Create a shooter for testing
    shooter_success, shooter_response = tester.test_add_shooter()
    if not shooter_success:
        print("❌ Adding shooter failed, cannot continue score editing test")
        return False
    
    shooter_id = tester.shooter_id
    print(f"✅ Created test shooter with ID: {shooter_id}")
    
    # Step 2: Create a match for testing
    match_name = f"Score Editing Test Match {int(time.time())}"
    
    success, response = tester.run_test(
        "Create Match for Score Editing Test",
        "POST",
        "matches",
        200,
        data={
            "name": match_name,
            "date": datetime.now().isoformat(),
            "location": "Test Range for Score Editing",
            "match_types": [
                {
                    "type": "NMC",
                    "instance_name": "NMC1",
                    "calibers": [".22", "CF"]
                }
            ],
            "aggregate_type": "None"
        },
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Creating match failed, cannot continue score editing test")
        return False
    
    match_id = response.get('id')
    print(f"✅ Created match with ID: {match_id}")
    
    # Step 3: Add a score for testing
    score_data = {
        "shooter_id": shooter_id,
        "match_id": match_id,
        "caliber": ".22",
        "match_type_instance": "NMC1",
        "stages": [
            {"name": "SF", "score": 95, "x_count": 3},
            {"name": "TF", "score": 97, "x_count": 4},
            {"name": "RF", "score": 98, "x_count": 5}
        ]
    }
    
    success, score_response = tester.run_test(
        "Add Score for Editing Test",
        "POST",
        "scores",
        200,
        data=score_data,
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Adding score failed, cannot continue score editing test")
        return False
    
    score_id = score_response.get('id')
    print(f"✅ Added score with ID: {score_id}")
    
    # Step 4: Test GET /api/scores/{score_id}
    success, get_response = tester.run_test(
        "Get Score by ID",
        "GET",
        f"scores/{score_id}",
        200,
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Getting score by ID failed")
        return False
    
    # Verify the retrieved score matches what we created
    if get_response.get('id') != score_id:
        print(f"❌ Retrieved score ID mismatch: {get_response.get('id')} != {score_id}")
        return False
    
    if get_response.get('shooter_id') != shooter_id:
        print(f"❌ Retrieved shooter ID mismatch: {get_response.get('shooter_id')} != {shooter_id}")
        return False
    
    if get_response.get('match_id') != match_id:
        print(f"❌ Retrieved match ID mismatch: {get_response.get('match_id')} != {match_id}")
        return False
    
    if get_response.get('caliber') != ".22":
        print(f"❌ Retrieved caliber mismatch: {get_response.get('caliber')} != .22")
        return False
    
    if get_response.get('match_type_instance') != "NMC1":
        print(f"❌ Retrieved match type instance mismatch: {get_response.get('match_type_instance')} != NMC1")
        return False
    
    # Verify total score calculation
    expected_total_score = sum(stage["score"] for stage in score_data["stages"])
    expected_total_x = sum(stage["x_count"] for stage in score_data["stages"])
    
    if get_response.get('total_score') != expected_total_score:
        print(f"❌ Retrieved total score mismatch: {get_response.get('total_score')} != {expected_total_score}")
        return False
    
    if get_response.get('total_x_count') != expected_total_x:
        print(f"❌ Retrieved total X count mismatch: {get_response.get('total_x_count')} != {expected_total_x}")
        return False
    
    print("✅ Successfully retrieved and verified score by ID")
    
    # Step 5: Test PUT /api/scores/{score_id} - Update the score
    updated_score_data = {
        "shooter_id": shooter_id,
        "match_id": match_id,
        "caliber": ".22",
        "match_type_instance": "NMC1",
        "stages": [
            {"name": "SF", "score": 96, "x_count": 4},  # Updated values
            {"name": "TF", "score": 98, "x_count": 5},  # Updated values
            {"name": "RF", "score": 99, "x_count": 6}   # Updated values
        ]
    }
    
    success, update_response = tester.run_test(
        "Update Score",
        "PUT",
        f"scores/{score_id}",
        200,
        data=updated_score_data,
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Updating score failed")
        return False
    
    # Verify the updated score has the correct values
    expected_updated_total = sum(stage["score"] for stage in updated_score_data["stages"])
    expected_updated_x = sum(stage["x_count"] for stage in updated_score_data["stages"])
    
    if update_response.get('total_score') != expected_updated_total:
        print(f"❌ Updated total score mismatch: {update_response.get('total_score')} != {expected_updated_total}")
        return False
    
    if update_response.get('total_x_count') != expected_updated_x:
        print(f"❌ Updated total X count mismatch: {update_response.get('total_x_count')} != {expected_updated_x}")
        return False
    
    print("✅ Successfully updated score")
    
    # Step 6: Verify data persistence by getting the score again
    success, get_updated_response = tester.run_test(
        "Get Updated Score",
        "GET",
        f"scores/{score_id}",
        200,
        token=tester.admin_token
    )
    
    if not success:
        print("❌ Getting updated score failed")
        return False
    
    # Verify the retrieved updated score matches what we updated
    if get_updated_response.get('total_score') != expected_updated_total:
        print(f"❌ Retrieved updated total score mismatch: {get_updated_response.get('total_score')} != {expected_updated_total}")
        return False
    
    if get_updated_response.get('total_x_count') != expected_updated_x:
        print(f"❌ Retrieved updated total X count mismatch: {get_updated_response.get('total_x_count')} != {expected_updated_x}")
        return False
    
    # Verify individual stage scores
    stages = get_updated_response.get('stages', [])
    for i, stage in enumerate(stages):
        expected_stage = updated_score_data["stages"][i]
        if stage.get('name') != expected_stage["name"]:
            print(f"❌ Stage name mismatch: {stage.get('name')} != {expected_stage['name']}")
            return False
        if stage.get('score') != expected_stage["score"]:
            print(f"❌ Stage score mismatch for {stage.get('name')}: {stage.get('score')} != {expected_stage['score']}")
            return False
        if stage.get('x_count') != expected_stage["x_count"]:
            print(f"❌ Stage X count mismatch for {stage.get('name')}: {stage.get('x_count')} != {expected_stage['x_count']}")
            return False
    
    print("✅ Successfully verified data persistence of updated score")
    
    # Step 7: Test authentication requirements - Try to access without a token
    success, _ = tester.run_test(
        "Get Score Without Authentication (should fail)",
        "GET",
        f"scores/{score_id}",
        401,  # Expect 401 Unauthorized
        token=None
    )
    
    if not success:
        print("❌ Authentication test failed - was able to get score without a token")
        return False
    
    print("✅ Authentication requirement verified for GET /api/scores/{score_id}")
    
    success, _ = tester.run_test(
        "Update Score Without Authentication (should fail)",
        "PUT",
        f"scores/{score_id}",
        401,  # Expect 401 Unauthorized
        data=updated_score_data,
        token=None
    )
    
    if not success:
        print("❌ Authentication test failed - was able to update score without a token")
        return False
    
    print("✅ Authentication requirement verified for PUT /api/scores/{score_id}")
    
    # Step 8: Test authorization requirements - Try to update with a reporter role
    # First, register a reporter user
    username = f"reporter_{int(time.time())}"
    email = f"{username}@example.com"
    password = "Test123!"
    
    success, _ = tester.run_test(
        "Register Reporter User",
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
    
    if not success:
        print("❌ Failed to register reporter user, skipping authorization test")
    else:
        # Login with the reporter user
        url = f"{tester.base_url}/api/auth/token"
        data = {
            'username': email,
            'password': password
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                reporter_token = response.json().get('access_token')
                
                # Try to update a score with reporter role (should fail with 403)
                success, _ = tester.run_test(
                    "Update Score with Reporter Role (should fail)",
                    "PUT",
                    f"scores/{score_id}",
                    403,  # Expect 403 Forbidden
                    data=updated_score_data,
                    token=reporter_token
                )
                
                if not success:
                    print("❌ Authorization test failed - reporter was able to update score")
                    return False
                
                print("✅ Authorization requirement verified - reporters cannot update scores")
                
                # Verify reporter can still view scores
                success, _ = tester.run_test(
                    "Get Score with Reporter Role (should succeed)",
                    "GET",
                    f"scores/{score_id}",
                    200,
                    token=reporter_token
                )
                
                if not success:
                    print("❌ Reporter could not view score")
                    return False
                
                print("✅ Authorization requirement verified - reporters can view scores")
            else:
                print(f"❌ Failed to login as reporter user: {response.status_code}")
        except Exception as e:
            print(f"❌ Error during reporter login: {str(e)}")
    
    print("\n✅ Score editing functionality test PASSED")
    return True

def main():
    # Get the backend URL from the environment
    backend_url = "https://ecc4b2e5-4738-47d7-aabd-fec160cafe64.preview.emergentagent.com"
    
    # Setup
    tester = ShootingMatchAPITester(backend_url)
    
    # Run tests
    print("\n===== TESTING SHOOTING MATCH SCORE MANAGEMENT API =====\n")
    
    # Authentication Tests
    admin_login_success, _ = tester.test_admin_login()
    if not admin_login_success:
        print("❌ Admin login failed, stopping tests")
        return 1
    
    # Run the score editing functionality test
    score_editing_test_success = test_score_editing_functionality(tester)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if score_editing_test_success:
        print("\n✅ Score editing functionality is working correctly!")
    else:
        print("\n❌ Score editing functionality has issues!")
    
    return 0 if tester.tests_passed == tester.tests_run and score_editing_test_success else 1

if __name__ == "__main__":
    sys.exit(main())
