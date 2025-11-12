#!/usr/bin/env python3
"""
Check if users are members of the Adopt Me group
Fast batch checker for 20k users
"""fefef


def lort():
    pass 


import requests
import csv
import json
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set

class AdoptMeChecker:
    def __init__(self, input_file: str, output_file: str = "adopt_me_results.csv",
                 threads: int = 10, delay: float = 0.1):
        """
        Initialize the Adopt Me checker.
        
        Args:
            input_file: CSV file with usernames (column: username)
            output_file: Output CSV file
            threads: Number of concurrent threads
            delay: Delay between requests per thread
        """
        self.input_file = input_file
        self.output_file = output_file
        self.threads = threads
        self.delay = delay
        
        # Adopt Me group ID
        self.adopt_me_group_id = 5596394
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.checked = 0
        self.found = 0
        self.errors = 0
        self.start_time = None
        
    def load_usernames(self) -> List[str]:
        """Load usernames from CSV file."""
        usernames = []
        
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                # Try to detect if it's CSV or just a list
                content = f.read()
                f.seek(0)
                
                if ',' in content or '\t' in content:
                    # It's a CSV
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Try common column names
                        username = (row.get('username') or row.get('Username') or 
                                  row.get('name') or row.get('Name') or 
                                  row.get('user') or list(row.values())[0])
                        if username:
                            usernames.append(username.strip())
                else:
                    # It's a plain text file, one username per line
                    f.seek(0)
                    usernames = [line.strip() for line in f if line.strip()]
                    
        except Exception as e:
            print(f"Error loading file: {e}")
            sys.exit(1)
        
        print(f"Loaded {len(usernames):,} usernames")
        return usernames
    
    def get_user_id(self, username: str) -> int:
        """Get user ID from username."""
        try:
            url = "https://users.roblox.com/v1/usernames/users"
            response = self.session.post(url, json={"usernames": [username]}, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('data') and len(data['data']) > 0:
                return data['data'][0].get('id')
            return None
        except Exception as e:
            return None
    
    def is_in_adopt_me_group(self, user_id: int) -> bool:
        """Check if user is in Adopt Me group."""
        try:
            url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for group in data.get('data', []):
                if group.get('group', {}).get('id') == self.adopt_me_group_id:
                    return True
            return False
        except Exception as e:
            return None
    
    def check_user(self, username: str) -> Dict:
        """Check if a single user is in Adopt Me group."""
        result = {
            'username': username,
            'user_id': None,
            'in_adopt_me': False,
            'error': None
        }
        
        try:
            # Get user ID
            user_id = self.get_user_id(username)
            
            if not user_id:
                result['error'] = 'User not found'
                return result
            
            result['user_id'] = user_id
            
            # Check group membership
            in_group = self.is_in_adopt_me_group(user_id)
            
            if in_group is None:
                result['error'] = 'API error'
                return result
            
            result['in_adopt_me'] = in_group
            
            # Small delay
            time.sleep(self.delay)
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def print_progress(self, total: int):
        """Print progress update."""
        if self.start_time is None:
            return
            
        elapsed = time.time() - self.start_time
        rate = self.checked / elapsed if elapsed > 0 else 0
        remaining = (total - self.checked) / rate if rate > 0 else 0
        
        progress_str = f"\rChecked: {self.checked}/{total} ({self.checked/total*100:.1f}%) | "
        progress_str += f"Found: {self.found} | Errors: {self.errors} | "
        progress_str += f"Rate: {rate:.1f}/s | "
        
        if elapsed < 60:
            progress_str += f"Elapsed: {elapsed:.0f}s"
        else:
            progress_str += f"Elapsed: {elapsed/60:.1f}m"
        
        if remaining > 0:
            if remaining < 60:
                progress_str += f" | ETA: {remaining:.0f}s"
            else:
                progress_str += f" | ETA: {remaining/60:.1f}m"
        
        sys.stdout.write(progress_str)
        sys.stdout.flush()
    
    def run(self):
        """Run the checker."""
        print("="*70)
        print("Adopt Me Player Checker")
        print("="*70)
        
        # Load usernames
        usernames = self.load_usernames()
        
        if not usernames:
            print("No usernames found!")
            return
        
        total = len(usernames)
        print(f"Checking {total:,} users against Adopt Me group...")
        print(f"Using {self.threads} threads")
        print()        
        self.start_time = time.time()
        
        # Open output file
        csv_file = open(self.output_file, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['username', 'user_id', 'in_adopt_me', 'error'])
        
        try:
            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                # Submit all tasks
                future_to_username = {
                    executor.submit(self.check_user, username): username 
                    for username in usernames
                }
                
                # Process results as they complete
                for future in as_completed(future_to_username):
                    result = future.result()
                    
                    # Write to CSV
                    csv_writer.writerow([
                        result['username'],
                        result['user_id'] or '',
                        'Yes' if result['in_adopt_me'] else 'No',
                        result['error'] or ''
                    ])
                    
                    # Update counters
                    self.checked += 1
                    if result['in_adopt_me']:
                        self.found += 1
                    if result['error']:
                        self.errors += 1
                    
                    # Print progress
                    self.print_progress(total)
            
            csv_file.close()
            
            # Final stats
            elapsed = time.time() - self.start_time
            print("\n")
            print("="*70)
            print("Checking completed!")
            print(f"Total checked: {self.checked:,}")
            print(f"Found in Adopt Me: {self.found:,} ({self.found/total*100:.1f}%)")
            print(f"Errors: {self.errors:,}")
            print(f"Total time: {elapsed/60:.1f} minutes")
            print(f"Average rate: {self.checked/elapsed:.1f} users/second")
            print(f"Results saved to: {self.output_file}")
            print("="*70)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            csv_file.close()
        except Exception as e:
            print(f"\n\nError: {e}")
            csv_file.close()


def main():
    parser = argparse.ArgumentParser(
        description='Check if users are in the Adopt Me group',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check users from a CSV file
  python check_adopt_me_players.py usernames.csv
  
  # Use more threads for faster checking
  python check_adopt_me_players.py usernames.csv --threads 20
  
  # Custom output file
  python check_adopt_me_players.py usernames.csv --output results.csv
  
Input file format:
  - CSV with a "username" column, OR
  - Plain text file with one username per line
        """
    )
    
    parser.add_argument(
        'input_file',
        type=str,
        help='Input file with usernames (CSV or plain text)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='adopt_me_results.csv',
        help='Output CSV file (default: adopt_me_results.csv)'
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=10,
        help='Number of concurrent threads (default: 10, max recommended: 20)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.1,
        help='Delay between requests per thread in seconds (default: 0.1)'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    checker = AdoptMeChecker(
        input_file=args.input_file,
        output_file=args.output,
        threads=args.threads,
        delay=args.delay
    )
    
    checker.run()


if __name__ == '__main__':
    main()
