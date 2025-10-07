#!/usr/bin/env python3
"""
Check for users with profile pictures and identify missing files
"""
from utils.database import read_users
import os

def check_profile_images():
    """Check for users with profile pictures and identify missing files"""
    users = read_users()
    profile_users = [u for u in users if u.get('picture')]

    print(f'Users with profile pictures: {len(profile_users)}')

    missing_files = []
    existing_files = []

    for user in profile_users:
        picture_path = user.get('picture')
        if picture_path and picture_path.startswith('/uploads/profiles/'):
            # Extract filename from path
            filename = picture_path.replace('/uploads/profiles/', '')
            file_path = f'uploads/profiles/{filename}'

            if os.path.exists(file_path):
                existing_files.append(filename)
                print(f'  ✅ {user["id"]}: {filename}')
            else:
                missing_files.append(filename)
                print(f'  ❌ {user["id"]}: {filename} (MISSING)')

    print(f'\nSummary:')
    print(f'  Existing files: {len(existing_files)}')
    print(f'  Missing files: {len(missing_files)}')

    if missing_files:
        print(f'\nMissing files:')
        for filename in missing_files[:5]:  # Show first 5
            print(f'  - {filename}')
        if len(missing_files) > 5:
            print(f'  ... and {len(missing_files) - 5} more')

    return missing_files

if __name__ == "__main__":
    check_profile_images()
