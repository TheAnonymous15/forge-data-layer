#!/usr/bin/env python3
"""
ForgeForth Africa - API Service Access Request Pipeline Test
============================================================
Tests the full pipeline:
1. Create access request
2. Approve access request (creates user with default password)
3. Login (requires password change)
4. Change password (sends password changed email)
5. Login with new password
"""
import os
import sys
import json
import django
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Configuration
DATA_LAYER_URL = os.getenv('DATA_LAYER_URL', 'http://localhost:9005')
API_SERVICE_URL = os.getenv('API_SERVICE_URL', 'http://localhost:9001')
TEST_EMAIL = 'daniel.kinyua@tutamail.com'
TEST_NAME = 'Daniel Kinyua'
NEW_PASSWORD = 'SecurePass2026!'

def print_header(step, title):
    print(f"\n{'='*60}")
    print(f"[Step {step}] {title}")
    print('='*60)

def print_result(success, message):
    icon = "✓ PASS" if success else "✗ FAIL"
    print(f"  {icon}: {message}")

def print_info(message):
    print(f"  ℹ INFO: {message}")

def cleanup_test_data():
    """Clean up existing test data."""
    from api_service.models import APIServiceUser, APIServiceAccessRequest
    
    APIServiceUser.objects.filter(email=TEST_EMAIL).delete()
    APIServiceAccessRequest.objects.filter(email=TEST_EMAIL).delete()
    print_result(True, f"Cleaned up existing test data for {TEST_EMAIL}")

