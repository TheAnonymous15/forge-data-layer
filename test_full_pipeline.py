#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Full Pipeline Test
======================================
Tests both API Service and Data Layer access request pipelines including:
1. Create access request
2. Approve request
3. Login (should require password change)
4. Change password (sends notification email)
5. Final login (should succeed with redirect URL)
"""
import os
import sys
import json
import django
import requests
from datetime import datetime

# Setup Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

# Configuration
DATA_LAYER_URL = 'http://localhost:9005'
TEST_EMAIL = 'daniel.kinyua@tutamail.com'
TEST_NAME = 'Daniel Kinyua'
NEW_PASSWORD = 'SecurePass2026!'


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_step(step_num, description):
    print(f"[Step {step_num}] {description}")


def print_result(success, message):
    icon = "✓" if success else "✗"
    status = "PASS" if success else "FAIL"
    print(f"  {icon} {status}: {message}")


def clean_test_data(service_type):
    """Clean existing test data for a service."""
    if service_type == 'api_service':
        from api_service.models import APIServiceUser, APIServiceAccessRequest
        APIServiceUser.objects.filter(email=TEST_EMAIL).delete()
        APIServiceAccessRequest.objects.filter(email=TEST_EMAIL).delete()
    else:
        from data_layer.models import DataLayerUser, DataLayerAccessRequest
        DataLayerUser.objects.filter(email=TEST_EMAIL).delete()
        DataLayerAccessRequest.objects.filter(email=TEST_EMAIL).delete()
    print_result(True, f"Cleaned test data for {TEST_EMAIL}")


def test_pipeline(service_type):
    """Test full pipeline for a service."""

    if service_type == 'api_service':
        base_url = f"{DATA_LAYER_URL}/api/v1/api-service"
        service_name = "API Service"
    else:
        base_url = f"{DATA_LAYER_URL}/api/v1/data-layer"
        service_name = "Data Layer"

    print_header(f"{service_name} Full Pipeline Test")

    # Step 0: Clean test data
    print_step(0, "Clean existing test data")
    try:
        clean_test_data(service_type)
    except Exception as e:
        print_result(False, f"Failed to clean data: {e}")
        return False

    # Step 1: Create access request
    print_step(1, "Create access request")
    try:
        response = requests.post(
            f"{base_url}/access-requests/",
            json={
                'full_name': TEST_NAME,
                'email': TEST_EMAIL,
                'organization': 'ForgeForth Africa',
                'reason': f'Full pipeline test for {service_name}',
                'intended_use': 'Testing and development'
            },
            timeout=30
        )
        data = response.json()

        if not data.get('success'):
            print_result(False, f"Create request failed: {data.get('error')}")
            return False

        request_id = data.get('request_id')
        notification_sent = data.get('notification_sent', False)
        print_result(True, f"Request created: {request_id}")
        print_result(notification_sent, f"Confirmation email {'sent' if notification_sent else 'NOT sent'}")

    except Exception as e:
        print_result(False, f"Create request error: {e}")
        return False

    # Step 2: Approve access request
    print_step(2, "Approve access request")
    try:
        response = requests.post(
            f"{base_url}/access-requests/{request_id}/approve/",
            json={
                'admin_username': 'test_admin',
                'admin_notes': 'Approved for pipeline testing'
            },
            timeout=30
        )
        data = response.json()

        if not data.get('success'):
            print_result(False, f"Approve request failed: {data.get('error')}")
            return False

        user_data = data.get('user', {})
        temp_password = user_data.get('temp_password')
        username = user_data.get('username')
        is_default_password = user_data.get('is_default_password', True)
        notification_sent = data.get('notification_sent', False)

        print_result(True, f"Request approved, user created")
        print(f"      Username: {username}")
        print(f"      Temp Password: {temp_password}")
        print(f"      Is Default Password: {is_default_password}")
        print_result(notification_sent, f"Approval email {'sent' if notification_sent else 'NOT sent'}")

    except Exception as e:
        print_result(False, f"Approve request error: {e}")
        return False

    # Step 3: Login (should require password change)
    print_step(3, "Login with temp password (should require password change)")
    try:
        response = requests.post(
            f"{base_url}/auth/login/",
            json={
                'username': username,
                'password': temp_password
            },
            timeout=30
        )
        data = response.json()

        if not data.get('success'):
            print_result(False, f"Login failed: {data.get('error')}")
            return False

        requires_change = data.get('requires_password_change', False)

        if requires_change:
            print_result(True, "Login successful - password change required")
            print(f"      Message: {data.get('message')}")
        else:
            print_result(False, "Login should have required password change but didn't")
            return False

    except Exception as e:
        print_result(False, f"Login error: {e}")
        return False

    # Step 4: Change password
    print_step(4, "Change password (should send notification email)")
    try:
        response = requests.post(
            f"{base_url}/auth/change-password/",
            json={
                'username': username,
                'current_password': temp_password,
                'new_password': NEW_PASSWORD,
                'confirm_password': NEW_PASSWORD
            },
            timeout=30
        )
        data = response.json()

        if not data.get('success'):
            print_result(False, f"Password change failed: {data.get('error')}")
            return False

        notification_sent = data.get('notification_sent', False)
        print_result(True, "Password changed successfully")
        print_result(notification_sent, f"Password change email {'sent' if notification_sent else 'NOT sent'}")

    except Exception as e:
        print_result(False, f"Password change error: {e}")
        return False

    # Step 5: Final login (should succeed with redirect URL)
    print_step(5, "Final login with new password (verify redirect URL)")
    try:
        response = requests.post(
            f"{base_url}/auth/login/",
            json={
                'username': username,
                'password': NEW_PASSWORD
            },
            timeout=30
        )
        data = response.json()

        if not data.get('success'):
            print_result(False, f"Final login failed: {data.get('error')}")
            return False

        requires_change = data.get('requires_password_change', False)
        redirect_url = data.get('redirect_url', 'NOT PROVIDED')
        token = data.get('token')
        user_info = data.get('user', {})

        if requires_change:
            print_result(False, "Login should NOT require password change anymore")
            return False

        print_result(True, "Final login successful!")
        print(f"      Redirect URL: {redirect_url}")
        print(f"      Token: {token[:20]}..." if token else "      Token: None")
        print(f"      User Role: {user_info.get('role', 'N/A')}")
        print(f"      User Email: {user_info.get('email', 'N/A')}")

        # Verify redirect URL is provided
        if redirect_url and redirect_url != 'NOT PROVIDED':
            print_result(True, f"Redirect URL verified: {redirect_url}")
        else:
            print_result(False, "Redirect URL NOT provided in response")
            return False

    except Exception as e:
        print_result(False, f"Final login error: {e}")
        return False

    return True


def main():
    print("\n" + "="*60)
    print("  ForgeForth Africa - Full Pipeline Test Suite")
    print("  Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    results = {}

    # Test API Service Pipeline
    results['api_service'] = test_pipeline('api_service')

    # Test Data Layer Pipeline
    results['data_layer'] = test_pipeline('data_layer')

    # Print summary
    print_header("Test Summary")

    for service, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        icon = "✓" if passed else "✗"
        print(f"  {icon} {service.replace('_', ' ').title()}: {status}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print(f"\n  Results: {total_passed}/{total_tests} pipelines passed")

    if total_passed == total_tests:
        print("\n  ✓ All pipeline tests passed successfully!")
        return 0
    else:
        print("\n  ✗ Some pipeline tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())

