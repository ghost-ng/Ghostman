"""
Script to check if message saving is working.
Run this while Ghostman is running and after sending a message to the AI.
"""

import os
from pathlib import Path

# Get the log file location
log_file = Path.home() / "AppData" / "Local" / "Ghostman" / "logs" / "ghostman.log"

if not log_file.exists():
    print(f"Log file not found at: {log_file}")
    print("Trying alternate location...")
    log_file = Path("ghostman.log")

if not log_file.exists():
    print(f"Log file not found at: {log_file}")
    exit(1)

print(f"Reading log file: {log_file}")
print("="*80)

# Read the last 200 lines of the log
with open(log_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    last_lines = lines[-200:] if len(lines) > 200 else lines

# Filter for save-related messages
save_keywords = [
    "💾",
    "ATTEMPTING TO SAVE",
    "SAVE CALLBACK",
    "Saving",
    "save",
    "add_message",
    "Adding message",
    "message count"
]

print("SAVE-RELATED LOG MESSAGES:")
print("="*80)

found_any = False
for line in last_lines:
    if any(keyword in line for keyword in save_keywords):
        print(line.rstrip())
        found_any = True

if not found_any:
    print("NO SAVE-RELATED MESSAGES FOUND!")
    print()
    print("This means messages are NOT being saved.")
    print("The AI service's send_message() might not be calling _save_current_conversation().")
else:
    print()
    print("="*80)
    print("Found save-related messages above. Check if save callback shows success or error.")