def step1_create_request():
    """Step 1: Create access request via API Service."""
    print_header(1, "Create Access Request (via API Service)")
    
    url = f"{API_SERVICE_URL}/api/v1/api-service/access-request/"
    data = {
        'full_name': TEST_NAME,
        'email': TEST_EMAIL,
        'organization': 'Test Organization',
        'reason': 'Pipeline testing for API Service access',
        'intended_use': 'Testing and development'
    }
    
    print(f"  → Creating access request...")
    print(f"  → URL: {url}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print_result(True, f"Access request created")
            print_info(f"Request ID: {result.get('request_id')}")
            print_info(f"Email notification sent: {result.get('notification_sent')}")
            return result.get('request_id')
        else:
            print_result(False, f"Failed: {result.get('error')}")
            return None
    except Exception as e:
        print_result(False, f"Error: {e}")
        return None

def step2_approve_request(request_id):
    """Step 2: Approve access request."""
    print_header(2, "Approve Access Request")
    
    url = f"{API_SERVICE_URL}/api/v1/api-service/access-request/{request_id}/approve/"
    data = {
        'admin_username': 'test_admin',
        'admin_notes': 'Approved for pipeline testing'
    }
    
    print(f"  → Approving request {request_id}...")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            user_info = result.get('user', {})
            print_result(True, "Access request approved")
            print_info(f"Username: {user_info.get('username')}")
            print_info(f"Temp Password: {user_info.get('temp_password')}")
            print_info(f"Is Default Password: {user_info.get('is_default_password')}")
            print_info(f"Notification sent: {result.get('notification_sent')}")
            return user_info.get('username'), user_info.get('temp_password')
        else:
            print_result(False, f"Failed: {result.get('error')}")
            return None, None
    except Exception as e:
        print_result(False, f"Error: {e}")
        return None, None

def step3_login_requires_password_change(username, password):
    """Step 3: Login - should require password change."""
    print_header(3, "Login (Should Require Password Change)")
    
    url = f"{API_SERVICE_URL}/api/v1/api-service/auth/login/"
    data = {
        'username': username,
        'password': password
    }
    
    print(f"  → Logging in as {username}...")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            requires_change = result.get('requires_password_change', False)
            if requires_change:
                print_result(True, "Login successful - password change required")
                print_info(f"Message: {result.get('message')}")
                return True
            else:
                print_result(False, "Expected password change requirement, but not set")
                return False
        else:
            print_result(False, f"Login failed: {result.get('error')}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def step4_change_password(username, current_password, new_password):
    """Step 4: Change password - should send notification email."""
    print_header(4, "Change Password (Should Send Notification Email)")
    
    url = f"{API_SERVICE_URL}/api/v1/api-service/auth/change-password/"
    data = {
        'username': username,
        'current_password': current_password,
        'new_password': new_password,
        'confirm_password': new_password
    }
    
    print(f"  → Changing password for {username}...")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print_result(True, "Password changed successfully")
            print_info(f"Message: {result.get('message')}")
            print_info(f"Notification sent: {result.get('notification_sent')}")
            return True
        else:
            print_result(False, f"Failed: {result.get('error')}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def step5_login_with_new_password(username, new_password):
    """Step 5: Login with new password - should succeed without password change requirement."""
    print_header(5, "Login with New Password")
    
    url = f"{API_SERVICE_URL}/api/v1/api-service/auth/login/"
    data = {
        'username': username,
        'password': new_password
    }
    
    print(f"  → Logging in as {username} with new password...")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            requires_change = result.get('requires_password_change', False)
            if not requires_change:
                print_result(True, "Login successful - no password change required")
                user_info = result.get('user', {})
                print_info(f"User ID: {user_info.get('id')}")
                print_info(f"Username: {user_info.get('username')}")
                print_info(f"Role: {user_info.get('role')}")
                return True
            else:
                print_result(False, "Password change should not be required after change")
                return False
        else:
            print_result(False, f"Login failed: {result.get('error')}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  ForgeForth Africa - API Service Pipeline Test")
    print("="*60)
    print(f"  Test Email: {TEST_EMAIL}")
    print(f"  API Service URL: {API_SERVICE_URL}")
    print(f"  Data Layer URL: {DATA_LAYER_URL}")
    print(f"  Time: {datetime.now().isoformat()}")
    
    # Cleanup
    print_header(0, "Cleanup Existing Test Data")
    cleanup_test_data()
    
    results = {}
    
    # Step 1: Create access request
    request_id = step1_create_request()
    results['create_request'] = request_id is not None
    
    if not request_id:
        print("\n✗ Pipeline failed at Step 1. Cannot continue.")
        return
    
    # Step 2: Approve access request
    username, temp_password = step2_approve_request(request_id)
    results['approve_request'] = username is not None
    
    if not username:
        print("\n✗ Pipeline failed at Step 2. Cannot continue.")
        return
    
    # Step 3: Login (should require password change)
    results['login_requires_change'] = step3_login_requires_password_change(username, temp_password)
    
    if not results['login_requires_change']:
        print("\n✗ Pipeline failed at Step 3. Cannot continue.")
        return
    
    # Step 4: Change password
    results['change_password'] = step4_change_password(username, temp_password, NEW_PASSWORD)
    
    if not results['change_password']:
        print("\n✗ Pipeline failed at Step 4. Cannot continue.")
        return
    
    # Step 5: Login with new password
    results['login_new_password'] = step5_login_with_new_password(username, NEW_PASSWORD)
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    all_passed = all(results.values())
    for step, passed in results.items():
        icon = "[PASS]" if passed else "[FAIL]"
        step_name = step.replace('_', ' ').title()
        print(f"  {step_name}: {icon}")
    
    print(f"\nResults: {sum(results.values())}/{len(results)} tests passed")
    
    if all_passed:
        print("✓ All tests passed! API Service Pipeline is fully operational.")
        print(f"\n  📧 Check {TEST_EMAIL} for:")
        print("     - Access request confirmation email")
        print("     - Access approved email with credentials")
        print("     - Password changed notification email")
    else:
        print("✗ Some tests failed. Review the output above.")
    
    # Save results
    results_file = 'api_service_pipeline_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_email': TEST_EMAIL,
            'api_service_url': API_SERVICE_URL,
            'results': results,
            'all_passed': all_passed
        }, f, indent=2)
    print(f"\nResults saved to: {results_file}")

if __name__ == '__main__':
    main()

