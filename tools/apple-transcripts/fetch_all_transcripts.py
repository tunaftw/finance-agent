#!/usr/bin/env python3
"""
Automate fetching Apple Podcast transcripts via UI automation.

Requirements:
1. Enable Accessibility for Terminal/iTerm in System Settings > Privacy & Security > Accessibility
2. Have Börspodden (or target podcast) in your Apple Podcasts library
3. pip install pyautogui (optional, for mouse automation)

Usage:
    python fetch_all_transcripts.py [--count 50] [--delay 3]
"""

import argparse
import subprocess
import time
import sys


def run_applescript(script: str) -> str:
    """Run AppleScript and return output."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript error: {result.stderr}")
    return result.stdout.strip()


def activate_podcasts():
    """Bring Podcasts app to foreground."""
    run_applescript('tell application "Podcasts" to activate')
    time.sleep(1)


def press_key(key: str, modifier: str = None):
    """Press a key using AppleScript."""
    if modifier:
        script = f'''
        tell application "System Events"
            keystroke "{key}" using {modifier} down
        end tell
        '''
    else:
        script = f'''
        tell application "System Events"
            keystroke "{key}"
        end tell
        '''
    run_applescript(script)


def press_key_code(code: int, modifier: str = None):
    """Press a key code using AppleScript."""
    if modifier:
        script = f'''
        tell application "System Events"
            key code {code} using {modifier} down
        end tell
        '''
    else:
        script = f'''
        tell application "System Events"
            key code {code}
        end tell
        '''
    run_applescript(script)


def click_transcript_button():
    """
    Try to click the transcript button.

    In Apple Podcasts, the transcript button should be in the Now Playing view.
    We'll try keyboard shortcuts first, then mouse position if available.
    """
    # Try Cmd+Shift+T (common transcript shortcut - may not work)
    try:
        press_key("t", "command down, shift")
        return True
    except:
        pass

    # Alternative: Try clicking at known position (requires calibration)
    try:
        import pyautogui
        # These coordinates need to be calibrated for your screen
        # Typically the transcript button is in the bottom player bar
        # You may need to adjust these values
        pyautogui.click(x=880, y=850)  # Example coordinates
        return True
    except ImportError:
        print("pyautogui not installed - cannot use mouse automation")
        return False
    except Exception as e:
        print(f"Mouse click failed: {e}")
        return False


def navigate_to_podcast(podcast_name: str = "Börspodden"):
    """Navigate to a specific podcast in the library."""
    # Use Cmd+F to search
    press_key("f", "command")
    time.sleep(0.5)

    # Type podcast name
    script = f'''
    tell application "System Events"
        keystroke "{podcast_name}"
    end tell
    '''
    run_applescript(script)
    time.sleep(1)

    # Press Enter to select
    press_key_code(36)  # Return key
    time.sleep(1)


def next_episode():
    """Navigate to next episode."""
    # Down arrow to next episode
    press_key_code(125)  # Down arrow
    time.sleep(0.5)


def play_episode():
    """Start playing current episode (needed to show transcript)."""
    press_key_code(49)  # Space bar
    time.sleep(0.5)


def pause_episode():
    """Pause current episode."""
    press_key_code(49)  # Space bar


def main():
    parser = argparse.ArgumentParser(description="Fetch Apple Podcast transcripts")
    parser.add_argument("--count", type=int, default=10, help="Number of episodes to process")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between episodes (seconds)")
    parser.add_argument("--podcast", default="Börspodden", help="Podcast name to search for")
    parser.add_argument("--start-episode", type=int, default=0, help="Episode index to start from")
    args = parser.parse_args()

    print(f"Will process {args.count} episodes from '{args.podcast}'")
    print(f"Delay between episodes: {args.delay}s")
    print()
    print("IMPORTANT:")
    print("1. Make sure Terminal has Accessibility permissions")
    print("   System Settings > Privacy & Security > Accessibility")
    print("2. Podcasts app should be open and show should be visible")
    print()
    input("Press Enter to start (Ctrl+C to cancel)...")

    try:
        activate_podcasts()
        time.sleep(1)

        # Navigate to podcast
        print(f"\nNavigating to {args.podcast}...")
        navigate_to_podcast(args.podcast)
        time.sleep(2)

        # Skip to start episode
        for i in range(args.start_episode):
            next_episode()
            time.sleep(0.2)

        # Process episodes
        for i in range(args.count):
            print(f"\nProcessing episode {i + 1 + args.start_episode}/{args.count + args.start_episode}...")

            # Select and play episode briefly
            press_key_code(36)  # Enter to open episode
            time.sleep(1)

            play_episode()
            time.sleep(0.5)

            # Try to open transcript
            if click_transcript_button():
                print(f"  Transcript requested")
                time.sleep(args.delay)  # Wait for transcript to load/cache
            else:
                print(f"  Could not click transcript button")

            pause_episode()

            # Go back and to next episode
            press_key_code(53)  # Escape to go back
            time.sleep(0.5)
            next_episode()
            time.sleep(0.3)

        print(f"\nDone! Processed {args.count} episodes.")
        print("Run 'podstock transcribe --source apple' to extract the cached transcripts.")

    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("1. Terminal has Accessibility permissions")
        print("2. Podcasts app is open")
        sys.exit(1)


if __name__ == "__main__":
    main()
