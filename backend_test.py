
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
                        # Check for .22 caliber score
                        key_22 = "900_1_.22"
                        if key_22 not in shooter_data["scores"]:
                            print(f"❌ .22 caliber score not found for shooter")
                            success = False
                        else:
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
                        
                        # Check for CF caliber score
                        key_cf = "900_1_CF"
                        if key_cf not in shooter_data["scores"]:
                            print(f"❌ CF caliber score not found for shooter")
                            success = False
                        else:
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

def main():
    # Get the backend URL from the environment
    backend_url = "https://515d5b7b-c54c-45c0-ac83-eab39da6c866.preview.emergentagent.com"
    
    # Setup
    tester = ShootingMatchAPITester(backend_url)
    
    # Run tests
    print("\n===== TESTING SHOOTING MATCH SCORE MANAGEMENT API =====\n")
    
    # Authentication Tests
    admin_login_success, _ = tester.test_admin_login()
    if not admin_login_success:
        print("❌ Admin login failed, stopping tests")
        return 1
    
    register_success, _ = tester.test_register_user()
    if not register_success:
        print("❌ User registration failed")
    
    user_info_success, _ = tester.test_get_current_user()
    if not user_info_success:
        print("❌ Getting user info failed")
    
    users_success, _ = tester.test_get_users()
    if not users_success:
        print("❌ Getting users failed")
    
    # Shooter Tests
    shooter_success, _ = tester.test_add_shooter()
    if not shooter_success:
        print("❌ Adding shooter failed")
    
    shooters_success, _ = tester.test_get_shooters()
    if not shooters_success:
        print("❌ Getting shooters failed")
    
    if shooter_success:
        shooter_detail_success, _ = tester.test_get_shooter()
        if not shooter_detail_success:
            print("❌ Getting shooter details failed")
    
    # Match Types Test
    match_types_success, match_types_response = tester.test_get_match_types()
    if not match_types_success:
        print("❌ Getting match types failed")
    
    # Match Tests
    match_success, _ = tester.test_add_match()
    if not match_success:
        print("❌ Adding match failed")
    
    # Match with Subtotals Test
    match_with_subtotals_success, _ = tester.test_add_match_with_subtotals()
    if not match_with_subtotals_success:
        print("❌ Adding match with subtotals failed")
    
    matches_success, _ = tester.test_get_matches()
    if not matches_success:
        print("❌ Getting matches failed")
    
    if match_success:
        match_detail_success, _ = tester.test_get_match()
        if not match_detail_success:
            print("❌ Getting match details failed")
        
        match_config_success, _ = tester.test_get_match_config()
        if not match_config_success:
            print("❌ Getting match configuration failed")
    
    if match_with_subtotals_success:
        match_config_with_subtotals_success, _ = tester.test_get_match_config_with_subtotals()
        if not match_config_with_subtotals_success:
            print("❌ Getting match configuration with subtotals failed")
    
    # Score Tests
    if shooter_success and match_success:
        score_success, _ = tester.test_add_score()
        if not score_success:
            print("❌ Adding score failed")
        
        if score_success:
            scores_success, _ = tester.test_get_scores()
            if not scores_success:
                print("❌ Getting scores failed")
            
            score_detail_success, _ = tester.test_get_score()
            if not score_detail_success:
                print("❌ Getting score details failed")
            
            scores_by_match_success, _ = tester.test_get_scores_by_match()
            if not scores_by_match_success:
                print("❌ Getting scores by match failed")
            
            scores_by_shooter_success, _ = tester.test_get_scores_by_shooter()
            if not scores_by_shooter_success:
                print("❌ Getting scores by shooter failed")
            
            update_score_success, _ = tester.test_update_score()
            if not update_score_success:
                print("❌ Updating score failed")
    
    # Score with Subtotals Test
    if shooter_success and match_with_subtotals_success:
        score_with_subtotals_success, _ = tester.test_add_score_with_subtotals()
        if not score_with_subtotals_success:
            print("❌ Adding score with subtotals failed")
    
    # Report Tests
    if match_success:
        match_report_success, _ = tester.test_view_match_report()
        if not match_report_success:
            print("❌ Viewing match report failed")
    
    # Report with Subtotals Test
    if match_with_subtotals_success and shooter_success and hasattr(tester, 'score_id_with_subtotals_22'):
        match_report_with_subtotals_success, _ = tester.test_view_match_report_with_subtotals()
        if not match_report_with_subtotals_success:
            print("❌ Viewing match report with subtotals failed")
    
    if shooter_success:
        shooter_report_success, _ = tester.test_view_shooter_report()
        if not shooter_report_success:
            print("❌ Viewing shooter report failed")
        
        shooter_averages_success, _ = tester.test_view_shooter_averages()
        if not shooter_averages_success:
            print("❌ Viewing shooter averages failed")
    
    # Permission Tests
    if register_success:
        permissions_success, _ = tester.test_reporter_permissions()
        if not permissions_success:
            print("❌ Reporter permissions test failed")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
