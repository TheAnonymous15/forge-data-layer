# -*- coding: utf-8 -*-
"""
ForgeForth Africa - Data Layer Client SDK
=========================================
A Python client for other services to communicate with the Data Layer.
Copy this file to your service to interact with the Data Layer API.
"""
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DataLayerConfig:
    """Configuration for Data Layer client."""
    base_url: str = "http://localhost:9010"
    service_id: str = ""
    api_key: str = ""
    timeout: float = 30.0

    @classmethod
    def from_env(cls):
        """Create config from environment variables."""
        return cls(
            base_url=os.getenv('DATA_LAYER_URL', 'http://localhost:9010'),
            service_id=os.getenv('SERVICE_ID', ''),
            api_key=os.getenv('DATA_LAYER_API_KEY', ''),
            timeout=float(os.getenv('DATA_LAYER_TIMEOUT', '30')),
        )


class DataLayerError(Exception):
    """Base exception for Data Layer errors."""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class DataLayerClient:
    """
    Client for interacting with the ForgeForth Data Layer API.

    Usage:
        client = DataLayerClient.from_env()

        # Register a user
        user = await client.users.create({
            'email': 'user@example.com',
            'password': 'securepassword',
            'first_name': 'John',
            'last_name': 'Doe',
            ...
        })

        # Login
        result = await client.users.login('user@example.com', 'password')

        # Get user profile
        profile = await client.profiles.get(user_id)
    """

    def __init__(self, config: DataLayerConfig = None):
        self.config = config or DataLayerConfig.from_env()
        self._client = None

        # Initialize sub-clients
        self.users = UsersClient(self)
        self.profiles = ProfilesClient(self)
        self.organizations = OrganizationsClient(self)
        self.opportunities = OpportunitiesClient(self)
        self.applications = ApplicationsClient(self)
        self.tokens = TokensClient(self)

    @classmethod
    def from_env(cls):
        """Create client from environment variables."""
        return cls(DataLayerConfig.from_env())

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self._get_headers(),
            )
        return self._client

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.config.service_id:
            headers['X-Service-ID'] = self.config.service_id
        if self.config.api_key:
            headers['X-API-Key'] = self.config.api_key
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        params: dict = None,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = f"/api/v1/{endpoint.lstrip('/')}"

        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise DataLayerError(
                    message=error_data.get('error', error_data.get('detail', 'Request failed')),
                    status_code=response.status_code,
                    details=error_data,
                )

            return response.json() if response.content else {}

        except httpx.RequestError as e:
            logger.error(f"Data Layer request failed: {e}")
            raise DataLayerError(f"Connection error: {e}")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def health_check(self) -> Dict[str, Any]:
        """Check if Data Layer is healthy."""
        return await self._request('GET', '/health/')


class BaseResourceClient:
    """Base class for resource-specific clients."""

    resource_name = ''

    def __init__(self, parent: DataLayerClient):
        self.parent = parent

    async def _request(self, method: str, endpoint: str = '', **kwargs):
        full_endpoint = f"{self.resource_name}/{endpoint}".rstrip('/')
        return await self.parent._request(method, full_endpoint, **kwargs)

    async def list(self, params: dict = None, auth_token: str = None) -> List[Dict]:
        """List resources."""
        result = await self._request('GET', params=params, auth_token=auth_token)
        return result.get('results', result) if isinstance(result, dict) else result

    async def get(self, resource_id: str, auth_token: str = None) -> Dict:
        """Get a single resource."""
        return await self._request('GET', f'{resource_id}/', auth_token=auth_token)

    async def create(self, data: dict, auth_token: str = None) -> Dict:
        """Create a resource."""
        return await self._request('POST', data=data, auth_token=auth_token)

    async def update(self, resource_id: str, data: dict, auth_token: str = None) -> Dict:
        """Update a resource."""
        return await self._request('PATCH', f'{resource_id}/', data=data, auth_token=auth_token)

    async def delete(self, resource_id: str, auth_token: str = None) -> None:
        """Delete a resource."""
        await self._request('DELETE', f'{resource_id}/', auth_token=auth_token)


