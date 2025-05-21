import requests
import json
from datetime import datetime, timedelta

def test_900pt_aggregate_match():
    """
    Test the 900pt Aggregate match type functionality with focus on:
    1. Score entry for the 900 match type
    2. Automatic calculation of subtotals (SFNMC, TFNMC, RFNMC)
    3. Match report showing the calculated subtotals
    """
    # Backend URL from frontend/.env
    base_url = "https://b78bc624-fd3d-457d-a921-b3684a7c6c0b.preview.emergentagent.com/api"
    headers = {"Content-Type": "application/json"}
    
    print("\n===== TESTING 900PT AGGREGATE MATCH FUNCTIONALITY =====\n")
    
    # Step 1: Login with admin credentials
    print("Step 1: Logging in with admin credentials...")
    login_data = {
        "username": "admin@example.com",
        "password": "admin123"
    }
    
    response = requests.post(
        f"{base_url}/auth/token",
        data=login_data
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return False
    
    token_data = response.json()
    auth_token = token_data["access_token"]
    headers["Authorization"] = f"Bearer {auth_token}"
    print("✅ Successfully logged in as admin")
    
    # Step 2: Create a shooter
    print("\nStep 2: Creating a test shooter...")
    shooter_data = {
        "name": f"Test Shooter 900pt {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "nra_number": "12345678",
        "cmp_number": "87654321"
    }
    
    response = requests.post(
        f"{base_url}/shooters",
        headers=headers,
        json=shooter_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create shooter: {response.text}")
        return False
    
    shooter = response.json()
    shooter_id = shooter["id"]
    print(f"✅ Created shooter with ID: {shooter_id}")
    
    # Step 3: Create a match with 900pt Aggregate match type
    print("\nStep 3: Creating a 900pt Aggregate match...")
    match_date = (datetime.now() + timedelta(days=7)).isoformat()
    match_data = {
        "name": f"Test 900pt Aggregate Match {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "date": match_date,
        "location": "Test Range",
        "match_types": [
            {
                "type": "900",
                "instance_name": "900_Test",
                "calibers": [".22", "CF", ".45"]
            }
        ],
        "aggregate_type": "None"
    }
    
    response = requests.post(
        f"{base_url}/matches",
        headers=headers,
        json=match_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create match: {response.text}")
        return False
    
    match = response.json()
    match_id = match["id"]
    print(f"✅ Created match with ID: {match_id}")
    
    # Step 4: Verify match configuration
    print("\nStep 4: Verifying match configuration...")
    response = requests.get(
        f"{base_url}/match-config/{match_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get match config: {response.text}")
        return False
    
    match_config = response.json()
    
    # Verify the match has the correct entry stages and subtotal mappings
    match_type_config = match_config["match_types"][0]
    
    # Check match type
    if match_type_config["type"] != "900":
        print(f"❌ Match type should be 900, got {match_type_config['type']}")
        return False
    
    # Check entry stages
    expected_entry_stages = ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2"]
    if match_type_config["entry_stages"] != expected_entry_stages:
        print(f"❌ Entry stages should be {expected_entry_stages}, got {match_type_config['entry_stages']}")
        return False
    
    # Check subtotal stages
    expected_subtotal_stages = ["SFNMC", "TFNMC", "RFNMC"]
    if match_type_config["subtotal_stages"] != expected_subtotal_stages:
        print(f"❌ Subtotal stages should be {expected_subtotal_stages}, got {match_type_config['subtotal_stages']}")
        return False
    
    # Check subtotal mappings
    expected_mappings = {
        "SFNMC": ["SF1", "SF2"],
        "TFNMC": ["TF1", "TF2"],
        "RFNMC": ["RF1", "RF2"]
    }
    
    for subtotal, stages in expected_mappings.items():
        if subtotal not in match_type_config["subtotal_mappings"]:
            print(f"❌ Subtotal {subtotal} missing from subtotal_mappings")
            return False
        if set(match_type_config["subtotal_mappings"][subtotal]) != set(stages):
            print(f"❌ Incorrect mapping for {subtotal}: {match_type_config['subtotal_mappings'][subtotal]}")
            return False
    
    print("✅ Match configuration verified successfully")
    
    # Step 5: Submit scores for the 900pt match with .22 caliber
    print("\nStep 5: Submitting scores for the 900pt match with .22 caliber...")
    score_data = {
        "shooter_id": shooter_id,
        "match_id": match_id,
        "caliber": ".22",
        "match_type_instance": "900_Test",
        "stages": [
            {"name": "SF1", "score": 95, "x_count": 3},
            {"name": "SF2", "score": 97, "x_count": 5},
            {"name": "TF1", "score": 98, "x_count": 6},
            {"name": "TF2", "score": 96, "x_count": 4},
            {"name": "RF1", "score": 94, "x_count": 2},
            {"name": "RF2", "score": 93, "x_count": 1}
        ]
    }
    
    response = requests.post(
        f"{base_url}/scores",
        headers=headers,
        json=score_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to submit scores: {response.text}")
        return False
    
    score_result = response.json()
    
    # Verify the total score is calculated correctly
    expected_total_score = sum(stage["score"] for stage in score_data["stages"])
    expected_total_x_count = sum(stage["x_count"] for stage in score_data["stages"])
    
    if score_result["total_score"] != expected_total_score:
        print(f"❌ Total score should be {expected_total_score}, got {score_result['total_score']}")
        return False
    
    if score_result["total_x_count"] != expected_total_x_count:
        print(f"❌ Total X count should be {expected_total_x_count}, got {score_result['total_x_count']}")
        return False
    
    print(f"✅ Score submitted successfully with total: {score_result['total_score']} and X count: {score_result['total_x_count']}")
    
    # Step 6: Submit scores for the 900pt match with CF caliber
    print("\nStep 6: Submitting scores for the 900pt match with CF caliber...")
    score_data_cf = {
        "shooter_id": shooter_id,
        "match_id": match_id,
        "caliber": "CF",
        "match_type_instance": "900_Test",
        "stages": [
            {"name": "SF1", "score": 94, "x_count": 2},
            {"name": "SF2", "score": 96, "x_count": 4},
            {"name": "TF1", "score": 97, "x_count": 5},
            {"name": "TF2", "score": 95, "x_count": 3},
            {"name": "RF1", "score": 93, "x_count": 1},
            {"name": "RF2", "score": 92, "x_count": 0}
        ]
    }
    
    response = requests.post(
        f"{base_url}/scores",
        headers=headers,
        json=score_data_cf
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to submit CF scores: {response.text}")
        return False
    
    score_result_cf = response.json()
    
    # Verify the total score is calculated correctly
    expected_total_score_cf = sum(stage["score"] for stage in score_data_cf["stages"])
    expected_total_x_count_cf = sum(stage["x_count"] for stage in score_data_cf["stages"])
    
    if score_result_cf["total_score"] != expected_total_score_cf:
        print(f"❌ CF Total score should be {expected_total_score_cf}, got {score_result_cf['total_score']}")
        return False
    
    if score_result_cf["total_x_count"] != expected_total_x_count_cf:
        print(f"❌ CF Total X count should be {expected_total_x_count_cf}, got {score_result_cf['total_x_count']}")
        return False
    
    print(f"✅ CF Score submitted successfully with total: {score_result_cf['total_score']} and X count: {score_result_cf['total_x_count']}")
    
    # Step 7: Check the match report for correct subtotal calculations
    print("\nStep 7: Checking match report for correct subtotal calculations...")
    response = requests.get(
        f"{base_url}/match-report/{match_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get match report: {response.text}")
        return False
    
    match_report = response.json()
    
    # Verify the shooter is in the report
    if shooter_id not in match_report["shooters"]:
        print(f"❌ Shooter {shooter_id} should be in the match report")
        return False
    
    # Get the shooter's scores
    shooter_scores = match_report["shooters"][shooter_id]["scores"]
    
    # Print all available score keys for debugging
    score_keys = list(shooter_scores.keys())
    print(f"Available score keys: {score_keys}")
    
    # Find the .22 caliber score key
    key_22 = None
    for key in score_keys:
        if "900_Test" in key and "TWENTYTWO" in key:
            key_22 = key
            break
    
    if not key_22:
        print(f"❌ .22 caliber score not found for shooter")
        return False
    
    print(f"Found .22 caliber score with key: {key_22}")
    
    # Verify subtotals for .22 caliber
    subtotals_22 = shooter_scores[key_22]["subtotals"]
    
    # Check SFNMC subtotal
    if "SFNMC" not in subtotals_22:
        print(f"❌ SFNMC subtotal not found in .22 caliber score")
        return False
    
    expected_sfnmc_score = score_data["stages"][0]["score"] + score_data["stages"][1]["score"]
    expected_sfnmc_x_count = score_data["stages"][0]["x_count"] + score_data["stages"][1]["x_count"]
    
    if subtotals_22["SFNMC"]["score"] != expected_sfnmc_score:
        print(f"❌ SFNMC score should be {expected_sfnmc_score}, got {subtotals_22['SFNMC']['score']}")
        return False
    
    if subtotals_22["SFNMC"]["x_count"] != expected_sfnmc_x_count:
        print(f"❌ SFNMC X count should be {expected_sfnmc_x_count}, got {subtotals_22['SFNMC']['x_count']}")
        return False
    
    print(f"✅ SFNMC subtotal verified: Score={subtotals_22['SFNMC']['score']}, X-count={subtotals_22['SFNMC']['x_count']}")
    
    # Check TFNMC subtotal
    if "TFNMC" not in subtotals_22:
        print(f"❌ TFNMC subtotal not found in .22 caliber score")
        return False
    
    expected_tfnmc_score = score_data["stages"][2]["score"] + score_data["stages"][3]["score"]
    expected_tfnmc_x_count = score_data["stages"][2]["x_count"] + score_data["stages"][3]["x_count"]
    
    if subtotals_22["TFNMC"]["score"] != expected_tfnmc_score:
        print(f"❌ TFNMC score should be {expected_tfnmc_score}, got {subtotals_22['TFNMC']['score']}")
        return False
    
    if subtotals_22["TFNMC"]["x_count"] != expected_tfnmc_x_count:
        print(f"❌ TFNMC X count should be {expected_tfnmc_x_count}, got {subtotals_22['TFNMC']['x_count']}")
        return False
    
    print(f"✅ TFNMC subtotal verified: Score={subtotals_22['TFNMC']['score']}, X-count={subtotals_22['TFNMC']['x_count']}")
    
    # Check RFNMC subtotal
    if "RFNMC" not in subtotals_22:
        print(f"❌ RFNMC subtotal not found in .22 caliber score")
        return False
    
    expected_rfnmc_score = score_data["stages"][4]["score"] + score_data["stages"][5]["score"]
    expected_rfnmc_x_count = score_data["stages"][4]["x_count"] + score_data["stages"][5]["x_count"]
    
    if subtotals_22["RFNMC"]["score"] != expected_rfnmc_score:
        print(f"❌ RFNMC score should be {expected_rfnmc_score}, got {subtotals_22['RFNMC']['score']}")
        return False
    
    if subtotals_22["RFNMC"]["x_count"] != expected_rfnmc_x_count:
        print(f"❌ RFNMC X count should be {expected_rfnmc_x_count}, got {subtotals_22['RFNMC']['x_count']}")
        return False
    
    print(f"✅ RFNMC subtotal verified: Score={subtotals_22['RFNMC']['score']}, X-count={subtotals_22['RFNMC']['x_count']}")
    
    # Find the CF caliber score key
    key_cf = None
    for key in score_keys:
        if "900_Test" in key and "CENTERFIRE" in key:
            key_cf = key
            break
    
    if not key_cf:
        print(f"❌ CF caliber score not found for shooter")
        return False
    
    print(f"Found CF caliber score with key: {key_cf}")
    
    # Verify subtotals for CF caliber
    subtotals_cf = shooter_scores[key_cf]["subtotals"]
    
    # Check SFNMC subtotal for CF
    if "SFNMC" not in subtotals_cf:
        print(f"❌ SFNMC subtotal not found in CF caliber score")
        return False
    
    expected_sfnmc_score_cf = score_data_cf["stages"][0]["score"] + score_data_cf["stages"][1]["score"]
    expected_sfnmc_x_count_cf = score_data_cf["stages"][0]["x_count"] + score_data_cf["stages"][1]["x_count"]
    
    if subtotals_cf["SFNMC"]["score"] != expected_sfnmc_score_cf:
        print(f"❌ CF SFNMC score should be {expected_sfnmc_score_cf}, got {subtotals_cf['SFNMC']['score']}")
        return False
    
    if subtotals_cf["SFNMC"]["x_count"] != expected_sfnmc_x_count_cf:
        print(f"❌ CF SFNMC X count should be {expected_sfnmc_x_count_cf}, got {subtotals_cf['SFNMC']['x_count']}")
        return False
    
    print(f"✅ CF SFNMC subtotal verified: Score={subtotals_cf['SFNMC']['score']}, X-count={subtotals_cf['SFNMC']['x_count']}")
    
    # Check TFNMC subtotal for CF
    if "TFNMC" not in subtotals_cf:
        print(f"❌ TFNMC subtotal not found in CF caliber score")
        return False
    
    expected_tfnmc_score_cf = score_data_cf["stages"][2]["score"] + score_data_cf["stages"][3]["score"]
    expected_tfnmc_x_count_cf = score_data_cf["stages"][2]["x_count"] + score_data_cf["stages"][3]["x_count"]
    
    if subtotals_cf["TFNMC"]["score"] != expected_tfnmc_score_cf:
        print(f"❌ CF TFNMC score should be {expected_tfnmc_score_cf}, got {subtotals_cf['TFNMC']['score']}")
        return False
    
    if subtotals_cf["TFNMC"]["x_count"] != expected_tfnmc_x_count_cf:
        print(f"❌ CF TFNMC X count should be {expected_tfnmc_x_count_cf}, got {subtotals_cf['TFNMC']['x_count']}")
        return False
    
    print(f"✅ CF TFNMC subtotal verified: Score={subtotals_cf['TFNMC']['score']}, X-count={subtotals_cf['TFNMC']['x_count']}")
    
    # Check RFNMC subtotal for CF
    if "RFNMC" not in subtotals_cf:
        print(f"❌ RFNMC subtotal not found in CF caliber score")
        return False
    
    expected_rfnmc_score_cf = score_data_cf["stages"][4]["score"] + score_data_cf["stages"][5]["score"]
    expected_rfnmc_x_count_cf = score_data_cf["stages"][4]["x_count"] + score_data_cf["stages"][5]["x_count"]
    
    if subtotals_cf["RFNMC"]["score"] != expected_rfnmc_score_cf:
        print(f"❌ CF RFNMC score should be {expected_rfnmc_score_cf}, got {subtotals_cf['RFNMC']['score']}")
        return False
    
    if subtotals_cf["RFNMC"]["x_count"] != expected_rfnmc_x_count_cf:
        print(f"❌ CF RFNMC X count should be {expected_rfnmc_x_count_cf}, got {subtotals_cf['RFNMC']['x_count']}")
        return False
    
    print(f"✅ CF RFNMC subtotal verified: Score={subtotals_cf['RFNMC']['score']}, X-count={subtotals_cf['RFNMC']['x_count']}")
    
    print("\n✅ All 900pt Aggregate match tests passed successfully!")
    return True

if __name__ == "__main__":
    test_900pt_aggregate_match()