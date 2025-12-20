import os
import sys
from dotenv import load_dotenv
from gmail_service import get_gmail_service, fetch_morning_dossier_emails
from content_processor import process_emails
from pdf_generator import generate_pdf

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for Gmail credentials
    if not os.path.exists('credentials.json') and not os.path.exists('token.json'):
        print("Error: credentials.json not found.")
        print("Please download your OAuth 2.0 Client IDs JSON from Google Cloud Console")
        print("and save it as 'credentials.json' in this directory.")
        return

    print("Starting Morning Dossier...")

    # 1. Authenticate and Fetch Emails
    service = get_gmail_service()
    if not service:
        print("Failed to authenticate with Gmail.")
        return

    print("Fetching emails...")
    emails = fetch_morning_dossier_emails(service)
    
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