class UsersClient(BaseResourceClient):
    """Client for user operations."""

    resource_name = 'users'

    async def register(self, data: dict) -> Dict:
        """Register a new user."""
        return await self.create(data)

    async def login(self, email: str, password: str, device_info: dict = None) -> Dict:
        """Authenticate a user."""
        return await self._request('POST', 'login/', data={
            'email': email,
            'password': password,
            'device_info': device_info or {},
        })

    async def verify_email(self, token: str) -> Dict:
        """Verify email with token."""
        return await self._request('POST', 'verify_email/', data={'token': token})

    async def forgot_password(self, email: str) -> Dict:
        """Request password reset."""
        return await self._request('POST', 'forgot_password/', data={'email': email})

    async def reset_password(self, token: str, new_password: str) -> Dict:
        """Reset password with token."""
        return await self._request('POST', 'reset_password/', data={
            'token': token,
            'new_password': new_password,
            'confirm_password': new_password,
        })

    async def change_password(self, current: str, new: str, auth_token: str) -> Dict:
        """Change password for authenticated user."""
        return await self._request('POST', 'change_password/', data={
            'current_password': current,
            'new_password': new,
            'confirm_password': new,
        }, auth_token=auth_token)

    async def me(self, auth_token: str) -> Dict:
        """Get current user."""
        return await self._request('GET', 'me/', auth_token=auth_token)

    async def check_email(self, email: str) -> bool:
        """Check if email exists."""
        result = await self._request('GET', 'check_email/', params={'email': email})
        return result.get('exists', False)

    async def check_phone(self, phone: str) -> bool:
        """Check if phone exists."""
        result = await self._request('GET', 'check_phone/', params={'phone': phone})
        return result.get('exists', False)

    async def resend_verification(self, email: str) -> Dict:
        """Resend verification email."""
        return await self._request('POST', 'resend_verification/', data={'email': email})


class ProfilesClient(BaseResourceClient):
    """Client for profile operations."""
    resource_name = 'profiles'

    async def get_by_user(self, user_id: str, auth_token: str = None) -> Dict:
        """Get profile by user ID."""
        return await self._request('GET', f'user/{user_id}/', auth_token=auth_token)


class OrganizationsClient(BaseResourceClient):
    """Client for organization operations."""
    resource_name = 'organizations'


class OpportunitiesClient(BaseResourceClient):
    """Client for opportunity operations."""
    resource_name = 'opportunities'

    async def list_active(self, params: dict = None) -> List[Dict]:
        """List active opportunities."""
        params = params or {}
        params['status'] = 'open'
        return await self.list(params=params)


class ApplicationsClient(BaseResourceClient):
    """Client for application operations."""
    resource_name = 'applications'

    async def apply(self, opportunity_id: str, data: dict, auth_token: str) -> Dict:
        """Apply to an opportunity."""
        data['opportunity'] = opportunity_id
        return await self.create(data, auth_token=auth_token)

    async def withdraw(self, application_id: str, auth_token: str) -> Dict:
        """Withdraw an application."""
        return await self._request('POST', f'{application_id}/withdraw/', auth_token=auth_token)


class TokensClient(BaseResourceClient):
    """Client for token operations."""
    resource_name = 'tokens'


# Synchronous wrapper for non-async contexts
class SyncDataLayerClient:
    """
    Synchronous wrapper for DataLayerClient.
    Use this in non-async Django views.
    """

    def __init__(self, config: DataLayerConfig = None):
        self.config = config or DataLayerConfig.from_env()
        self._client = None

    @classmethod
    def from_env(cls):
        return cls(DataLayerConfig.from_env())

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers=self._get_headers(),
            )
        return self._client

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.config.service_id:
            headers['X-Service-ID'] = self.config.service_id
        if self.config.api_key:
            headers['X-API-Key'] = self.config.api_key
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"/api/v1/{endpoint.lstrip('/')}"

        auth_token = kwargs.pop('auth_token', None)
        headers = {}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        response = self.client.request(method=method, url=url, headers=headers, **kwargs)

        if response.status_code >= 400:
            error_data = response.json() if response.content else {}
            raise DataLayerError(
                message=error_data.get('error', error_data.get('detail', 'Request failed')),
                status_code=response.status_code,
                details=error_data,
            )

        return response.json() if response.content else {}

    def close(self):
        if self._client:
            self._client.close()

    # User operations
    def register_user(self, data: dict) -> Dict:
        return self._request('POST', 'users/', json=data)

    def login(self, email: str, password: str) -> Dict:
        return self._request('POST', 'users/login/', json={'email': email, 'password': password})

    def verify_email(self, token: str) -> Dict:
        return self._request('POST', 'users/verify_email/', json={'token': token})

    def get_user(self, user_id: str, auth_token: str = None) -> Dict:
        return self._request('GET', f'users/{user_id}/', auth_token=auth_token)

    def check_email_exists(self, email: str) -> bool:
        result = self._request('GET', 'users/check_email/', params={'email': email})
        return result.get('exists', False)

