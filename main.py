import os
import sys
import json
import argparse
from dotenv import load_dotenv
from gmail_service import get_gmail_service, fetch_morning_dossier_emails
from content_processor import process_emails
from pdf_generator import generate_pdf

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate Morning Dossier PDF')
    parser.add_argument('--limit', type=int, help='Limit the number of emails to process')
    parser.add_argument('--cache', action='store_true', help='Use local cache for emails (avoid refetching)')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI processing for faster testing')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Handle AI toggle
    if args.no_ai:
        print("AI processing disabled.")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
    
    # Check for Gmail credentials (only if not using cache or cache empty)
    need_auth = True
    if args.cache and os.path.exists('email_cache.json'):
        need_auth = False

    service = None
    if need_auth:
        if not os.path.exists('credentials.json') and not os.path.exists('token.json'):
            print("Error: credentials.json not found.")
            print("Please download your OAuth 2.0 Client IDs JSON from Google Cloud Console")
            print("and save it as 'credentials.json' in this directory.")
            return

        print("Starting Morning Dossier...")
        # 1. Authenticate (if needed)
        service = get_gmail_service()
        if not service:
            print("Failed to authenticate with Gmail.")
            return

    # 1. Fetch Emails (from cache or Gmail)
    emails = []
    if args.cache and os.path.exists('email_cache.json'):
        print("Loading emails from local cache...")
        with open('email_cache.json', 'r') as f:
            emails = json.load(f)
        
        # Apply limit to cached emails if specified
        if args.limit:
             emails = emails[:args.limit]
             print(f"Limiting cached emails to {args.limit}")

    else:
        if not service:
             # Should be caught by auth check above, but safety first
             print("Service not available.")
             return

        print("Fetching emails from Gmail...")
        emails = fetch_morning_dossier_emails(service, max_results=args.limit)
        
        if args.cache:
            print("Saving emails to local cache...")
            with open('email_cache.json', 'w') as f:
                json.dump(emails, f, indent=2)
    
    if not emails:
        print("No emails found to process. Exiting.")
        return

    # 2. Process Content
    print("Processing content...")
    processed_articles = process_emails(emails)

    # 3. Generate PDF
    output_file = f"Morning_Dossier_{os.getenv('USER', 'User')}.pdf"
    if generate_pdf(processed_articles, output_file):
        print(f"\nSuccess! Your morning dossier is ready: {output_file}")
        # Open the PDF on Mac
        if sys.platform == 'darwin':
            os.system(f"open {output_file}")
    else:
        print("Failed to generate PDF.")

if __name__ == "__main__":
    main()
