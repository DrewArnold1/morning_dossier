import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json not found. Please download it from Google Cloud Console.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def get_attachment(service, user_id, msg_id, attachment_id, filename, store_dir):
    try:
        attachment = service.users().messages().attachments().get(
            userId=user_id, messageId=msg_id, id=attachment_id).execute()
        file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
        
        path = os.path.join(store_dir, filename)
        with open(path, 'wb') as f:
            f.write(file_data)
        return path
    except Exception as e:
        print(f"Error downloading attachment {filename}: {e}")
        return None

def parse_parts(service, user_id, msg_id, parts, store_dir, cid_map):
    body = ""
    html_body = ""
    
    for part in parts:
        mimeType = part.get('mimeType')
        filename = part.get('filename')
        part_id = part.get('partId')
        
        # Handle attachments/inline images
        if filename:
            body_data = part.get('body', {})
            attachment_id = body_data.get('attachmentId')
            if attachment_id:
                # Check for Content-ID for inline images
                headers = part.get('headers', [])
                content_id = next((h['value'] for h in headers if h['name'] == 'Content-ID'), None)
                
                # Sanitize filename
                safe_filename = f"{msg_id}_{part_id}_{filename}"
                # Download
                local_path = get_attachment(service, user_id, msg_id, attachment_id, safe_filename, store_dir)
                
                if content_id and local_path:
                    # content_id usually looks like <foo@bar>
                    clean_cid = content_id.strip('<>')
                    cid_map[clean_cid] = local_path

        # Handle text/html content
        if mimeType == 'text/plain' and not filename:
            data = part.get('body', {}).get('data')
            if data:
                body += base64.urlsafe_b64decode(data).decode('utf-8')
        elif mimeType == 'text/html' and not filename:
            data = part.get('body', {}).get('data')
            if data:
                html_body += base64.urlsafe_b64decode(data).decode('utf-8')
        
        # Recurse if multipart
        if part.get('parts'):
            sub_body, sub_html = parse_parts(service, user_id, msg_id, part.get('parts'), store_dir, cid_map)
            body += sub_body
            html_body += sub_html
            
    return body, html_body

def get_message_content(service, user_id, msg_id, store_dir='images'):
    if not os.path.exists(store_dir):
        os.makedirs(store_dir)
        
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
        payload = message.get('payload')
        headers = payload.get('headers')
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')

        cid_map = {}
        body = ""
        html_body = ""
        
        if payload.get('parts'):
            body, html_body = parse_parts(service, user_id, msg_id, payload.get('parts'), store_dir, cid_map)
        else:
            # Fallback for simple messages
            data = payload.get('body', {}).get('data')
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                if payload.get('mimeType') == 'text/html':
                    html_body = decoded
                else:
                    body = decoded
        
        # Replace CIDs in HTML
        if html_body:
            for cid, path in cid_map.items():
                # Replace cid:reference with local path
                # Note: WeasyPrint needs absolute paths usually, or file:// URIs
                abs_path = os.path.abspath(path)
                html_body = html_body.replace(f'cid:{cid}', f'file://{abs_path}')

        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body,
            'html_body': html_body,
            'images': list(cid_map.values())
        }
    except Exception as e:
        print(f"Error fetching message {msg_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_morning_dossier_emails(service, user_id='me', store_dir='images', max_results=None):
    try:
        results = service.users().messages().list(userId=user_id, q='label:morning-dossier').execute()
        messages = results.get('messages', [])
        
        email_data = []
        if not messages:
            print("No emails found with label 'morning-dossier'.")
        else:
            print(f"Found {len(messages)} emails.")
            
            # Apply limit if specified
            if max_results:
                messages = messages[:max_results]
                print(f"Limiting to first {max_results} emails.")

            for msg in messages:
                print(f"Fetching content for {msg['id']}...")
                content = get_message_content(service, user_id, msg['id'], store_dir)
                if content:
                    email_data.append(content)
        
        return email_data

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []
