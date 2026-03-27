#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Access Request Pipeline Test
============================================================
Tests the complete Data Layer access request flow:
1. Health check
2. Create access request
3. List access requests
4. Get specific request
5. Approve/Reject request
6. Email notifications
"""
import os
import sys
import json
import argparse
import requests
from datetime import datetime

# Configuration
DATA_LAYER_URL = os.getenv('DATA_LAYER_URL', 'http://localhost:9005')
TEST_EMAIL = os.getenv('TEST_EMAIL', 'daniel.kinyua@tutamail.com')

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")


def print_step(step_num, text):
    print(f"\n{Colors.CYAN}[Step {step_num}] {text}{Colors.RESET}")


def print_pass(text):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.RESET} {text}")


def print_fail(text):
    print(f"  {Colors.RED}✗ FAIL:{Colors.RESET} {text}")


def print_info(text):
    print(f"  {Colors.YELLOW}ℹ INFO:{Colors.RESET} {text}")


def print_action(text):
    print(f"  → {text}")


def test_health():
    """Test Data Layer health endpoint."""
    print_step(1, "Checking Data Layer Health")

    try:
        url = f"{DATA_LAYER_URL}/api/v1/data-layer/health/"
        print_action(f"Endpoint: GET {url}")

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') or data.get('status') == 'healthy':
                print_pass(f"Data Layer is healthy at {url}")
                return True
            else:
                print_fail(f"Health check returned: {data}")
                return False
        else:
            print_fail(f"Health check failed with status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_fail(f"Cannot connect to Data Layer at {DATA_LAYER_URL}")
        print_info("Make sure the Data Layer service is running on port 9005")
        return False
    except Exception as e:
        print_fail(f"Health check error: {e}")
        return False


def create_access_request(email):
    """Create a new access request."""
    print_step(2, "Creating Access Request")
    print_info(f"Using email: {email}")

    try:
        url = f"{DATA_LAYER_URL}/api/v1/data-layer/access-requests/"
        print_action(f"Endpoint: POST {url}")

        payload = {
            "full_name": "Test User",
            "email": email,
            "phone": "+254700000000",
            "organization": "Test Organization",
            "job_title": "Developer",
            "reason": "Testing Data Layer access request pipeline",
            "intended_use": "API integration and testing",
            "requested_role": "developer"
        }

        response = requests.post(url, json=payload, timeout=15)
        data = response.json()

        print_info(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(data, indent=2)}")

        if response.status_code in [200, 201] and data.get('success'):
            request_id = data.get('request_id')
            notification = data.get('notification_sent', False)
            print_pass(f"Access request created: {request_id}")
            if notification:
                print_info("Confirmation email sent")
            return request_id
        else:
            print_fail(f"Failed to create request: {data.get('error', 'Unknown error')}")
            return None

    except Exception as e:
        print_fail(f"Create request error: {e}")
        return None


def list_access_requests():
    """List all access requests."""
    print_step(3, "Listing Access Requests")

    try:
        url = f"{DATA_LAYER_URL}/api/v1/data-layer/access-requests/list/"
        print_action(f"Endpoint: GET {url}")

        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get('success'):
            total = data.get('total', 0)
            requests_list = data.get('requests', [])
            print_pass(f"Listed {len(requests_list)} requests (total: {total})")
            return requests_list
        else:
            print_fail(f"Failed to list requests: {data.get('error')}")
            return []

    except Exception as e:
        print_fail(f"List requests error: {e}")
        return []


def get_access_request(request_id):
    """Get a specific access request."""
    print_step(4, "Getting Access Request Details")

    try:
        url = f"{DATA_LAYER_URL}/api/v1/data-layer/access-requests/{request_id}/"
        print_action(f"Endpoint: GET {url}")

        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get('success'):
            req = data.get('request', {})
            print_pass(f"Retrieved request for: {req.get('email')}")
            print_info(f"Status: {req.get('status')}")
            print_info(f"Requested Role: {req.get('requested_role')}")
            return req
        else:
            print_fail(f"Failed to get request: {data.get('error')}")
            return None

    except Exception as e:
        print_fail(f"Get request error: {e}")
        return None


def approve_access_request(request_id):
    """Approve an access request."""
    print_step(5, "Approving Access Request")

    try:
        url = f"{DATA_LAYER_URL}/api/v1/data-layer/access-requests/{request_id}/approve/"
        print_action(f"Endpoint: POST {url}")

        payload = {
            "admin_username": "admin",
            "admin_notes": "Approved via pipeline test"
        }

        response = requests.post(url, json=payload, timeout=15)
        data = response.json()

        print_info(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(data, indent=2)}")

        if data.get('success'):
            user = data.get('user', {})
            print_pass(f"Request approved! User created: {user.get('username')}")
            print_info(f"Temp password: {user.get('temp_password')}")
            if data.get('notification_sent'):
                print_info("Approval email sent")
            return True
        else:
            print_fail(f"Failed to approve: {data.get('error')}")
            return False

    except Exception as e:
        print_fail(f"Approve request error: {e}")
        return False


def reject_access_request(request_id):
    """Reject an access request."""
    print_step(5, "Rejecting Access Request")

    try:
        url = f"{DATA_LAYER_URL}/api/v1/data-layer/access-requests/{request_id}/reject/"
        print_action(f"Endpoint: POST {url}")

        payload = {
            "admin_username": "admin",
            "reason": "Test rejection - pipeline testing"
        }

        response = requests.post(url, json=payload, timeout=15)
        data = response.json()

        print_info(f"Status Code: {response.status_code}")
        print_info(f"Response: {json.dumps(data, indent=2)}")

        if data.get('success'):
            print_pass("Request rejected successfully")
            if data.get('notification_sent'):
                print_info("Rejection email sent")
            return True
        else:
            print_fail(f"Failed to reject: {data.get('error')}")
            return False

    except Exception as e:
        print_fail(f"Reject request error: {e}")
        return False


def run_pipeline(email, action='approve', skip_action=False):
    """Run the complete pipeline test."""
    print_header("Data Layer Access Request Pipeline Test")
    print(f"Data Layer: {DATA_LAYER_URL}")
    print(f"Test Email: {email}")
    print(f"Action: {action}")

    results = {
        'health': False,
        'create': False,
        'list': False,
        'get': False,
        'action': False
    }

    # Step 1: Health Check
    results['health'] = test_health()
    if not results['health']:
        print_fail("Data Layer is not healthy. Cannot continue.")
        return results

    # Step 2: Create Access Request
    request_id = create_access_request(email)
    results['create'] = request_id is not None

    if not results['create']:
        print_fail("Failed to create access request. Cannot continue.")
        return results

    # Step 3: List Access Requests
    requests_list = list_access_requests()
    results['list'] = len(requests_list) > 0

    # Step 4: Get Specific Request
    request_details = get_access_request(request_id)
    results['get'] = request_details is not None

    # Step 5: Approve or Reject
    if skip_action:
        print_step(5, f"Skipping {action} (--skip-action flag)")
        print_info(f"Request ID for manual testing: {request_id}")
        results['action'] = True
    elif action == 'approve':
        results['action'] = approve_access_request(request_id)
    elif action == 'reject':
        results['action'] = reject_access_request(request_id)

    # Summary
    print_header("Test Summary")

    for key, passed in results.items():
        status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if passed else f"{Colors.RED}[FAIL]{Colors.RESET}"
        print(f"  {key.title()}: {status}")

    passed_count = sum(results.values())
    total_count = len(results)

    print(f"\nResults: {passed_count}/{total_count} tests passed")

    if all(results.values()):
        print(f"{Colors.GREEN}✓ All tests passed! Pipeline is fully operational.{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ Some tests failed. Check the output above.{Colors.RESET}")

    return results


def main():
    parser = argparse.ArgumentParser(description='Test Data Layer Access Request Pipeline')
    parser.add_argument('--email', default=TEST_EMAIL, help='Email for test request')
    parser.add_argument('--action', choices=['approve', 'reject'], default='approve',
                        help='Action to take on request')
    parser.add_argument('--skip-action', action='store_true',
                        help='Skip the approve/reject step')
    parser.add_argument('--reject', action='store_true',
                        help='Test rejection instead of approval')

    args = parser.parse_args()

    action = 'reject' if args.reject else args.action

    run_pipeline(
        email=args.email,
        action=action,
        skip_action=args.skip_action
    )


if __name__ == '__main__':
    main()

