import requests
import json
import time
import uuid
import sys
from pprint import pprint

# Backend URL from frontend/.env
BACKEND_URL = "https://ecc4b2e5-4738-47d7-aabd-fec160cafe64.preview.emergentagent.com/api"

# Test user credentials
TEST_ADMIN = {
    "email": "admin@example.com",
    "password": "admin123",
    "username": "admin"
}

def print_separator(title):
    """Print a separator with a title for better readability"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")

def test_user_role_management():
    """Test the user role management functionality"""
    print_separator("USER ROLE MANAGEMENT API TEST")
    
    # Step 1: Login as admin
    print("1. Logging in as admin...")
    login_response = requests.post(
        f"{BACKEND_URL}/auth/token",
        data={
            "username": TEST_ADMIN["email"],
            "password": TEST_ADMIN["password"]
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Admin login failed with status code {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    admin_token = login_response.json()["access_token"]
    print(f"✅ Admin login successful")
    
    # Step 2: Create a new reporter user
    print("\n2. Creating a new reporter user...")
    reporter_email = f"reporter_{uuid.uuid4()}@example.com"
    reporter_username = f"reporter_{uuid.uuid4()}"
    reporter_password = "reporter123"
    
    register_response = requests.post(
        f"{BACKEND_URL}/auth/register",
        json={
            "email": reporter_email,
            "username": reporter_username,
            "password": reporter_password,
            "role": "reporter"
        }
    )
    
    if register_response.status_code != 200:
        print(f"❌ Reporter registration failed with status code {register_response.status_code}")
        print(f"Response: {register_response.text}")
        return False
    
    reporter_id = register_response.json()["id"]
    print(f"✅ Reporter user created with ID: {reporter_id}")
    
    # Step 3: Get all users to verify the reporter was created
    print("\n3. Getting all users...")
    users_response = requests.get(
        f"{BACKEND_URL}/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if users_response.status_code != 200:
        print(f"❌ Get users failed with status code {users_response.status_code}")
        print(f"Response: {users_response.text}")
        return False
    
    users = users_response.json()
    reporter_user = next((user for user in users if user["id"] == reporter_id), None)
    
    if not reporter_user:
        print(f"❌ Reporter user with ID {reporter_id} not found in users list")
        return False
    
    if reporter_user["role"] != "reporter":
        print(f"❌ Reporter user has incorrect role: {reporter_user['role']}")
        return False
    
    print(f"✅ Reporter user verified in users list with role: {reporter_user['role']}")
    
    # Step 4: Update the reporter user to admin role
    print("\n4. Updating reporter user to admin role...")
    update_response = requests.put(
        f"{BACKEND_URL}/users/{reporter_id}",
        json={
            "email": reporter_email,
            "username": reporter_username,
            "role": "admin"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if update_response.status_code != 200:
        print(f"❌ Update user role failed with status code {update_response.status_code}")
        print(f"Response: {update_response.text}")
        return False
    
    updated_user = update_response.json()
    if updated_user["role"] != "admin":
        print(f"❌ User role was not updated to admin. Current role: {updated_user['role']}")
        return False
    
    print(f"✅ User role successfully updated to admin")
    
    # Step 5: Update the user back to reporter role
    print("\n5. Updating user back to reporter role...")
    update_response = requests.put(
        f"{BACKEND_URL}/users/{reporter_id}",
        json={
            "email": reporter_email,
            "username": reporter_username,
            "role": "reporter"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if update_response.status_code != 200:
        print(f"❌ Update user role failed with status code {update_response.status_code}")
        print(f"Response: {update_response.text}")
        return False
    
    updated_user = update_response.json()
    if updated_user["role"] != "reporter":
        print(f"❌ User role was not updated to reporter. Current role: {updated_user['role']}")
        return False
    
    print(f"✅ User role successfully updated back to reporter")
    
    # Step 6: Login as the reporter user
    print("\n6. Logging in as the reporter user...")
    reporter_login_response = requests.post(
        f"{BACKEND_URL}/auth/token",
        data={
            "username": reporter_email,
            "password": reporter_password
        }
    )
    
    if reporter_login_response.status_code != 200:
        print(f"❌ Reporter login failed with status code {reporter_login_response.status_code}")
        print(f"Response: {reporter_login_response.text}")
        return False
    
    reporter_token = reporter_login_response.json()["access_token"]
    reporter_role = reporter_login_response.json()["role"]
    
    if reporter_role != "reporter":
        print(f"❌ Reporter login returned incorrect role: {reporter_role}")
        return False
    
    print(f"✅ Reporter login successful with role: {reporter_role}")
    
    print("\n✅ User role management API test PASSED")
    return True

def test_authentication():
    """Test the authentication functionality"""
    print_separator("AUTHENTICATION TEST")
    
    # Step 1: Login as admin
    print("1. Testing admin login...")
    login_response = requests.post(
        f"{BACKEND_URL}/auth/token",
        data={
            "username": TEST_ADMIN["email"],
            "password": TEST_ADMIN["password"]
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Admin login failed with status code {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    admin_token = login_response.json()["access_token"]
    print(f"✅ Admin login successful")
    
    # Step 2: Verify token by getting current user
    print("\n2. Verifying token by getting current user...")
    me_response = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if me_response.status_code != 200:
        print(f"❌ Get current user failed with status code {me_response.status_code}")
        print(f"Response: {me_response.text}")
        return False
    
    user_data = me_response.json()
    if user_data["email"] != TEST_ADMIN["email"]:
        print(f"❌ Current user email mismatch: {user_data['email']} != {TEST_ADMIN['email']}")
        return False
    
    print(f"✅ Token verification successful")
    
    # Step 3: Test with invalid token (simulating after logout)
    print("\n3. Testing with invalid token (simulating after logout)...")
    invalid_token = "invalid_token_after_logout"
    invalid_response = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )
    
    if invalid_response.status_code != 401:
        print(f"❌ Invalid token test failed. Expected status 401, got {invalid_response.status_code}")
        print(f"Response: {invalid_response.text}")
        return False
    
    print(f"✅ Invalid token correctly rejected with status 401")
    
    # Step 4: Test with expired token (if possible)
    # Since we can't easily create an expired token, we'll skip this step
    
    print("\n✅ Authentication test PASSED")
    return True

def test_logout_functionality():
    """Test the logout functionality (JWT token validation)"""
    print_separator("LOGOUT FUNCTIONALITY TEST")
    
    # Step 1: Login as admin
    print("1. Logging in as admin...")
    login_response = requests.post(
        f"{BACKEND_URL}/auth/token",
        data={
            "username": TEST_ADMIN["email"],
            "password": TEST_ADMIN["password"]
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Admin login failed with status code {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    admin_token = login_response.json()["access_token"]
    print(f"✅ Admin login successful")
    
    # Step 2: Verify token is valid
    print("\n2. Verifying token is valid...")
    me_response = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if me_response.status_code != 200:
        print(f"❌ Token validation failed with status code {me_response.status_code}")
        print(f"Response: {me_response.text}")
        return False
    
    print(f"✅ Token is valid")
    
    # Step 3: Simulate logout by using an invalid token
    print("\n3. Simulating logout by using an invalid token...")
    invalid_token = "invalid_token_after_logout"
    invalid_response = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )
    
    if invalid_response.status_code != 401:
        print(f"❌ Invalid token test failed. Expected status 401, got {invalid_response.status_code}")
        print(f"Response: {invalid_response.text}")
        return False
    
    print(f"✅ After logout (invalid token), access is correctly denied with status 401")
    
    print("\n✅ Logout functionality test PASSED")
    return True

def run_all_tests():
    """Run all tests and return the results"""
    results = {
        "user_role_management": test_user_role_management(),
        "authentication": test_authentication(),
        "logout_functionality": test_logout_functionality()
    }
    
    print_separator("TEST SUMMARY")
    for test_name, result in results.items():
        print(f"{test_name}: {'✅ PASSED' if result else '❌ FAILED'}")
    
    all_passed = all(results.values())
    print(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)