# -*- coding: utf-8 -*-
"""
ForgeForth Africa Data Layer - Startup Script
=============================================
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run the data layer service."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    base_dir = Path(__file__).resolve().parent
    host = os.getenv('DATA_LAYER_HOST', '0.0.0.0')
    port = os.getenv('DATA_LAYER_PORT', '9010')
    env = os.getenv('DATA_LAYER_ENV', 'development')

    print("=" * 60)
    print("  ForgeForth Africa - Data Layer Service")
    print("=" * 60)
    print(f"  Environment: {env}")
    print(f"  Host: {host}:{port}")
    print("=" * 60)

    # Run migrations
    print("\n[1/3] Running migrations...")
    subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], cwd=base_dir)

    # Collect static files in production
    if env == 'production':
        print("\n[2/3] Collecting static files...")
        subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], cwd=base_dir)
    else:
        print("\n[2/3] Skipping static collection (development)")

    # Start server
    print(f"\n[3/3] Starting server on {host}:{port}...")

    if env == 'production':
        # Use gunicorn in production
        subprocess.run([
            'gunicorn',
            'config.wsgi:application',
            f'--bind={host}:{port}',
            '--workers=4',
            '--timeout=120',
            '--access-logfile=-',
            '--error-logfile=-',
        ], cwd=base_dir)
    else:
        # Use Django dev server in development
        subprocess.run([
            sys.executable,
            'manage.py',
            'runserver',
            f'{host}:{port}'
        ], cwd=base_dir)


if __name__ == '__main__':
    main()

