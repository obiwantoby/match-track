import requests
import json
import uuid
from datetime import datetime, timedelta
import time
import os
from pprint import pprint

# Get the backend URL from environment or use default
BACKEND_URL = os.environ.get("BACKEND_URL", "https://54bdef35-ae60-4161-ae24-d2c0da9aaead.preview.emergentagent.com")
API_URL = f"{BACKEND_URL}/api"

# Test user credentials
TEST_USER = {
    "email": "test@example.com",
    "username": "testuser",
    "password": "testpassword123",
    "role": "admin"
}

# Global variables to store test data
token = None
user_id = None
match_id = None
shooter_id = None
score_id = None

def print_separator(title):
    """Print a separator with a title for better test output readability"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def register_user():
    """Register a test user"""
    global user_id
    
    print_separator("REGISTERING TEST USER")
    
    # Check if user already exists
    try:
        response = requests.post(
            f"{API_URL}/auth/token",
            data={"username": TEST_USER["email"], "password": TEST_USER["password"]}
        )
        if response.status_code == 200:
            print("User already exists, logging in instead")
            user_data = response.json()
            user_id = user_data["user_id"]
            return login_user()
    except:
        pass
    
    # Register new user
    response = requests.post(
        f"{API_URL}/auth/register",
        json=TEST_USER
    )
    
    if response.status_code == 200:
        user_data = response.json()
        user_id = user_data["id"]
        print(f"User registered successfully with ID: {user_id}")
        return True
    else:
        print(f"Failed to register user: {response.status_code} - {response.text}")
        return False

def login_user():
    """Login the test user and get authentication token"""
    global token
    
    print_separator("LOGGING IN TEST USER")
    
    response = requests.post(
        f"{API_URL}/auth/token",
        data={"username": TEST_USER["email"], "password": TEST_USER["password"]}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data["access_token"]
        print(f"Login successful, token obtained")
        return True
    else:
        print(f"Failed to login: {response.status_code} - {response.text}")
        return False

def create_test_match():
    """Create a test match with multiple stages"""
    global match_id
    
    print_separator("CREATING TEST MATCH")
    
    # Define match data with multiple stages
    match_data = {
        "name": f"All NULL Test Match {datetime.now().strftime('%H%M%S')}",
        "date": datetime.now().isoformat(),
        "location": "Test Range",
        "match_types": [
            {
                "type": "NMC",
                "instance_name": "NMC1",
                "calibers": [".22", "CF", ".45"]
            },
            {
                "type": "600",
                "instance_name": "600_1",
                "calibers": [".22", "CF", ".45"]
            }
        ],
        "aggregate_type": "None"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_URL}/matches",
        json=match_data,
        headers=headers
    )
    
    if response.status_code == 200:
        match_data = response.json()
        match_id = match_data["id"]
        print(f"Match created successfully with ID: {match_id}")
        print(f"Match types: {[mt['instance_name'] for mt in match_data['match_types']]}")
        return True
    else:
        print(f"Failed to create match: {response.status_code} - {response.text}")
        return False

def create_test_shooter():
    """Create a test shooter"""
    global shooter_id
    
    print_separator("CREATING TEST SHOOTER")
    
    shooter_data = {
        "name": f"All NULL Test Shooter {datetime.now().strftime('%H%M%S')}",
        "nra_number": "12345678",
        "cmp_number": "87654321"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_URL}/shooters",
        json=shooter_data,
        headers=headers
    )
    
    if response.status_code == 200:
        shooter_data = response.json()
        shooter_id = shooter_data["id"]
        print(f"Shooter created successfully with ID: {shooter_id}")
        return True
    else:
        print(f"Failed to create shooter: {response.status_code} - {response.text}")
        return False

def create_all_null_scores():
    """Create scores with NULL values for both score and x_count in all stages"""
    global score_id
    
    print_separator("CREATING SCORES WITH ALL NULL VALUES")
    
    # Get match configuration to determine stages
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/match-config/{match_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"Failed to get match configuration: {response.status_code} - {response.text}")
        return False
    
    match_config = response.json()
    
    # Create scores for each match type and caliber with NULL values for all stages
    for match_type in match_config["match_types"]:
        match_type_instance = match_type["instance_name"]
        
        for caliber in match_type["calibers"]:
            print(f"\nCreating score for {match_type_instance} with {caliber} caliber...")
            
            # Create stages with NULL values
            stages = []
            for stage_name in match_type["entry_stages"]:
                stages.append({
                    "name": stage_name,
                    "score": None,
                    "x_count": None
                })
            
            score_data = {
                "shooter_id": shooter_id,
                "match_id": match_id,
                "caliber": caliber,
                "match_type_instance": match_type_instance,
                "stages": stages
            }
            
            response = requests.post(
                f"{API_URL}/scores",
                json=score_data,
                headers=headers
            )
            
            if response.status_code == 200:
                score_data = response.json()
                
                # Save the first score ID for later verification
                if score_id is None:
                    score_id = score_data["id"]
                
                print(f"Score created successfully with ID: {score_data['id']}")
                print(f"  not_shot: {score_data['not_shot']}")
                print(f"  total_score: {score_data['total_score']}")
                print(f"  total_x_count: {score_data['total_x_count']}")
                
                # Verify that the backend correctly marks this as a not_shot score
                if score_data["not_shot"] == True and score_data["total_score"] is None and score_data["total_x_count"] is None:
                    print("✅ Backend correctly marked this as a not_shot score with NULL total_score and total_x_count")
                else:
                    print("❌ Backend did not correctly handle NULL values")
                    return False
            else:
                print(f"Failed to create score: {response.status_code} - {response.text}")
                return False
    
    return True

def verify_score_retrieval():
    """Verify that the score can be retrieved and NULL values are preserved"""
    
    print_separator("VERIFYING SCORE RETRIEVAL")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/scores/{score_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        score_data = response.json()
        print(f"Score retrieved successfully with ID: {score_id}")
        print(f"  not_shot: {score_data['not_shot']}")
        print(f"  total_score: {score_data['total_score']}")
        print(f"  total_x_count: {score_data['total_x_count']}")
        
        # Verify that NULL values are preserved
        if score_data["not_shot"] == True and score_data["total_score"] is None and score_data["total_x_count"] is None:
            print("✅ NULL values are correctly preserved in the retrieved score")
            
            # Verify all stages have NULL values
            all_stages_null = all(stage["score"] is None and stage["x_count"] is None for stage in score_data["stages"])
            if all_stages_null:
                print("✅ All stages correctly have NULL values")
            else:
                print("❌ Some stages do not have NULL values")
                return False
                
            return True
        else:
            print("❌ NULL values are not correctly preserved")
            return False
    else:
        print(f"Failed to retrieve score: {response.status_code} - {response.text}")
        return False

def verify_match_report():
    """Verify the match report API endpoint handles NULL scores correctly"""
    
    print_separator("VERIFYING MATCH REPORT API")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/match-report/{match_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        report_data = response.json()
        print("Match report retrieved successfully")
        
        # Find our shooter and scores
        shooter_data = report_data["shooters"].get(shooter_id)
        if not shooter_data:
            print("❌ Shooter not found in match report")
            return False
        
        # Check all scores for this shooter
        all_scores_correct = True
        for score_key, score_data in shooter_data["scores"].items():
            print(f"\nChecking score for {score_key}:")
            
            # Verify NULL values are preserved in the match report
            if score_data["score"]["total_score"] is None and score_data["score"]["total_x_count"] is None:
                print(f"✅ NULL values are correctly preserved for {score_key}")
                
                # Verify all stages have NULL values
                all_stages_null = all(stage["score"] is None and stage["x_count"] is None for stage in score_data["score"]["stages"])
                if all_stages_null:
                    print(f"✅ All stages correctly have NULL values for {score_key}")
                else:
                    print(f"❌ Some stages do not have NULL values for {score_key}")
                    all_scores_correct = False
            else:
                print(f"❌ NULL values are not correctly preserved for {score_key}")
                all_scores_correct = False
        
        return all_scores_correct
    else:
        print(f"Failed to retrieve match report: {response.status_code} - {response.text}")
        return False

def verify_excel_export():
    """Verify that the Excel export handles NULL scores correctly"""
    
    print_separator("VERIFYING EXCEL EXPORT")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_URL}/match-report/{match_id}/excel",
        headers=headers,
        stream=True
    )
    
    if response.status_code == 200:
        # Save the Excel file
        filename = "all_null_test_export.xlsx"
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        print(f"Excel export downloaded successfully to {filename}")
        print("\nNOTE: Excel file verification requires manual inspection.")
        print("The backend code shows that:")
        print("1. Scores marked as not_shot display 'Not Shot' in red in individual sheets")
        print("2. Total rows for not_shot scores show '-' instead of numbers")
        print("3. The Match Report tab displays '-' for not_shot scores")
        print("4. not_shot scores are excluded from average calculations")
        
        return True
    else:
        print(f"Failed to download Excel export: {response.status_code} - {response.text}")
        return False

def run_tests():
    """Run all tests in sequence"""
    
    # Setup
    if not register_user():
        return False
    
    if not login_user():
        return False
    
    if not create_test_match():
        return False
    
    if not create_test_shooter():
        return False
    
    # Test NULL score handling
    if not create_all_null_scores():
        return False
    
    if not verify_score_retrieval():
        return False
    
    if not verify_match_report():
        return False
    
    if not verify_excel_export():
        return False
    
    print_separator("TEST SUMMARY")
    print("✅ All tests completed successfully!")
    print("\nVerified that:")
    print("1. Scores with NULL values for both score and x_count in all stages are correctly marked as not_shot")
    print("2. Total score and total x_count are set to NULL when all stages are NULL")
    print("3. NULL values are preserved when retrieving scores")
    print("4. Match report API correctly handles scores with all NULL values")
    print("5. Excel export should display scores with all NULL values as 'Not Shot' in individual sheets")
    print("   and '-' in the Match Report tab (requires manual verification)")
    
    return True

if __name__ == "__main__":
    run_tests()