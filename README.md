# Operations Chatbot

A Python-based chatbot application with a Tkinter GUI that helps users search through Q&A and procedures data.

## Features

- Search through Q&A and procedures data
- Keyword-based search functionality
- User-friendly GUI interface
- "Something missing?" feature to report missing information
- Email notification system for missing information reports
- Admin panel for managing Q&A and procedures data
- Non-resizable window with background image
- Conversation bubble-style chat interface
- Clear chat functionality
- Ticket Creator, Turnover, and Procedures buttons

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create two CSV files in the same directory as the script:
   - `qa.csv`: Contains Q&A data
   - `procedures.csv`: Contains procedures data

3. Configure the email settings in the `chatbot.py` file:
   - Replace `your-email@example.com` with your email address
   - Replace `admin@example.com` with the admin email address
   - Replace `your-password` with your email password

## Usage

1. Run the application:
```bash
python chatbot.py
```

2. Enter your search query in the search box and click "Send"
3. Results will be displayed in the chat display area
4. Click on any result to see more details
5. If you find missing information, click the "Something missing?" link to report it

## Admin Panel

The chatbot includes an admin panel for managing Q&A and procedures data:

1. Click the "Admin" button in the top-right corner
2. Login with the following credentials:
   - Username: dcs_ops_admin
   - Password: admin
3. In the admin panel, you can:
   - Add, update, and delete Q&A entries
   - Add, update, and delete procedures
   - Validate links in procedures
   - Create new entries by selecting "Create New" from the list
