This script filters arXiv daily listing emails based on keywords, and sends a filtered summary to a designated email. 
It's mainly for my own use, so no warranty :)

##### To Use:
1. Sign up for daily arXiv emails (see https://info.arxiv.org/help/subscribe.html).
2. Set up the script to run daily (e.g., using crontab at 9am GMT).
3. Create a `.env` file with the following format:
    ```
    EMAIL_ACCOUNT=your_email 
    EMAIL_PASSWORD=your_app_password
    RECIPIENT_EMAIL=recipient_email
    SEARCH_CRITERION='FROM "no-reply@arxiv.org"'
    KEYWORDS="quantum computing,error correction"
    ```


