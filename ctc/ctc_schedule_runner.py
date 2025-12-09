#!/usr/bin/env python3
"""
Schedule runner for automatic train dispatch.
Called by the CTC UI to run a schedule file in a separate process.
Usage: python ctc_schedule_runner.py <schedule_file_path>
"""

import sys
import os

# Ensure the ctc module is in the path
ctc_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(ctc_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if ctc_dir not in sys.path:
    sys.path.insert(0, ctc_dir)

# Change to the parent directory to ensure relative imports work correctly
os.chdir(parent_dir)

# Set up logging
log_file = os.path.join(ctc_dir, 'schedule_dispatch.log')
log = open(log_file, 'a')

def log_msg(msg):
    print(msg)
    print(msg, file=log)
    log.flush()

try:
    from ctc.ctc_main_temp import dispatch_schedule
    log_msg("[SCHEDULE RUNNER] Successfully imported dispatch_schedule")
except ImportError as e:
    log_msg(f"[SCHEDULE RUNNER] Import error: {e}")
    log_msg("[SCHEDULE RUNNER] Trying alternate import...")
    try:
        sys.path.insert(0, ctc_dir)
        from ctc_main_temp import dispatch_schedule
        log_msg("[SCHEDULE RUNNER] Successfully imported dispatch_schedule with alternate path")
    except ImportError as e2:
        log_msg(f"[SCHEDULE RUNNER] Fatal import error: {e2}")
        log.close()
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        log_msg("[SCHEDULE RUNNER] Error: No schedule file provided")
        log.close()
        sys.exit(1)
    
    schedule_file = sys.argv[1]
    log_msg(f"[SCHEDULE RUNNER] Schedule file argument: {schedule_file}")
    
    if not os.path.exists(schedule_file):
        log_msg(f"[SCHEDULE RUNNER] Error: Schedule file not found: {schedule_file}")
        log.close()
        sys.exit(1)
    
    log_msg(f"[SCHEDULE RUNNER] Starting schedule dispatch from: {schedule_file}")
    
    try:
        dispatch_schedule(schedule_file)
        log_msg("[SCHEDULE RUNNER] Schedule dispatch complete")
    except Exception as e:
        log_msg(f"[SCHEDULE RUNNER] Error during schedule dispatch: {e}")
        import traceback
        log_msg(traceback.format_exc())
        log.close()
        sys.exit(1)
    
    log.close()

if __name__ == "__main__":
    main()
