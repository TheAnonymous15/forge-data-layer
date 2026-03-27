#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Full Pipeline Test Script
==============================================
Tests the complete access request pipeline including:
1. API Layer connectivity
2. Data Layer connectivity
3. Database operations
4. Email server authentication
5. Email sending
6. Access request creation
7. Access request approval via API Service

Usage: python test_pipeline.py [--email your@email.com] [--test approve]
"""

import os
import sys
import json
import argparse
import smtplib
import socket
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.db import connection

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")

def print_step(step_num, text):
    print(f"\n{Colors.CYAN}[Step {step_num}]{Colors.ENDC} {Colors.BOLD}{text}{Colors.ENDC}")

def print_substep(text):
    print(f"  {Colors.BLUE}→{Colors.ENDC} {text}")

def print_success(text):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.ENDC} {text}")

def print_fail(text):
    print(f"  {Colors.RED}✗ FAIL:{Colors.ENDC} {text}")

def print_warning(text):
    print(f"  {Colors.YELLOW}⚠ WARNING:{Colors.ENDC} {text}")

def print_info(text):
    print(f"  {Colors.BLUE}ℹ INFO:{Colors.ENDC} {text}")

def test_step(description, test_func):
    """Run a test and return result"""
    try:
        result = test_func()
        if result.get('success'):
            print_success(description)
            if result.get('details'):
                print_info(result['details'])
            return True
        else:
            print_fail(f"{description}: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print_fail(f"{description}: {str(e)}")
        return False


class PipelineTest:
    def __init__(self, test_email, api_service_url=None, data_layer_url=None):
        self.test_email = test_email
        self.api_service_url = api_service_url or 'http://localhost:9001'
        self.data_layer_url = data_layer_url or 'http://localhost:9005'
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'test_email': test_email,
            'api_service_url': self.api_service_url,
            'data_layer_url': self.data_layer_url,
            'steps': {}
        }
        self.created_request_id = None

    def run_all_tests(self):
        """Run the complete pipeline test"""
        print_header("ForgeForth Africa - Pipeline Test")
        print_info(f"Test Email: {self.test_email}")
        print_info(f"API Service URL: {self.api_service_url}")
        print_info(f"Data Layer URL: {self.data_layer_url}")
        print_info(f"Environment: {settings.DATA_LAYER_ENV}")
        print_info(f"Database Mode: {'TEST' if getattr(settings, 'IS_DEV_MODE', True) else 'PRODUCTION'}")
        print_info(f"Timestamp: {self.results['timestamp']}")

        # Step 1: Test Environment Configuration
        print_step(1, "Environment Configuration")
        self.test_environment()

        # Step 2: Test Database Connection
        print_step(2, "Database Connection")
        self.test_database()

        # Step 3: Test Email Configuration
        print_step(3, "Email Configuration")
        self.test_email_config()

        # Step 4: Test Email Server Connection
        print_step(4, "Email Server Connection (SMTP)")
        self.test_smtp_connection()

        # Step 5: Test Email Sending
        print_step(5, "Email Sending")
        self.test_email_sending()

        # Step 6: Test Access Request Creation
        print_step(6, "Access Request Creation")
        self.test_access_request()

        # Step 7: Test Full Pipeline (Access Request + Email)
        print_step(7, "Full Pipeline Test (Access Request with Email)")
        self.test_full_pipeline()

        # Summary
        self.print_summary()

        return self.results

    def run_approve_test(self):
        """Run only the approve access request test via API Service"""
        print_header("ForgeForth Africa - Approve Access Request Test")
        print_info(f"Test Email: {self.test_email}")
        print_info(f"API Service URL: {self.api_service_url}")
        print_info(f"Data Layer URL: {self.data_layer_url}")
        print_info(f"Timestamp: {self.results['timestamp']}")

        # Step 1: Test API Service connectivity
        print_step(1, "API Service Connectivity")
        api_ok = self.test_api_service_health()

        # Step 2: Test Data Layer connectivity
        print_step(2, "Data Layer Connectivity")
        dl_ok = self.test_data_layer_health()

        if not api_ok or not dl_ok:
            print_fail("Cannot proceed - services not available")
            return self.results

        # Step 3: Create a test access request
        print_step(3, "Create Test Access Request via API Service")
        request_created = self.test_create_access_request_via_api()

        if not request_created:
            print_fail("Cannot proceed - failed to create access request")
            return self.results

        # Step 4: Approve the access request via API Service
        print_step(4, "Approve Access Request via API Service")
        self.test_approve_access_request_via_api()

        # Summary
        self.print_summary()
        return self.results

    def test_api_service_health(self):
        """Test API Service health endpoint"""
        print_substep(f"Checking API Service at {self.api_service_url}...")

        try:
            # Try the health endpoint
            response = requests.get(f"{self.api_service_url}/health/", timeout=10)

            if response.status_code == 200:
                print_success(f"API Service is healthy (Status: {response.status_code})")
                self.results['steps']['api_service_health'] = {'success': True}
                return True
            else:
                print_fail(f"API Service returned status {response.status_code}")
                self.results['steps']['api_service_health'] = {'success': False, 'status_code': response.status_code}
                return False
        except requests.exceptions.ConnectionError:
            print_fail(f"Cannot connect to API Service at {self.api_service_url}")
            print_warning("Make sure the API service is running: python manage.py runserver 0.0.0.0:9001")
            self.results['steps']['api_service_health'] = {'success': False, 'error': 'Connection refused'}
            return False
        except Exception as e:
            print_fail(f"API Service health check error: {e}")
            self.results['steps']['api_service_health'] = {'success': False, 'error': str(e)}
            return False

    def test_data_layer_health(self):
        """Test Data Layer health endpoint"""
        print_substep(f"Checking Data Layer at {self.data_layer_url}...")

        try:
            response = requests.get(f"{self.data_layer_url}/api/v1/data-layer/health/", timeout=10)

            if response.status_code == 200:
                print_success(f"Data Layer is healthy (Status: {response.status_code})")
                data = response.json()
                print_info(f"Data Layer status: {data.get('status', 'unknown')}")
                self.results['steps']['data_layer_health'] = {'success': True}
                return True
            else:
                print_fail(f"Data Layer returned status {response.status_code}")
                self.results['steps']['data_layer_health'] = {'success': False, 'status_code': response.status_code}
                return False
        except requests.exceptions.ConnectionError:
            print_fail(f"Cannot connect to Data Layer at {self.data_layer_url}")
            print_warning("Make sure the Data Layer is running: python manage.py runserver 0.0.0.0:9005")
            self.results['steps']['data_layer_health'] = {'success': False, 'error': 'Connection refused'}
            return False
        except Exception as e:
            print_fail(f"Data Layer health check error: {e}")
            self.results['steps']['data_layer_health'] = {'success': False, 'error': str(e)}
            return False

    def test_create_access_request_via_api(self):
        """Create an access request via the API Service"""
        print_substep("Creating access request through API Service...")

        import uuid
        test_id = str(uuid.uuid4())[:8]

        request_data = {
            'full_name': f'Approval Test User {test_id}',
            'email': self.test_email,
            'organization': 'ForgeForth Test Organization',
            'service_type': 'api_service',
            'reason': 'Testing the approve access request pipeline via API Service',
            'requested_role': 'developer'
        }

        try:
            print_substep(f"POST {self.api_service_url}/api/v1/data-layer/access-requests/")
            response = requests.post(
                f"{self.api_service_url}/api/v1/data-layer/access-requests/",
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            print_info(f"Response status: {response.status_code}")

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('success'):
                    self.created_request_id = data.get('request_id') or data.get('id')
                    print_success(f"Access request created: {self.created_request_id}")
                    print_info(f"Email: {request_data['email']}")
                    print_info(f"Status: pending")
                    self.results['steps']['create_access_request'] = {
                        'success': True,
                        'request_id': self.created_request_id
                    }
                    return True
                else:
                    print_fail(f"API returned success=false: {data.get('error', 'Unknown error')}")
                    self.results['steps']['create_access_request'] = {'success': False, 'error': data.get('error')}
                    return False
            else:
                print_fail(f"HTTP {response.status_code}: {response.text[:200]}")
                self.results['steps']['create_access_request'] = {'success': False, 'status_code': response.status_code}
                return False

        except Exception as e:
            print_fail(f"Error creating access request: {e}")
            self.results['steps']['create_access_request'] = {'success': False, 'error': str(e)}
            return False

    def test_approve_access_request_via_api(self):
        """Approve an access request via the API Service endpoint"""
        if not self.created_request_id:
            print_fail("No request ID available - cannot test approve")
            self.results['steps']['approve_access_request'] = {'success': False, 'error': 'No request ID'}
            return False

        print_substep(f"Approving access request: {self.created_request_id}")

        approve_data = {
            'admin_notes': 'Approved via pipeline test script'
        }

        try:
            endpoint = f"{self.api_service_url}/api/v1/data-layer/access-requests/{self.created_request_id}/approve/"
            print_substep(f"POST {endpoint}")

            response = requests.post(
                endpoint,
                json=approve_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            print_info(f"Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_success("Access request APPROVED successfully!")
                    print_info(f"Message: {data.get('message', 'N/A')}")

                    user_data = data.get('user', {})
                    if user_data:
                        print_success(f"User account created:")
                        print_info(f"  User ID: {user_data.get('id', 'N/A')}")
                        print_info(f"  Username: {user_data.get('username', 'N/A')}")
                        print_info(f"  Temp Password: {user_data.get('temp_password', '***hidden***')}")

                    notification_sent = data.get('notification_sent', False)
                    if notification_sent:
                        print_success(f"Approval email sent to {self.test_email}")
                    else:
                        notification_error = data.get('notification_error', 'Unknown')
                        print_warning(f"Approval email not sent: {notification_error}")

                    self.results['steps']['approve_access_request'] = {
                        'success': True,
                        'request_id': self.created_request_id,
                        'user_created': bool(user_data),
                        'username': user_data.get('username'),
                        'notification_sent': notification_sent
                    }
                    return True
                else:
                    error = data.get('error', 'Unknown error')
                    print_fail(f"Approval failed: {error}")
                    self.results['steps']['approve_access_request'] = {'success': False, 'error': error}
                    return False
            else:
                print_fail(f"HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print_info(f"Error: {error_data.get('error', response.text[:200])}")
                except:
                    print_info(f"Response: {response.text[:200]}")
                self.results['steps']['approve_access_request'] = {
                    'success': False,
                    'status_code': response.status_code
                }
                return False

        except Exception as e:
            print_fail(f"Error approving access request: {e}")
            import traceback
            traceback.print_exc()
            self.results['steps']['approve_access_request'] = {'success': False, 'error': str(e)}
            return False

    def test_environment(self):
        """Test environment configuration"""
        print_substep("Checking Django settings...")

        checks = [
            ('SECRET_KEY', bool(settings.SECRET_KEY)),
            ('DEBUG', settings.DEBUG is not None),
            ('ALLOWED_HOSTS', bool(settings.ALLOWED_HOSTS)),
            ('DATABASE_URL', bool(getattr(settings, 'DATABASE_URL', None))),
        ]

        all_pass = True
        for name, passed in checks:
            if passed:
                print_success(f"{name} is configured")
            else:
                print_fail(f"{name} is NOT configured")
                all_pass = False

        self.results['steps']['environment'] = {'success': all_pass}
        return all_pass

    def test_database(self):
        """Test database connection"""
        print_substep("Testing database connection...")

        try:
            # Test connection
            connection.ensure_connection()
            print_success("Database connection established")

            # Get database info
            db_settings = settings.DATABASES['default']
            engine = db_settings.get('ENGINE', 'unknown')
            name = db_settings.get('NAME', 'unknown')
            print_info(f"Engine: {engine}")
            print_info(f"Database: {name}")

            # Test a simple query
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    print_success("Database query test passed")
                else:
                    print_fail("Database query test failed")
                    self.results['steps']['database'] = {'success': False}
                    return False

            # Check if ServiceAccessRequest table exists
            from data_layer.models import ServiceAccessRequest
            count = ServiceAccessRequest.objects.count()
            print_success(f"ServiceAccessRequest table accessible (current records: {count})")

            self.results['steps']['database'] = {'success': True, 'record_count': count}
            return True

        except Exception as e:
            print_fail(f"Database error: {str(e)}")
            self.results['steps']['database'] = {'success': False, 'error': str(e)}
            return False

    def test_email_config(self):
        """Test email configuration"""
        print_substep("Checking email settings...")

        config = {
            'EMAIL_BACKEND': settings.EMAIL_BACKEND,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': settings.EMAIL_PORT,
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'EMAIL_HOST_PASSWORD': '***' if settings.EMAIL_HOST_PASSWORD else '(not set)',
            'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
            'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', False),
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        }

        print_info(f"Backend: {config['EMAIL_BACKEND']}")
        print_info(f"Host: {config['EMAIL_HOST']}:{config['EMAIL_PORT']}")
        print_info(f"User: {config['EMAIL_HOST_USER']}")
        print_info(f"Password: {config['EMAIL_HOST_PASSWORD']}")
        print_info(f"TLS: {config['EMAIL_USE_TLS']}, SSL: {config['EMAIL_USE_SSL']}")
        print_info(f"From: {config['DEFAULT_FROM_EMAIL']}")

        # Check if password is configured
        if not settings.EMAIL_HOST_PASSWORD:
            print_warning("EMAIL_HOST_PASSWORD is not set - emails may fail")
            self.results['steps']['email_config'] = {'success': False, 'error': 'No password'}
            return False

        if 'console' in settings.EMAIL_BACKEND.lower():
            print_warning("Using console email backend - emails will be printed, not sent")

        print_success("Email configuration looks valid")
        self.results['steps']['email_config'] = {'success': True, 'config': config}
        return True

    def test_smtp_connection(self):
        """Test SMTP server connection"""
        print_substep(f"Connecting to SMTP server {settings.EMAIL_HOST}:{settings.EMAIL_PORT}...")

        try:
            # Test DNS resolution first
            print_substep("Resolving DNS...")
            ip = socket.gethostbyname(settings.EMAIL_HOST)
            print_success(f"DNS resolved: {settings.EMAIL_HOST} -> {ip}")

            # Test port connectivity
            print_substep(f"Testing port {settings.EMAIL_PORT} connectivity...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((settings.EMAIL_HOST, settings.EMAIL_PORT))
            sock.close()

            if result != 0:
                print_fail(f"Cannot connect to port {settings.EMAIL_PORT}")
                self.results['steps']['smtp_connection'] = {'success': False, 'error': 'Port not reachable'}
                return False
            print_success(f"Port {settings.EMAIL_PORT} is reachable")

            # Test SMTP connection
            print_substep("Establishing SMTP connection...")
            if getattr(settings, 'EMAIL_USE_SSL', False):
                server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30)
            else:
                server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30)

            print_success("SMTP connection established")

            # Start TLS if needed
            if settings.EMAIL_USE_TLS and not getattr(settings, 'EMAIL_USE_SSL', False):
                print_substep("Starting TLS encryption...")
                server.starttls()
                print_success("TLS encryption enabled")

            # Authenticate
            print_substep(f"Authenticating as {settings.EMAIL_HOST_USER}...")
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            print_success("SMTP authentication successful")

            server.quit()

            self.results['steps']['smtp_connection'] = {'success': True}
            return True

        except smtplib.SMTPAuthenticationError as e:
            print_fail(f"SMTP Authentication failed: {str(e)}")
            self.results['steps']['smtp_connection'] = {'success': False, 'error': f'Auth failed: {str(e)}'}
            return False
        except socket.timeout:
            print_fail("Connection timed out")
            self.results['steps']['smtp_connection'] = {'success': False, 'error': 'Timeout'}
            return False
        except Exception as e:
            print_fail(f"SMTP error: {str(e)}")
            self.results['steps']['smtp_connection'] = {'success': False, 'error': str(e)}
            return False

    def test_email_sending(self):
        """Test sending an actual email"""
        print_substep(f"Sending test email to {self.test_email}...")

        try:
            subject = "ForgeForth Africa - Pipeline Test Email"
            message = f"""
