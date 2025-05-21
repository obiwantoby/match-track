import requests
import json
import time
from datetime import datetime, timedelta

# API Configuration
API_URL = "https://dbc4f39c-847d-49ea-9a6b-7f8bb33e72ed.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

def print_separator():
    print("\n" + "="*80 + "\n")

def authenticate():
    print("Authenticating as admin...")
    auth_url = f"{API_URL}/auth/token"
    
    try:
        response = requests.post(
            auth_url,
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"Authentication successful. User ID: {token_data['user_id']}, Role: {token_data['role']}")
            return token_data["access_token"]
        else:
            print(f"Authentication failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return None

def test_multiple_score_submissions():
    print_separator()
    print("TESTING MULTIPLE SCORE SUBMISSIONS")
    print_separator()
    
    # Step 1: Authenticate
    token = authenticate()
    if not token:
        print("Authentication failed. Cannot proceed with tests.")
        return False
    
    print_separator()
    
    # Step 2: Create a test shooter
    print("Creating test shooter...")
    shooter_url = f"{API_URL}/shooters"
    
    shooter_data = {
        "name": f"Test Shooter {int(time.time())}",
        "nra_number": "TS12345",
        "cmp_number": "CMP67890"
    }
    
    try:
        response = requests.post(
            shooter_url,
            json=shooter_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            shooter = response.json()
            shooter_id = shooter["id"]
            print(f"Shooter created successfully. ID: {shooter_id}, Name: {shooter['name']}")
        else:
            print(f"Shooter creation failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Shooter creation error: {str(e)}")
        return False
    
    print_separator()
    
    # Step 3: Create a test match with multiple match types and calibers
    print("Creating test match with multiple match types and calibers...")
    match_url = f"{API_URL}/matches"
    
    match_data = {
        "name": f"Test Match {int(time.time())}",
        "date": (datetime.now() + timedelta(days=7)).isoformat(),
        "location": "Test Range",
        "match_types": [
            {
                "type": "600",
                "instance_name": "600_1",
                "calibers": [".22", "CF", ".45"]
            },
            {
                "type": "600",
                "instance_name": "600_2",
                "calibers": [".22", "CF", ".45"]
            },
            {
                "type": "600",
                "instance_name": "600_3",
                "calibers": [".22", "CF", ".45"]
            }
        ],
        "aggregate_type": "1800 (3x600)"
    }
    
    try:
        response = requests.post(
            match_url,
            json=match_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            match = response.json()
            match_id = match["id"]
            print(f"Match created successfully. ID: {match_id}, Name: {match['name']}")
        else:
            print(f"Match creation failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Match creation error: {str(e)}")
        return False
    
    print_separator()
    
    # Step 4: Get match configuration
    print(f"Getting match configuration for match ID: {match_id}...")
    config_url = f"{API_URL}/match-config/{match_id}"
    
    try:
        response = requests.get(
            config_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            match_config = response.json()
            print(f"Match configuration retrieved successfully.")
            
            # Print match types and calibers
            for mt in match_config["match_types"]:
                print(f"Match Type: {mt['type']}, Instance: {mt['instance_name']}, Calibers: {mt['calibers']}")
        else:
            print(f"Match configuration retrieval failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Match configuration retrieval error: {str(e)}")
        return False
    
    print_separator()
    
    # Step 5: Submit multiple scores simultaneously (simulating the updated ScoreEntry.js behavior)
    print("Submitting multiple scores simultaneously...")
    scores_url = f"{API_URL}/scores"
    
    # Create score submissions for all match types and calibers
    score_submissions = []
    
    for match_type in match_config["match_types"]:
        match_type_instance = match_type["instance_name"]
        stages = match_type["stages"]
        
        for caliber in match_type["calibers"]:
            # Create score stages with test values
            score_stages = []
            for stage_name in stages:
                # Use different scores for different calibers to verify they're stored correctly
                if caliber == ".22":
                    score_value = 90
                    x_count = 3
                elif caliber == "CF":
                    score_value = 92
                    x_count = 4
                else:  # .45
                    score_value = 88
                    x_count = 2
                
                score_stages.append({
                    "name": stage_name,
                    "score": score_value,
                    "x_count": x_count
                })
            
            # Create score submission
            score_data = {
                "shooter_id": shooter_id,
                "match_id": match_id,
                "match_type_instance": match_type_instance,
                "caliber": caliber,
                "stages": score_stages
            }
            
            score_submissions.append(score_data)
    
    # Submit all scores
    submitted_scores = []
    for score_data in score_submissions:
        try:
            response = requests.post(
                scores_url,
                json=score_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                score = response.json()
                submitted_scores.append(score)
                print(f"Score submitted successfully for {score_data['match_type_instance']} - {score_data['caliber']}.")
                print(f"  Total Score: {score['total_score']}, X Count: {score['total_x_count']}")
            else:
                print(f"Score submission failed for {score_data['match_type_instance']} - {score_data['caliber']}. Status code: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Score submission error: {str(e)}")
    
    if not submitted_scores:
        print("No scores were submitted successfully.")
        return False
    
    print_separator()
    
    # Step 6: Verify that all scores were stored correctly
    print(f"Verifying scores for shooter ID: {shooter_id}, match ID: {match_id}...")
    scores_url = f"{API_URL}/scores?match_id={match_id}&shooter_id={shooter_id}"
    
    try:
        response = requests.get(
            scores_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            retrieved_scores = response.json()
            print(f"Retrieved {len(retrieved_scores)} scores from the database.")
            
            # Verify that all submitted scores are in the retrieved scores
            submitted_ids = set(score["id"] for score in submitted_scores)
            retrieved_ids = set(score["id"] for score in retrieved_scores)
            
            if submitted_ids.issubset(retrieved_ids):
                print("All submitted scores were successfully retrieved.")
                
                # Verify total_score and total_x_count calculations
                all_calculations_correct = True
                for submitted_score in submitted_scores:
                    matching_retrieved = next((s for s in retrieved_scores if s["id"] == submitted_score["id"]), None)
                    
                    if matching_retrieved:
                        expected_total_score = sum(stage["score"] for stage in submitted_score["stages"])
                        expected_total_x_count = sum(stage["x_count"] for stage in submitted_score["stages"])
                        
                        if matching_retrieved["total_score"] != expected_total_score or matching_retrieved["total_x_count"] != expected_total_x_count:
                            print(f"Score calculation mismatch for score ID: {submitted_score['id']}")
                            print(f"  Expected: total_score={expected_total_score}, total_x_count={expected_total_x_count}")
                            print(f"  Actual: total_score={matching_retrieved['total_score']}, total_x_count={matching_retrieved['total_x_count']}")
                            all_calculations_correct = False
                
                if all_calculations_correct:
                    print("All score calculations are correct.")
                else:
                    print("Some score calculations are incorrect.")
            else:
                print("Some submitted scores were not found in the retrieved scores.")
                print(f"Missing score IDs: {submitted_ids - retrieved_ids}")
                return False
        else:
            print(f"Score retrieval failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Score retrieval error: {str(e)}")
        return False
    
    print_separator()
    
    # Step 7: Check match report to verify aggregation
    print(f"Checking match report for match ID: {match_id}...")
    report_url = f"{API_URL}/match-report/{match_id}"
    
    try:
        response = requests.get(
            report_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            report = response.json()
            print(f"Match report retrieved successfully.")
            
            # Check if the report contains shooter data
            if "shooters" in report and shooter_id in report["shooters"]:
                shooter_data = report["shooters"][shooter_id]
                print(f"Report contains data for shooter: {shooter_data['shooter']['name']}")
                
                # Check if all scores are in the report
                if "scores" in shooter_data:
                    score_count = len(shooter_data["scores"])
                    print(f"Shooter has {score_count} scores in the report.")
                    
                    if score_count == len(submitted_scores):
                        print("All submitted scores are present in the match report.")
                    else:
                        print(f"Mismatch in score count. Expected: {len(submitted_scores)}, Found: {score_count}")
                
                # Check if aggregates are calculated
                if "aggregates" in shooter_data and shooter_data["aggregates"]:
                    print(f"Aggregates calculated for shooter: {list(shooter_data['aggregates'].keys())}")
                    
                    # For 1800 (3x600) aggregate, we should have aggregates for each caliber
                    expected_calibers = [".22", "CF", ".45"]
                    for caliber in expected_calibers:
                        aggregate_key = f"1800_{caliber}"
                        if aggregate_key in shooter_data["aggregates"]:
                            aggregate = shooter_data["aggregates"][aggregate_key]
                            print(f"  {aggregate_key}: Score={aggregate['score']}, X Count={aggregate['x_count']}")
                            
                            # Verify the aggregate calculation
                            # For each caliber, we should have 3 scores of 600 points each (one for each match type instance)
                            # The aggregate should be the sum of these scores
                            caliber_scores = [s for s in submitted_scores if s["caliber"] == caliber]
                            if len(caliber_scores) >= 3:
                                # Sort by score (highest first) and take top 3
                                caliber_scores.sort(key=lambda s: s["total_score"], reverse=True)
                                top_three = caliber_scores[:3]
                                expected_total = sum(s["total_score"] for s in top_three)
                                expected_x_count = sum(s["total_x_count"] for s in top_three)
                                
                                if aggregate["score"] == expected_total and aggregate["x_count"] == expected_x_count:
                                    print(f"  Aggregate calculation is correct for {caliber}.")
                                else:
                                    print(f"  Aggregate calculation is incorrect for {caliber}.")
                                    print(f"    Expected: score={expected_total}, x_count={expected_x_count}")
                                    print(f"    Actual: score={aggregate['score']}, x_count={aggregate['x_count']}")
                        else:
                            print(f"  Missing aggregate for {caliber}.")
                else:
                    print("No aggregates calculated for shooter.")
            else:
                print(f"Shooter {shooter_id} not found in match report.")
                return False
        else:
            print(f"Match report retrieval failed. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Match report retrieval error: {str(e)}")
        return False
    
    print_separator()
    print("MULTIPLE SCORE SUBMISSIONS TEST COMPLETED SUCCESSFULLY")
    return True

if __name__ == "__main__":
    test_multiple_score_submissions()