#!/usr/bin/env python3
"""
GrowCommunity Setup Script
This script helps you set up GrowCommunity for development.
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """Run a command and display its description."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description.lower()}: {e}")
        print(f"Error output: {e.stderr}")
        return None

def main():
    print("🌟 Welcome to GrowCommunity Setup!")
    print("This script will help you set up the application for development.\n")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print("❌ Python 3.8 or higher is required.")
        sys.exit(1)
    
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
    
    # Check if we're in the correct directory
    if not os.path.exists('manage.py'):
        print("❌ Please run this script from the growcommunity project directory (where manage.py is located)")
        sys.exit(1)
    
    # Install dependencies
    run_command("pip install -r requirements.txt", "Installing Python dependencies")
    
    # Run migrations
    run_command("python manage.py migrate", "Setting up database")
    
    # Create superuser
    print("\n🔄 Creating admin user...")
    print("Please provide admin credentials:")
    run_command("python manage.py createsuperuser", "Creating admin user")
    
    # Setup initial data
    run_command("python manage.py setup_initial_data", "Setting up initial data")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run: python manage.py runserver")
    print("2. Visit: http://127.0.0.1:8000/")
    print("3. Admin panel: http://127.0.0.1:8000/admin/")
    print("\n💡 To create invite links, log into admin and go to Invites section")
    print("📖 Check README.md for detailed usage instructions")

if __name__ == "__main__":
    main()