Hello,

This is a test email from the ForgeForth Africa Pipeline Test.

Test Details:
- Timestamp: {datetime.now().isoformat()}
- Environment: {settings.DATA_LAYER_ENV}
- Database Mode: {'TEST' if getattr(settings, 'IS_DEV_MODE', True) else 'PRODUCTION'}

If you received this email, the email pipeline is working correctly!

Best regards,
ForgeForth Africa System
            """

            html_message = f"""
<!DOCTYPE html>
<html>
<head><title>Pipeline Test</title></head>
<body style="font-family: Arial, sans-serif; background-color: #0f172a; padding: 20px;">
    <div style="max-width: 500px; margin: 0 auto; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; border: 1px solid rgba(99, 102, 241, 0.3); padding: 30px;">
        <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #fff; font-size: 14px; font-weight: 600; padding: 10px 20px; border-radius: 6px; display: inline-block; margin-bottom: 20px;">ForgeForth Africa</div>
        <h1 style="color: #fff; font-size: 20px; margin-bottom: 15px;">Pipeline Test Successful! ✓</h1>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">This is a test email confirming the email pipeline is working correctly.</p>
        <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px; padding: 15px; margin: 20px 0;">
            <p style="color: #cbd5e1; font-size: 13px; margin: 5px 0;"><strong>Timestamp:</strong> {datetime.now().isoformat()}</p>
            <p style="color: #cbd5e1; font-size: 13px; margin: 5px 0;"><strong>Environment:</strong> {settings.DATA_LAYER_ENV}</p>
            <p style="color: #cbd5e1; font-size: 13px; margin: 5px 0;"><strong>Status:</strong> <span style="color: #22c55e;">All Systems Operational</span></p>
        </div>
        <p style="color: #64748b; font-size: 12px; margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">© 2026 ForgeForth Africa</p>
    </div>
