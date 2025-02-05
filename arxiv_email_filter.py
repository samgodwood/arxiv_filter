#!/usr/bin/env python3

import imaplib
import email
import ssl
import re
import logging
from email.mime.text import MIMEText
import smtplib  
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables again, overriding if needed
load_dotenv(override=True)

# Fetch sensitive data and configuration
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

# Fetch non-sensitive configuration values from environment variables
search_criterion = os.getenv('SEARCH_CRITERION', '')
keywords = os.getenv('KEYWORDS', '').split(',')  # Convert the comma-separated string into a list


# Configure logging
logging.basicConfig(filename='arxiv_filter.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = 993
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465

def connect_imap():
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        logging.info("Connected to IMAP server successfully.")
        return mail
    except imaplib.IMAP4.error as e:
        logging.error(f"IMAP connection error: {e}")
        raise

def fetch_emails(mail, folder="INBOX"):
    try:
        mail.select(folder)  # Select the folder (INBOX by default)
        
        # Get today's date
        today = datetime.today().strftime('%d-%b-%Y')

        # search criterion to include the 'SINCE' filter for today
        search_criterion_with_date = f'({search_criterion} SINCE "{today}")'
        
        result, data = mail.search(None, search_criterion_with_date)  # Search emails
        if result != 'OK':
            logging.error("No emails found with the specified criteria.")
            return []
        email_ids = data[0].split()  # Split the data to get individual email IDs
        logging.info(f"Found {len(email_ids)} emails from today.")
        return email_ids  # Return the list of email IDs
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []  # Return an empty list in case of an error

def extract_papers(content):
    logging.info("Starting paper extraction...")

    content_size = len(content)
    logging.info(f"Email content size: {content_size} characters")

    papers = []

    # Use a regular expression to match multiple paper blocks in email content
    pattern = re.compile(r'arXiv:(\d+\.\d+)\s+Date:.*?Title:\s+(.*?)\s+Authors:\s+(.*?)\s+Categories:.*?\\(.*?)(https://arxiv.org/abs/\1)', re.DOTALL)
    
    matches = pattern.findall(content)
    logging.info(f"Found {len(matches)} papers.")

    for match in matches:
        arxiv_id = match[0].strip()
        title = match[1].strip()
        authors = match[2].strip()
        abstract = match[3].strip().replace('\n', ' ')

        papers.append({
            'arxiv_id': arxiv_id,
            'title': title,
            'authors': authors,
            'abstract': abstract
        })

    logging.info(f"Extracted {len(papers)} papers.")
    return papers


def parse_email(mail, email_id):
    logging.info(f"Starting to parse email with ID: {email_id}")
    try:
        result, data = mail.fetch(email_id, '(RFC822)')  # Fetch the email by ID
        if result != 'OK':
            logging.error(f"Failed to fetch email ID {email_id}")
            return None
        
        raw_email = data[0][1]  # Get the raw email content
        msg = email.message_from_bytes(raw_email)  # Parse the email content into a Message object
        
        content = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    content = part.get_payload(decode=True).decode('utf-8')  # Extract text/plain part
                    break
        else:
            content = msg.get_payload(decode=True).decode('utf-8')  # Extract plain text if not multipart
        
        papers = extract_papers(content)
        return papers
    except Exception as e:
        logging.error(f"Error parsing email ID {email_id}: {e}")
        return None

def filter_papers(papers, keywords):
    if not papers:
        return []
    
    # Normalize keywords to lowercase for case-insensitive comparison
    keywords = [kw.lower() for kw in keywords]
    
    filtered = []  # List to store papers that match any keyword
    
    # Check each paper for the presence of any keyword
    for paper in papers:
        # Combine title, abstract, and authors into a single string for easier searching
        combined_text = f"{paper['title']} {paper['abstract']} {paper['authors']}".lower()
        
        # If any keyword appears in the combined text, add the paper to the filtered list
        if any(kw in combined_text for kw in keywords):
            filtered.append(paper)
    
    return filtered 

def send_email(recipient, subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ACCOUNT
        msg["To"] = recipient

        # Set up connection with the SMTP server
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)  # Log in to the email server
            server.sendmail(EMAIL_ACCOUNT, recipient, msg.as_string())  # Send the email

        logging.info("Email sent successfully.")
    
    except Exception as e:
        logging.error(f"Error sending email: {e}")

# Main execution block
if __name__ == "__main__":
    try:
        logging.info("Connecting to the IMAP server...")
        mail = connect_imap()  

        logging.info("Fetching emails...")
        email_ids = fetch_emails(mail, folder="INBOX")  # Fetch 

        if email_ids:
            email_id = email_ids[0]  # Process l
            logging.info(f"Parsing email ID: {email_id}")
            papers = parse_email(mail, email_id)  # Extract 

            if papers:
                # Filter papers 
                filtered_papers = filter_papers(papers, keywords)

                if filtered_papers:
                    email_body = "Here are the filtered papers relevant to your research:\n\n"
                    for i, paper in enumerate(filtered_papers, start=1):
                        # Make abstracts less bulky by limiting to 500 chars
                        abstract_preview = paper['abstract'][:500] + "..." if len(paper['abstract']) > 500 else paper['abstract']
                        email_body += (f"Paper {i}:\n"
                                       f"Title: {paper['title']}\n"
                                       f"arXiv ID: {paper['arxiv_id']}\n"
                                       f"Authors: {paper['authors']}\n"
                                       f"Abstract: {abstract_preview}\n"
                                       + "-"*40 + "\n\n")
                else:
                    email_body = "No papers matched the provided keywords."

                # Send the email
                send_email(RECIPIENT_EMAIL, "Filtered Papers", email_body)
            else:
                logging.info("No papers found in the email.")
        else:
            logging.info("No emails found with the specified criteria.")
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")


