import os
import re
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

def clean_with_ai(html_content, title):
    """
    Uses OpenAI to intelligently strip boilerplate while preserving content structure and local images.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: No OpenAI API Key found. Skipping AI cleaning.")
        return html_content

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """
You are an expert editor for a printing press. 
Your job is to clean up HTML emails to be printed as a nice book.

RULES:
1. Remove all ads, navigation menus, "view in browser" links, "subscribe" buttons, and tracking pixels.
2. Remove the "Header" if it just repeats the email subject.
3. Remove footer boilerplate (unsubscribe links, address, privacy policy).
4. KEEP the main article content intact.
5. KEEP all <img> tags exactly as they are (do not change src attributes).
6. Return only the cleaned HTML <body> content. Do not include <html> or <head> tags.
7. Do not use Markdown backticks in your response. Just return the raw HTML.
"""},
                {"role": "user", "content": f"Title: {title}\n\nHTML Content:\n{html_content}"}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during AI cleaning: {e}")
        return html_content

def process_endnotes(soup):
    """
    Transforms footnotes into a collected 'Endnotes' section.
    Moves referenced footnote content to a specific container at the end.
    """
    # Map of ID -> Element for quick lookup
    ids = {tag['id']: tag for tag in soup.find_all(id=True)}
    
    # Find all anchors that look like footnote references
    anchors = list(soup.find_all('a', href=True))
    
    footnote_items = []
    processed_ids = set()
    
    for anchor in anchors:
        # Safety check: if anchor was part of a previously extracted footnote
        # and we decomposed it (e.g. back-links), its attrs might be gone.
        if not anchor.attrs or 'href' not in anchor.attrs:
            continue

        href = anchor['href']
        if not href.startswith('#'):
            continue
            
        target_id = href[1:]
        target_div = ids.get(target_id)
        
        # Verify it looks like a footnote reference
        text = anchor.get_text().strip()
        is_number = re.match(r'^\[?\(?\d+\)?\]?$', text)
        is_footnote_id = 'footnote' in target_id.lower() or 'fn' in target_id.lower() or 'ref' in target_id.lower()
        
        if target_div and (is_number or is_footnote_id):
            # Styling for the anchor (superscript)
            if not anchor.find('sup'):
                # Wrap text in sup if not already
                anchor_text = anchor.get_text()
                anchor.string = ""
                sup = soup.new_tag("sup")
                sup.string = anchor_text
                anchor.append(sup)
            
            # If we haven't processed this note yet, add it to our list
            if target_id not in processed_ids:
                processed_ids.add(target_id)
                
                # Extract the content
                note_content = target_div.extract()
                
                # Clean up the note content
                # Remove back-links if possible to clean up visual clutter in print
                for link in note_content.find_all('a'):
                    if link.get('href', '').startswith('#'):
                         # Often back links are just "^" or "return"
                         if len(link.get_text().strip()) < 3 or 'return' in link.get_text().lower():
                             link.decompose()
                
                # Ensure it's a block element
                if note_content.name not in ['div', 'p', 'li']:
                    wrapper = soup.new_tag("div")
                    wrapper.append(note_content)
                    note_content = wrapper
                
                note_content['class'] = note_content.get('class', []) + ['endnote-item']
                footnote_items.append(note_content)

    # If we found footnotes, append them to a new section at the end
    if footnote_items:
        # Create container
        endnotes_container = soup.new_tag("div", attrs={"class": "endnotes"})
        
        # Header
        header = soup.new_tag("h3")
        header.string = "Notes"
        endnotes_container.append(header)
        
        # Append all items
        for item in footnote_items:
            endnotes_container.append(item)
        
        # Append to body (or end of soup)
        if soup.body:
            soup.body.append(endnotes_container)
        else:
            soup.append(endnotes_container)

def clean_html(html_content, remove_title=None, author_name=None):
    """
    Basic cleanup of HTML content.
    Removes html/body tags to allow embedding in a larger template.
    Also strips out some potentially problematic style attributes.
    If remove_title is provided, attempts to remove a header matching that title.
    If author_name is provided, attempts to remove standalone author links.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "meta", "link", "noscript"]):
        script.extract()
    
    # Process footnotes/endnotes
    try:
        process_endnotes(soup)
    except Exception as e:
        print(f"Error processing endnotes: {e}")
    
    # Remove title if requested
    if remove_title:
        # Normalize comparison
        target_title = remove_title.strip().lower()
        
        # Check first h1 (and h2 just in case)
        found_title = False
        for header in soup.find_all(['h1', 'h2'], limit=2):
            if found_title:
                break
            
            # check direct text match
            header_text = header.get_text().strip().lower()
            
            # We check for exact match or if the header is contained in the title 
            # (or vice versa, but usually header is the title)
            # We use a threshold of similarity or simple inclusion if reasonable length
            if header_text and (header_text == target_title or 
                               (len(target_title) > 10 and target_title in header_text) or
                               (len(header_text) > 10 and header_text in target_title)):
                header.decompose()
                found_title = True
    
    # Enhanced Boilerplate Removal
    # We iterate over a list of potential boilerplate containers
    for element in soup.find_all(['p', 'div', 'span', 'h3', 'h4', 'blockquote']):
        text = element.get_text(" ", strip=True)
        text_lower = text.lower()
        
        # 1. Check for "Forwarded this email..."
        # Safety: Only remove if the element text is relatively short (e.g. < 300 chars)
        # to avoid deleting a parent container that holds the whole article + this line.
        if len(text) < 300 and "forwarded this email" in text_lower and "subscribe" in text_lower:
            element.decompose()
            continue

        # 2. Check for just punctuation like "..."
        # Matches strings that are only dots, spaces, or ellipses
        # Added check for single dot specifically which seems to be a common separator artifact
        if re.match(r'^[\.\s…]+$', text) or text.strip() == ".":
             element.decompose()
             continue
             
        # 3. Check for standalone dates (Month Day or Month Day, Year)
        # e.g. "Dec 19", "December 19, 2024"
        # We limit this to short strings to avoid deleting content starting with a date.
        # This regex matches generic date formats often seen in headers
        if len(text) < 25 and re.match(r'^[A-Z][a-z]{2,8}\s+\d{1,2}(?:,\s+\d{4})?$', text.strip()):
            element.decompose()
            continue
            
        # 4. Remove empty elements
        if not text:
            # Check if it has images or iframes before deleting
            if not element.find(['img', 'iframe']):
                 element.decompose()
                 continue
                 
        # 5. Remove "Paid" status markers
        # Matches "Paid", ". Paid", "· Paid", etc.
        if re.match(r'^[\.·•]?\s*Paid$', text.strip(), re.IGNORECASE):
            element.decompose()
            continue
            
        # 6. Remove standalone author links if they match the sender
        if author_name:
            # We try to match roughly. Author name from email might be "Matthew Yglesias"
            # Text might be "Matthew Yglesias" or "By Matthew Yglesias"
            clean_author = author_name.lower().replace("by ", "").strip()
            clean_text = text_lower.replace("by ", "").strip()
            
            # Use simple containment or exact match, BUT with length check to avoid deleting parent containers
            if len(clean_text) < len(clean_author) + 50 and clean_author and clean_text and (clean_author == clean_text or clean_author in clean_text):
                 # Check if it's primarily a link
                 if element.find('a') or element.name == 'a':
                     element.decompose()
                     continue

    # Remove common newsletter boilerplate
    # Substack specific elements
    for element in soup.find_all(class_=[
        "subscription-widget-wrap", 
        "post-footer", 
        "footer", 
        "comments-section",
        "share-dialog",
        "subscribe-footer",
        "simple-text-box", # Often used for 'Share' buttons
        "preview", # Email preview text (often hidden or invisible characters)
        "email-ufi-2-bottom", # Substack bottom bar
        "email-ufi-2-top", # Substack top bar/meta
        "post-meta", # Substack metadata (often redundant or just separators)
        "email-button-outline", # Generic buttons
        "email-button-text",
        "email-icon-button",
    ]):
        element.decompose()

    # Generic "Like", "Share", "Unsubscribe" text detection
    # This is a bit aggressive, so we target specific small blocks
    ad_markers = [
        "ads powered by",
        "adchoices",
        "sponsored by",
        "advertisement",
    ]

    footer_markers = [
        "share", "comment", "subscribe", "unsubscribe", 
        "update your preferences", "view in browser",
        "manage your email settings",
        "privacy policy", "terms of service", "california notices",
        "connect with us on", "all rights reserved",
        "received this email because", "stop receiving",
        "thanks for reading", "we’ll see you",
        "we'd like your feedback", "need help? review our",
        "the new york times company",
        "get the new york times app"
    ]

    for element in soup.find_all(['p', 'div', 'span', 'a', 'h3', 'h4', 'table', 'td', 'tr']):
        text = element.get_text(" ", strip=True).lower()
        
        # 1. Check for Ads
        if any(marker in text for marker in ad_markers):
             # Remove if it's a relatively small block (likely just the ad label or wrapper)
             # or if it explicitly says "ads powered by liveintent" which is definitely trash
             if len(text) < 200 or "ads powered by liveintent" in text:
                 element.decompose()
                 continue

        # 2. Check for Footer/Boilerplate
        # We enforce a length limit to avoid deleting the main content if it happens to contain a keyword
        if len(text) < 500:
            if any(marker in text for marker in footer_markers):
                element.decompose()
                continue
            
            # Specific check for NYT reporter lists which are often just names and emails
            # Pattern: Name, Title/Role, Location @handle
            if "@" in text and ("editor" in text or "reporter" in text) and len(text) < 200:
                # Only delete if it looks like a signature line (not a mention in text)
                # Heuristic: mostly names and titles
                element.decompose()
                continue

        # Remove elements that are just links to "Read in app"
        if "read in app" in text and len(text) < 50:
            element.decompose()
            continue

    # Remove tiny images (likely tracking pixels or icons)
    for img in soup.find_all('img'):
        # Safety check: ensure img is a Tag and has attributes
        if not hasattr(img, 'attrs') or img.attrs is None:
            continue
            
        width = img.get('width')
        height = img.get('height')
        # Check if dimensions are explicitly set and small
        # Safety check: width/height can be None or strings
        if width and str(width).isdigit() and int(width) <= 50:
            img.decompose()
        elif height and str(height).isdigit() and int(height) <= 50:
            img.decompose()

    # Remove isolated punctuation/separator nodes (like the standalone ".")
    # We iterate over all elements and check leaf nodes
    for element in soup.find_all(True):
        # Skip tags that usually contain no text but are important
        if element.name in ['img', 'br', 'hr', 'iframe', 'source', 'track', 'area', 'col', 'input', 'meta', 'link']:
            continue
            
        # Check if it's a leaf node (no children tags)
        if not element.find(True):
            text = element.get_text(strip=True)
            # Matches ".", " . ", "...", " .", "•", "∙" etc.
            # U+2219 is BULLET OPERATOR (∙), U+2022 is BULLET (•), U+00B7 is MIDDLE DOT (·)
            if text and (re.match(r'^[\.\s…•·∙]+$', text) or text == "."):
                element.decompose()
            
    # Final pass: Remove empty elements again (since we might have emptied some containers)
    for element in soup.find_all(['div', 'p', 'span', 'h3', 'h4', 'blockquote', 'table', 'tr', 'td']):
        if not element.get_text(strip=True):
             # Check for images/iframes/hr/br/inputs
             if not element.find(['img', 'iframe', 'hr', 'br', 'input']):
                 element.decompose()

    # Remove all style attributes to prevent weird CSS issues
    for tag in soup.find_all(True):
        if tag.has_attr('style'):
            del tag['style']
        
    # Get the content inside body if it exists, otherwise the whole thing
    if soup.body:
        content = soup.body
        # Unwrapper body tag
        content.name = "div"
        # content.attrs = {"class": "article-content"} # Removed to avoid nested columns
        return str(content)
    else:
        return f'<div>{str(soup)}</div>'