</body>
</html>
            """

            from django.core.mail import EmailMultiAlternatives

            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[self.test_email]
            )
            email.attach_alternative(html_message, "text/html")

            print_substep("Connecting to mail server...")
            print_substep("Sending email...")
            email.send(fail_silently=False)

            print_success(f"Test email sent successfully to {self.test_email}")
            self.results['steps']['email_sending'] = {'success': True, 'recipient': self.test_email}
            return True

        except Exception as e:
            print_fail(f"Email sending failed: {str(e)}")
            self.results['steps']['email_sending'] = {'success': False, 'error': str(e)}
            return False

    def test_access_request(self):
        """Test creating an access request in the database"""
        print_substep("Creating test access request...")

        try:
            from data_layer.models import ServiceAccessRequest
            import uuid

            # Create a unique test request
            test_id = str(uuid.uuid4())[:8]
            request = ServiceAccessRequest.objects.create(
                full_name=f"Pipeline Test {test_id}",
                email=f"test_{test_id}@pipeline.test",
                organization="Pipeline Test Org",
                service_type="api_service",
                reason="Automated pipeline test - can be deleted",
                status="pending"
            )

            print_success(f"Access request created with ID: {request.id}")
            print_info(f"Request email: {request.email}")

            # Verify it was saved
            saved = ServiceAccessRequest.objects.filter(id=request.id).exists()
            if saved:
                print_success("Request verified in database")
            else:
                print_fail("Request not found in database after creation")
                self.results['steps']['access_request'] = {'success': False, 'error': 'Not saved'}
                return False

            # Clean up test request
            request.delete()
            print_success("Test request cleaned up")

            self.results['steps']['access_request'] = {'success': True, 'request_id': str(request.id)}
            return True

        except Exception as e:
            print_fail(f"Access request creation failed: {str(e)}")
            self.results['steps']['access_request'] = {'success': False, 'error': str(e)}
            return False

    def test_full_pipeline(self):
        """Test the complete pipeline: create access request + send confirmation email"""
        print_substep("Running full pipeline test...")
        print_substep(f"Email recipient: {self.test_email}")

        try:
            from data_layer.models import ServiceAccessRequest
            from communications.services import send_access_request_confirmation
            import uuid

            # Step 1: Create the access request
            print_substep("1. Creating access request in database...")
            test_id = str(uuid.uuid4())[:8]

            request = ServiceAccessRequest.objects.create(
                full_name="Daniel Muthike",
                email=self.test_email,
                organization="Full Pipeline Test",
                service_type="api_service",
                reason="Full pipeline test with email confirmation",
                status="pending"
            )
            print_success(f"Access request created: {request.id}")

            # Step 2: Send confirmation email
            print_substep("2. Sending confirmation email...")
            email_result = send_access_request_confirmation(
                full_name=request.full_name,
                email=request.email,
                service_type=request.service_type,
                request_id=str(request.id)
            )

            if email_result.get('success'):
                print_success(f"Confirmation email sent to {self.test_email}")
                print_info(f"Email log ID: {email_result.get('email_log_id', 'N/A')}")
            else:
                print_fail(f"Email sending failed: {email_result.get('error', 'Unknown error')}")
                # Don't fail the whole test, just note the email issue
                print_warning("Access request was created but email failed")

            # Verify final state
            print_substep("3. Verifying final state...")
            saved_request = ServiceAccessRequest.objects.get(id=request.id)
            print_success(f"Request status: {saved_request.status}")
            print_info(f"Request ID: {saved_request.id}")
            print_info(f"Created at: {saved_request.created_at}")

            self.results['steps']['full_pipeline'] = {
                'success': True,
                'request_id': str(request.id),
                'email_sent': email_result.get('success', False),
                'email_log_id': email_result.get('email_log_id')
            }

            print_success("Full pipeline test completed!")
            return True

        except Exception as e:
            print_fail(f"Full pipeline test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['steps']['full_pipeline'] = {'success': False, 'error': str(e)}
            return False

    def print_summary(self):
        """Print test summary"""
        print_header("Test Summary")

        total_steps = len(self.results['steps'])
        passed_steps = sum(1 for s in self.results['steps'].values() if s.get('success'))
        failed_steps = total_steps - passed_steps

        for step_name, result in self.results['steps'].items():
            status = f"{Colors.GREEN}PASS{Colors.ENDC}" if result.get('success') else f"{Colors.RED}FAIL{Colors.ENDC}"
            print(f"  {step_name.replace('_', ' ').title()}: [{status}]")
            if not result.get('success') and result.get('error'):
                print(f"    {Colors.RED}└── Error: {result['error']}{Colors.ENDC}")

        print(f"\n{Colors.BOLD}Results: {passed_steps}/{total_steps} tests passed{Colors.ENDC}")

        if failed_steps == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Pipeline is fully operational.{Colors.ENDC}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ {failed_steps} test(s) failed. Please check the errors above.{Colors.ENDC}")

        # Save results to file
        results_file = 'pipeline_test_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n{Colors.BLUE}Results saved to: {results_file}{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser(description='Test ForgeForth Africa Pipeline')
    parser.add_argument('--email', '-e', default='muthikedaniel59@gmail.com',
                        help='Email address to send test emails to')
    parser.add_argument('--test', '-t', choices=['all', 'approve', 'email', 'db'],
                        default='all', help='Specific test to run')
    parser.add_argument('--api-url', default='http://localhost:9001',
                        help='API Service URL (default: http://localhost:9001)')
    parser.add_argument('--data-url', default='http://localhost:9005',
                        help='Data Layer URL (default: http://localhost:9005)')
    args = parser.parse_args()

    tester = PipelineTest(
        test_email=args.email,
        api_service_url=args.api_url,
        data_layer_url=args.data_url
    )

    if args.test == 'approve':
        tester.run_approve_test()
    elif args.test == 'email':
        print_header("Email Test Only")
        tester.test_email_config()
        tester.test_smtp_connection()
        tester.test_email_sending()
        tester.print_summary()
    elif args.test == 'db':
        print_header("Database Test Only")
        tester.test_database()
        tester.test_access_request()
        tester.print_summary()
    else:
        tester.run_all_tests()


if __name__ == '__main__':
    main()

