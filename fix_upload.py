#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Temporary script to fix the data upload issue"""

import os

file_path = 'main/views/data_upload_views.py'

# Get the current directory
current_dir = os.getcwd()
print(f"Current directory: {current_dir}")
print(f"File path: {file_path}")
print(f"Full path: {os.path.abspath(file_path)}")

if not os.path.exists(file_path):
    print(f"ERROR: File not found at {os.path.abspath(file_path)}")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the problematic line
modified = False
for i, line in enumerate(lines):
    if "if pd.isna(value) or value == '' or value == 0:" in line:
        print(f"Found line {i+1}: {line.strip()}")
        lines[i] = "                    # Skip only empty or null values (allow 0 values to be processed)\n"
        lines.insert(i+1, "                    if pd.isna(value) or value == '':\n")
        modified = True
        print(f"Replaced with: {lines[i].strip()}")
        print(f"New line: {lines[i+1].strip()}")
    elif "for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']:" in line:
        print(f"Found line {i+1}: {line.strip()}")
        lines[i] = "                # Add support for formats like '01-Nov-25', '01-Nov-2025', etc.\n"
        lines.insert(i+1, "                for fmt in ['%d-%b-%y', '%d-%b-%Y', '%d/%b/%y', '%d/%b/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:\n")
        modified = True
        print(f"Replaced date format line")
    elif "date_obj = pd.to_datetime(date_str).date()" in line and "dayfirst" not in line:
        print(f"Found line {i+1}: {line.strip()}")
        # Check if previous line is a comment
        if i > 0 and "#" in lines[i-1]:
            lines[i] = "                        # Try pandas' flexible date parser as fallback (handles various formats)\n"
            lines.insert(i+1, "                        date_obj = pd.to_datetime(date_str, dayfirst=True).date()\n")
        else:
            lines[i] = lines[i].replace("date_obj = pd.to_datetime(date_str).date()", 
                                        "# Try pandas' flexible date parser as fallback (handles various formats)\n                        date_obj = pd.to_datetime(date_str, dayfirst=True).date()")
        modified = True
        print(f"Replaced date parsing line")

if modified:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("\nFile updated successfully!")
    print("Changes made:")
    print("1. Removed check that skips 0 values")
    print("2. Added support for date formats like '01-Nov-25'")
    print("3. Improved fallback date parsing")
else:
    print("\nNo changes were needed - file may already be updated or patterns not found")