def text_to_html(text):
    """
    Convert plain text to basic HTML.
    """
    paragraphs = text.split('\n\n')
    html = ""
    for p in paragraphs:
        if p.strip():
            html += f"<p>{p.strip()}</p>"
    return html

def process_single_email(email):
    """
    Helper function to process a single email.
    """
    print(f"Processing: {email['subject']}")
    
    # Determine content source
    raw_html = email.get('html_body')
    raw_text = email.get('body')
    
    # Extract sender name for cleaning
    sender_name = email.get('sender', '')
    # Parse name from "Name <email>" format if needed
    if '<' in sender_name:
        sender_name = sender_name.split('<')[0].strip()
    
    if raw_html:
        # 1. Basic structural cleanup (remove scripts, styles)
        pre_cleaned = clean_html(raw_html, remove_title=email['subject'], author_name=sender_name)
        
        # 2. AI Polish (Optional but recommended)
        # We pass the pre-cleaned HTML to save tokens and help the AI focus
        if os.getenv("OPENAI_API_KEY"):
            print(f"  > AI Cleaning: {email['subject']}...")
            clean_body = clean_with_ai(pre_cleaned, email['subject'])
        else:
            clean_body = pre_cleaned
    else:
        clean_body = text_to_html(raw_text)
        
    return {
        'original_subject': email['subject'],
        'title': email['subject'],
        'author': sender_name,
        'date': email['date'],
        'summary': '',
        'content': clean_body,
        'images': email.get('images', [])
    }

def process_emails(emails_data):
    processed_articles = []
    
    print(f"Processing {len(emails_data)} emails in parallel...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks
        future_to_email = {executor.submit(process_single_email, email): email for email in emails_data}
        
        # Collect results as they complete
        for future in as_completed(future_to_email):
            try:
                article = future.result()
                processed_articles.append(article)
            except Exception as exc:
                print(f"Email processing generated an exception: {exc}")

    # Sort back by date (or original order) if needed. 
    # Currently we just append as they finish, so order might be scrambled.
    # Let's try to maintain original order if possible, or sort by date.
    # Assuming the input list is sorted by date/relevance, we might want to preserve that.
    
    # To preserve order, we can map the results back to the original index
    # But since the input emails_data is a list, we can just re-sort processed_articles
    # based on the order in emails_data if we had an ID. 
    # Simplest way: just rely on the fact that PDF generation iterates through them.
    # If order matters (e.g. latest first), we should sort.
    # The original 'emails_data' usually comes from Gmail API in date order.
    
    # Re-sort based on original list order
    email_subjects = [e['subject'] for e in emails_data]
    processed_articles.sort(key=lambda x: email_subjects.index(x['original_subject']) if x['original_subject'] in email_subjects else 999)
            
    return processed_articles
