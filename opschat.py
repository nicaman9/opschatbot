import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tkinter import scrolledtext
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string
import os
import webbrowser
from PIL import Image, ImageTk, ImageDraw
import requests

class ChatbotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Operations Chatbot")
        self.root.geometry("800x600")  # Shrink the window size
        
        # Make window not resizable
        self.root.resizable(False, False)
        
        # Set background image
        try:
            # Load and resize the background image
            bg_image = Image.open("yellowjacketlogo.png")
            bg_image = bg_image.resize((800, 600), Image.LANCZOS)  # Resize to match new window size
            
            # Create a semi-transparent overlay
            overlay = Image.new('RGBA', (800, 600), (255, 255, 255, 77))  # 77 is 30% opacity (255 * 0.3)
            
            # Composite the images
            bg_image = bg_image.convert('RGBA')
            bg_image = Image.alpha_composite(bg_image, overlay)
            
            # Convert to PhotoImage
            self.bg_image = ImageTk.PhotoImage(bg_image)
            
            # Create a label with the background image
            self.bg_label = tk.Label(self.root, image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            
            # Load profile image for the bot
            profile_img = Image.open("yellowjacketlogo.png")
            # Resize to a small circle
            profile_img = profile_img.resize((40, 40), Image.LANCZOS)
            # Create a circular mask
            mask = Image.new('L', (40, 40), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 40, 40), fill=255)
            # Apply the mask
            output = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
            output.paste(profile_img, (0, 0))
            output.putalpha(mask)
            self.profile_image = ImageTk.PhotoImage(output)
        except Exception as e:
            print(f"Warning: Could not load images: {e}")
            self.profile_image = None
        
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('punkt_tab', quiet=True)
        except Exception as e:
            print(f"Warning: Could not download NLTK data: {e}")
            # Fallback to basic tokenization if NLTK fails
            self.use_nltk = False
        else:
            self.use_nltk = True
        
        # Load CSV files
        try:
            self.qa_data = pd.read_csv('qa.csv')
            self.procedures_data = pd.read_csv('procedures.csv')
            
            # Add link column if it doesn't exist
            if 'link' not in self.procedures_data.columns:
                self.procedures_data['link'] = ''
                self.procedures_data.to_csv('procedures.csv', index=False)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV files: {str(e)}")
            self.qa_data = pd.DataFrame(columns=['question', 'answer'])
            self.procedures_data = pd.DataFrame(columns=['procedure_name', 'steps', 'link'])
        
        # Initialize chat history with message objects
        self.chat_history = []
        
        # Store all search results for reference
        self.all_results = {"qa": [], "procedures": []}
        
        # Bot name
        self.bot_name = "Rocky"
        
        self.setup_gui()
        
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)  # Title row
        main_frame.rowconfigure(1, weight=1)  # Chat display row
        main_frame.rowconfigure(2, weight=0)  # Input frame row
        main_frame.rowconfigure(3, weight=0)  # Buttons frame row
        
        # Title frame to hold title and clear button
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        title_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(title_frame, text="Chatbot", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Clear chat button
        clear_chat_button = ttk.Button(title_frame, text="Clear Chat", command=self.clear_chat)
        clear_chat_button.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        # Admin button
        admin_button = ttk.Button(title_frame, text="Admin", command=self.show_admin_page)
        admin_button.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        # Chat display - reduce height to make room for buttons
        self.chat_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, width=80, height=25)
        self.chat_display.grid(row=1, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.chat_display.tag_configure("user", foreground="blue")
        self.chat_display.tag_configure("bot", foreground="green")
        self.chat_display.tag_configure("link", foreground="purple", underline=1)
        self.chat_display.tag_bind("link", "<Button-1>", self.handle_link_click)
        self.chat_display.tag_bind("link", "<Enter>", lambda e: self.chat_display.config(cursor="hand2"))
        self.chat_display.tag_bind("link", "<Leave>", lambda e: self.chat_display.config(cursor=""))
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        # Add label above input
        input_label = ttk.Label(input_frame, text="Ask a question or search for keywords:", font=("Arial", 10))
        input_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(0, 5))
        
        # Message entry
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(input_frame, textvariable=self.message_var, width=70)
        self.message_entry.grid(row=1, column=0, padx=5, sticky=(tk.W, tk.E))
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        # Send button
        send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        send_button.grid(row=1, column=1, padx=5)
        
        # Clear button
        clear_button = ttk.Button(input_frame, text="Clear", command=self.clear_input)
        clear_button.grid(row=1, column=2, padx=5)
        
        # Buttons frame - add more padding and ensure it's visible
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # "Something missing?" link
        missing_link = ttk.Label(buttons_frame, text="Something missing?", foreground="blue", cursor="hand2")
        missing_link.pack(side=tk.LEFT, padx=5)
        missing_link.bind("<Button-1>", self.show_missing_modal)
        
        # Ticket Creator button
        ticket_button = ttk.Button(buttons_frame, text="Ticket Creator", command=self.open_ticket_creator)
        ticket_button.pack(side=tk.LEFT, padx=5)
        
        # Turnover button
        turnover_button = ttk.Button(buttons_frame, text="Turnover", command=self.open_turnover)
        turnover_button.pack(side=tk.LEFT, padx=5)
        
        # Procedures button
        procedures_button = ttk.Button(buttons_frame, text="Procedures", command=self.open_procedures)
        procedures_button.pack(side=tk.LEFT, padx=5)
        
        # Tools button
        tools_button = ttk.Button(buttons_frame, text="Tools", command=self.show_tools_modal)
        tools_button.pack(side=tk.LEFT, padx=5)
        
        # Store current results for reference when clicking links
        self.current_results = {"qa": [], "procedures": []}
        
        # Welcome message
        self.add_bot_message("Hello! I'm your operations assistant. How can I help you today?")
        
    def clear_input(self):
        """Clear the input field"""
        self.message_var.set("")
        self.message_entry.focus()
        
    def open_turnover(self):
        # This function would open the turnover application
        # For now, we'll just show a message
        messagebox.showinfo("Turnover", "Opening Turnover application...")
        # In a real implementation, you would use:
        # os.system("python turnover.py") or
        # webbrowser.open("path/to/turnover.html")
        
    def open_procedures(self):
        # This function would open the procedures application
        # For now, we'll just show a message
        messagebox.showinfo("Procedures", "Opening Procedures application...")
        # In a real implementation, you would use:
        # os.system("python procedures.py") or
        # webbrowser.open("path/to/procedures.html")
        
    def open_ticket_creator(self):
        # This function would open the ticket creator application
        # For now, we'll just show a message
        messagebox.showinfo("Ticket Creator", "Opening Ticket Creator application...")
        # In a real implementation, you would use:
        # os.system("python ticket_creator.py") or
        # webbrowser.open("path/to/ticket_creator.html")
        
    def show_tools_modal(self):
        # Create a frame for the tools modal
        tools_frame = ttk.LabelFrame(self.chat_display, text="Tools")
        tools_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Create buttons for each tool
        for i in range(1, 11):
            tool_button = ttk.Button(tools_frame, text=f"Tool {i}", 
                                   command=lambda i=i: self.open_tool(i))
            tool_button.pack(pady=5, padx=10, fill=tk.X)
        
        # Close button
        close_button = ttk.Button(tools_frame, text="Close", 
                                command=tools_frame.destroy)
        close_button.pack(pady=10)
        
    def open_tool(self, tool_number):
        # This function would open the selected tool
        # For now, we'll just show a message
        messagebox.showinfo(f"Tool {tool_number}", f"Opening Tool {tool_number}...")
        # In a real implementation, you would use:
        # os.system(f"python tool_{tool_number}.py") or
        # webbrowser.open(f"path/to/tool_{tool_number}.html")
        
    def send_message(self):
        message = self.message_var.get().strip()
        if not message:
            return
            
        # Add user message to chat
        self.add_user_message(message)
        
        # Clear input
        self.message_var.set("")
        
        # Process message and get response
        self.process_message(message)
        
    def add_user_message(self, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "You: ", "user")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        # Store the message in chat history
        self.chat_history.append({
            "type": "user",
            "text": message,
            "tags": [("user", "end-2c linestart", "end-1c")]
        })
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def add_bot_message(self, message):
        self.chat_display.config(state=tk.NORMAL)
        
        # Create a frame for the bot message with profile image
        bot_frame = ttk.Frame(self.chat_display)
        self.chat_display.window_create(tk.END, window=bot_frame)
        
        # Add profile image if available
        if hasattr(self, 'profile_image') and self.profile_image:
            profile_label = ttk.Label(bot_frame, image=self.profile_image)
            profile_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add bot name and message
        self.chat_display.insert(tk.END, f"{self.bot_name}: ", "bot")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        # Store the message in chat history
        self.chat_history.append({
            "type": "bot",
            "text": message,
            "tags": [("bot", "end-2c linestart", "end-1c")]
        })
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def process_message(self, message):
        # Extract keywords from message
        keywords = self.extract_keywords(message)

        # Search in QA data
        qa_results = self.search_in_dataframe(self.qa_data, keywords)

        # Search in procedures data
        procedure_results = self.search_in_dataframe(self.procedures_data, keywords)

        # Store current results
        self.current_results["qa"] = qa_results
        self.current_results["procedures"] = procedure_results

        for result in qa_results:
            if result not in self.all_results["qa"]:
                self.all_results["qa"].append(result)

        for result in procedure_results:
            if result not in self.all_results["procedures"]:
                self.all_results["procedures"].append(result)

        if qa_results or procedure_results:
            self.chat_display.config(state=tk.NORMAL)

            bot_frame = ttk.Frame(self.chat_display)
            self.chat_display.window_create(tk.END, window=bot_frame)

            if hasattr(self, 'profile_image') and self.profile_image:
                profile_label = ttk.Label(bot_frame, image=self.profile_image)
                profile_label.pack(side=tk.LEFT, padx=(0, 5))

            self.chat_display.insert(tk.END, f"{self.bot_name}: ", "bot")

            message_tags = [("bot", "end-2c linestart", "end-1c")]

            self.chat_display.insert(tk.END, "Here's the most relevant result I found:\n\n")

            # Display best match
            if qa_results:
                best = qa_results[0]
                self.chat_display.insert(tk.END, f"Q: {best['question']}\nA: {best['answer']}\n\n")
            elif procedure_results:
                best = procedure_results[0]
                self.chat_display.insert(tk.END, f"Procedure: {best['procedure_name']}\nSteps: {best['steps']}\n\n")

            self.chat_display.insert(tk.END, "Other relevant entries:\n\n")

            # List all QA links
            if len(qa_results) > 0:
                self.chat_display.insert(tk.END, "Q&A Results:\n")
                for i, result in enumerate(qa_results):
                    all_index = self.all_results["qa"].index(result)
                    link_text = f"\u27a4 {result['question']}\n"
                    link_start = self.chat_display.index("end-1c")
                    self.chat_display.insert(tk.END, link_text, ("link", f"qa_{all_index}"))
                    link_end = self.chat_display.index("end-1c")
                    self.chat_display.insert(tk.END, "\n")
                    message_tags.append(("link", link_start, link_end))

            if len(procedure_results) > 0:
                self.chat_display.insert(tk.END, "\nProcedures:\n")
                for i, result in enumerate(procedure_results):
                    all_index = self.all_results["procedures"].index(result)
                    link_text = f"\u27a4 {result['procedure_name']}\n"
                    link_start = self.chat_display.index("end-1c")
                    self.chat_display.insert(tk.END, link_text, ("link", f"proc_{all_index}"))
                    link_end = self.chat_display.index("end-1c")
                    self.chat_display.insert(tk.END, "\n")
                    message_tags.append(("link", link_start, link_end))

            self.chat_display.insert(tk.END, "\nClick on any item above to see more details.\n\n")

            self.chat_history.append({
                "type": "bot",
                "text": "I found some information that might help:",
                "tags": message_tags,
                "results": {
                    "qa": qa_results,
                    "procedures": procedure_results
                }
            })

            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
        else:
            self.add_bot_message("I couldn't find any specific information about that. Would you like to try rephrasing your question?")

    def extract_keywords(self, message):
        if self.use_nltk:
            try:
                # Use NLTK for tokenization and stopword removal
                tokens = word_tokenize(message.lower())
                stop_words = set(stopwords.words('english'))
                keywords = [word for word in tokens if word not in stop_words and word not in string.punctuation]
            except Exception as e:
                print(f"Warning: NLTK processing failed: {e}")
                # Fallback to basic tokenization if NLTK processing fails
                words = message.lower().split()
                keywords = [word for word in words if len(word) > 2]  # Simple filter for short words
        else:
            # Fallback to basic tokenization
            words = message.lower().split()
            keywords = [word for word in words if len(word) > 2]  # Simple filter for short words
            
        return keywords
        
    def search_in_dataframe(self, df, keywords):
        results = []
        
        if df.empty:
            return results
            
        for index, row in df.iterrows():
            for column in df.columns:
                if isinstance(row[column], str):
                    text = row[column].lower()
                    if all(keyword in text for keyword in keywords):
                        results.append(row.to_dict())
                        break
                        
        return results
        
    def handle_link_click(self, event):
        # Get the clicked tags
        tags = self.chat_display.tag_names("current")
        for tag in tags:
            if tag.startswith("qa_"):
                index = int(tag.split("_")[1])
                self.show_qa_details(self.all_results["qa"][index], index)
            elif tag.startswith("proc_"):
                index = int(tag.split("_")[1])
                self.show_procedure_details(self.all_results["procedures"][index], index)
                
    def show_qa_details(self, qa_item, index):
        # Create a frame for details
        details_frame = ttk.LabelFrame(self.chat_display, text="Q&A Details")
        details_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Question
        ttk.Label(details_frame, text="Question:", font=("TkDefaultFont", 10, "bold")).pack(pady=(10,0), padx=10, anchor="w")
        question_text = tk.Text(details_frame, wrap=tk.WORD, height=2, width=50)
        question_text.insert("1.0", qa_item["question"])
        question_text.config(state=tk.DISABLED)
        question_text.pack(pady=(5,10), padx=10)
        
        # Answer
        ttk.Label(details_frame, text="Answer:", font=("TkDefaultFont", 10, "bold")).pack(pady=(0,0), padx=10, anchor="w")
        answer_text = tk.Text(details_frame, wrap=tk.WORD, height=8, width=50)
        answer_text.insert("1.0", qa_item["answer"])
        answer_text.config(state=tk.DISABLED)
        answer_text.pack(pady=5, padx=10)
        
        # Buttons frame
        button_frame = ttk.Frame(details_frame)
        button_frame.pack(pady=10)
        
        # Open link button
        open_link_button = ttk.Button(button_frame, text="Open in Browser", 
                                    command=lambda: webbrowser.open(f"https://example.com/qa/{index}"))
        open_link_button.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                command=details_frame.destroy)
        close_button.pack(side=tk.LEFT, padx=5)
        
    def show_procedure_details(self, procedure_item, index):
        # Create a frame for details
        details_frame = ttk.LabelFrame(self.chat_display, text="Procedure Details")
        details_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Procedure name
        ttk.Label(details_frame, text="Procedure:", font=("TkDefaultFont", 10, "bold")).pack(pady=(10,0), padx=10, anchor="w")
        name_text = tk.Text(details_frame, wrap=tk.WORD, height=2, width=50)
        name_text.insert("1.0", procedure_item["procedure_name"])
        name_text.config(state=tk.DISABLED)
        name_text.pack(pady=(5,10), padx=10)
        
        # Steps
        ttk.Label(details_frame, text="Steps:", font=("TkDefaultFont", 10, "bold")).pack(pady=(0,0), padx=10, anchor="w")
        steps_text = tk.Text(details_frame, wrap=tk.WORD, height=12, width=50)
        
        # Format steps nicely
        steps = procedure_item["steps"].split("2. ")
        formatted_steps = []
        for i, step in enumerate(steps):
            if i == 0:  # First step already has the number
                formatted_steps.append(step)
            else:
                formatted_steps.append(f"2. {step}")
        
        steps_text.insert("1.0", "\n".join(formatted_steps))
        steps_text.config(state=tk.DISABLED)
        steps_text.pack(pady=5, padx=10)
        
        # Buttons frame
        button_frame = ttk.Frame(details_frame)
        button_frame.pack(pady=10)
        
        # Open link button
        open_link_button = ttk.Button(button_frame, text="Open in Browser", 
                                    command=lambda: webbrowser.open(f"https://example.com/procedure/{index}"))
        open_link_button.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                command=details_frame.destroy)
        close_button.pack(side=tk.LEFT, padx=5)
        
    def show_missing_modal(self, event):
        # Create a frame for the missing information form
        modal_frame = ttk.LabelFrame(self.chat_display, text="Report Missing Information")
        modal_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Input field
        ttk.Label(modal_frame, text="Please describe what information is missing:").pack(pady=10)
        missing_text = scrolledtext.ScrolledText(modal_frame, wrap=tk.WORD, width=40, height=5)
        missing_text.pack(padx=10, pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(modal_frame)
        button_frame.pack(pady=10)
        
        # Submit button
        submit_button = ttk.Button(button_frame, text="Submit", 
                                 command=lambda: self.submit_missing(missing_text.get("1.0", tk.END), modal_frame))
        submit_button.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        clear_button = ttk.Button(button_frame, text="Clear", 
                                command=lambda: missing_text.delete("1.0", tk.END))
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                command=modal_frame.destroy)
        close_button.pack(side=tk.LEFT, padx=5)
        
    def submit_missing(self, message, modal_frame):
        try:
            # Email configuration
            sender_email = "nic20370@gmail.com" 
            receiver_email = "nicaman9@gmail.com" 
            password = "Serviceaccount1!"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = "Missing Information Report"
            
            body = f"Missing Information Report:\n\n{message}"
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
            server.quit()
            
            messagebox.showinfo("Success", "Report submitted successfully!")
            modal_frame.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send report: {str(e)}")

    def clear_chat(self):
        """Clear the chat display and reset chat history"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # Clear chat history
        self.chat_history = []
        
        # Clear all results
        self.all_results = {"qa": [], "procedures": []}
        
        # Add welcome message back
        self.add_bot_message("Hello! I'm your operations assistant. How can I help you today?")

    def show_admin_page(self):
        """Show the admin page for managing CSV files"""
        # Create login dialog
        login_window = tk.Toplevel(self.root)
        login_window.title("Admin Login")
        login_window.geometry("300x180")  # Increased height to ensure button visibility
        login_window.resizable(False, False)
        
        # Center the login window on the main window
        login_window.transient(self.root)
        login_window.grab_set()
        
        # Calculate position to center the login window on the main window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        login_width = 300
        login_height = 180
        
        x_position = main_x + (main_width - login_width) // 2
        y_position = main_y + (main_height - login_height) // 2
        
        login_window.geometry(f"{login_width}x{login_height}+{x_position}+{y_position}")
        
        # Login frame
        login_frame = ttk.Frame(login_window, padding="20")
        login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(login_frame, text="Username:").pack(anchor=tk.W)
        username_entry = ttk.Entry(login_frame, width=30)
        username_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Password
        ttk.Label(login_frame, text="Password:").pack(anchor=tk.W)
        password_entry = ttk.Entry(login_frame, width=30, show="*")
        password_entry.pack(fill=tk.X, pady=(0, 20))
        
        def check_credentials():
            username = username_entry.get()
            password = password_entry.get()
            
            if username == "dcs_ops_admin" and password == "admin":
                login_window.destroy()
                self.show_admin_panel()
            else:
                messagebox.showerror("Error", "Invalid credentials")
        
        # Login button
        ttk.Button(login_frame, text="Login", command=check_credentials).pack(pady=(0, 10))
        
        # Bind Enter key to login
        login_window.bind('<Return>', lambda e: check_credentials())
        
        # Focus username entry
        username_entry.focus()
        
    def show_admin_panel(self):
        """Show the admin panel after successful login"""
        admin_window = tk.Toplevel(self.root)
        admin_window.title("Admin Panel")
        admin_window.geometry("800x600")

                # Center the window
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()

        admin_width = 800
        admin_height = 600

        x_position = main_x + (main_width - admin_width) // 2
        y_position = main_y + (main_height - admin_height) // 2

        admin_window.geometry(f"{admin_width}x{admin_height}+{x_position}+{y_position}")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(admin_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Q&A Tab
        qa_frame = ttk.Frame(notebook)
        notebook.add(qa_frame, text="Q&A Management")
        
        # Q&A List
        qa_list_frame = ttk.Frame(qa_frame)
        qa_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        qa_list_label = ttk.Label(qa_list_frame, text="Q&A Entries:")
        qa_list_label.pack(anchor=tk.W)
        
        qa_listbox = tk.Listbox(qa_list_frame, width=50, height=20)
        qa_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Add "Create New" option at the top of Q&A list
        qa_listbox.insert(tk.END, "Create New")
        
        # Load Q&A entries
        for _, row in self.qa_data.iterrows():
            qa_listbox.insert(tk.END, row['question'])
        
        # Q&A Edit Frame
        qa_edit_frame = ttk.Frame(qa_frame)
        qa_edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(qa_edit_frame, text="Question:").pack(anchor=tk.W)
        qa_question_entry = ttk.Entry(qa_edit_frame, width=50)
        qa_question_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(qa_edit_frame, text="Answer:").pack(anchor=tk.W)
        qa_answer_text = tk.Text(qa_edit_frame, width=50, height=10)
        qa_answer_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Q&A Buttons
        qa_button_frame = ttk.Frame(qa_edit_frame)
        qa_button_frame.pack(fill=tk.X)
        
        def add_qa():
            question = qa_question_entry.get()
            answer = qa_answer_text.get("1.0", tk.END).strip()
            if question and answer:
                new_row = pd.DataFrame({'question': [question], 'answer': [answer]})
                self.qa_data = pd.concat([self.qa_data, new_row], ignore_index=True)
                self.qa_data.to_csv('qa.csv', index=False)
                qa_listbox.insert(tk.END, question)
                qa_question_entry.delete(0, tk.END)
                qa_answer_text.delete("1.0", tk.END)
                messagebox.showinfo("Success", "Q&A entry added successfully!")
        
        def update_qa():
            selection = qa_listbox.curselection()
            if selection:
                index = selection[0]
                # Skip if "Create New" is selected
                if index == 0:
                    add_qa()
                    return
                    
                # Adjust index for actual data (subtract 1 to account for "Create New")
                data_index = index - 1
                question = qa_question_entry.get()
                answer = qa_answer_text.get("1.0", tk.END).strip()
                if question and answer:
                    self.qa_data.iloc[data_index] = [question, answer]
                    self.qa_data.to_csv('qa.csv', index=False)
                    qa_listbox.delete(index)
                    qa_listbox.insert(index, question)
                    messagebox.showinfo("Success", "Q&A entry updated successfully!")
        
        def delete_qa():
            selection = qa_listbox.curselection()
            if selection:
                index = selection[0]
                # Skip if "Create New" is selected
                if index == 0:
                    return
                    
                # Adjust index for actual data (subtract 1 to account for "Create New")
                data_index = index - 1
                self.qa_data = self.qa_data.drop(data_index).reset_index(drop=True)
                self.qa_data.to_csv('qa.csv', index=False)
                qa_listbox.delete(index)
                qa_question_entry.delete(0, tk.END)
                qa_answer_text.delete("1.0", tk.END)
                messagebox.showinfo("Success", "Q&A entry deleted successfully!")
        
        def load_qa():
            selection = qa_listbox.curselection()
            if selection:
                index = selection[0]
                # Clear fields if "Create New" is selected
                if index == 0:
                    qa_question_entry.delete(0, tk.END)
                    qa_answer_text.delete("1.0", tk.END)
                    return
                    
                # Adjust index for actual data (subtract 1 to account for "Create New")
                data_index = index - 1
                qa_question_entry.delete(0, tk.END)
                qa_question_entry.insert(0, self.qa_data.iloc[data_index]['question'])
                qa_answer_text.delete("1.0", tk.END)
                qa_answer_text.insert("1.0", self.qa_data.iloc[data_index]['answer'])
        
        ttk.Button(qa_button_frame, text="Add", command=add_qa).pack(side=tk.LEFT, padx=5)
        ttk.Button(qa_button_frame, text="Update", command=update_qa).pack(side=tk.LEFT, padx=5)
        ttk.Button(qa_button_frame, text="Delete", command=delete_qa).pack(side=tk.LEFT, padx=5)
        
        qa_listbox.bind('<<ListboxSelect>>', lambda e: load_qa())
        
        # Procedures Tab
        proc_frame = ttk.Frame(notebook)
        notebook.add(proc_frame, text="Procedures Management")
        
        # Procedures List
        proc_list_frame = ttk.Frame(proc_frame)
        proc_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        proc_list_label = ttk.Label(proc_list_frame, text="Procedures:")
        proc_list_label.pack(anchor=tk.W)
        
        proc_listbox = tk.Listbox(proc_list_frame, width=50, height=20)
        proc_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Add "Create New" option at the top of Procedures list
        proc_listbox.insert(tk.END, "Create New")
        
        # Load Procedures
        for _, row in self.procedures_data.iterrows():
            proc_listbox.insert(tk.END, row['procedure_name'])
        
        # Procedures Edit Frame
        proc_edit_frame = ttk.Frame(proc_frame)
        proc_edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(proc_edit_frame, text="Procedure Name:").pack(anchor=tk.W)
        proc_name_entry = ttk.Entry(proc_edit_frame, width=50)
        proc_name_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(proc_edit_frame, text="Steps:").pack(anchor=tk.W)
        proc_steps_text = tk.Text(proc_edit_frame, width=50, height=10)
        proc_steps_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        ttk.Label(proc_edit_frame, text="Link:").pack(anchor=tk.W)
        proc_link_entry = ttk.Entry(proc_edit_frame, width=50)
        proc_link_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Procedures Buttons
        proc_button_frame = ttk.Frame(proc_edit_frame)
        proc_button_frame.pack(fill=tk.X)
        
        def validate_links():
            invalid_links = []
            for index, row in self.procedures_data.iterrows():
                if row['link']:
                    try:
                        response = requests.head(row['link'], timeout=5)
                        if response.status_code != 200:
                            invalid_links.append(f"{row['procedure_name']}: {row['link']} (Status: {response.status_code})")
                    except:
                        invalid_links.append(f"{row['procedure_name']}: {row['link']} (Connection failed)")
            
            if invalid_links:
                message = "The following links are invalid:\n\n" + "\n".join(invalid_links)
            else:
                message = "All links are valid!"
            messagebox.showinfo("Link Validation", message)
        
        def add_proc():
            name = proc_name_entry.get()
            steps = proc_steps_text.get("1.0", tk.END).strip()
            link = proc_link_entry.get()
            if name and steps:
                new_row = pd.DataFrame({'procedure_name': [name], 'steps': [steps], 'link': [link]})
                self.procedures_data = pd.concat([self.procedures_data, new_row], ignore_index=True)
                self.procedures_data.to_csv('procedures.csv', index=False)
                proc_listbox.insert(tk.END, name)
                proc_name_entry.delete(0, tk.END)
                proc_steps_text.delete("1.0", tk.END)
                proc_link_entry.delete(0, tk.END)
                messagebox.showinfo("Success", "Procedure added successfully!")
        
        def update_proc():
            selection = proc_listbox.curselection()
            if selection:
                index = selection[0]
                # Skip if "Create New" is selected
                if index == 0:
                    add_proc()
                    return
                    
                # Adjust index for actual data (subtract 1 to account for "Create New")
                data_index = index - 1
                name = proc_name_entry.get()
                steps = proc_steps_text.get("1.0", tk.END).strip()
                link = proc_link_entry.get()
                if name and steps:
                    self.procedures_data.iloc[data_index] = [name, steps, link]
                    self.procedures_data.to_csv('procedures.csv', index=False)
                    proc_listbox.delete(index)
                    proc_listbox.insert(index, name)
                    messagebox.showinfo("Success", "Procedure updated successfully!")
        
        def delete_proc():
            selection = proc_listbox.curselection()
            if selection:
                index = selection[0]
                # Skip if "Create New" is selected
                if index == 0:
                    return
                    
                # Adjust index for actual data (subtract 1 to account for "Create New")
                data_index = index - 1
                self.procedures_data = self.procedures_data.drop(data_index).reset_index(drop=True)
                self.procedures_data.to_csv('procedures.csv', index=False)
                proc_listbox.delete(index)
                proc_name_entry.delete(0, tk.END)
                proc_steps_text.delete("1.0", tk.END)
                proc_link_entry.delete(0, tk.END)
                messagebox.showinfo("Success", "Procedure deleted successfully!")
        
        def load_proc():
            selection = proc_listbox.curselection()
            if selection:
                index = selection[0]
                # Clear fields if "Create New" is selected
                if index == 0:
                    proc_name_entry.delete(0, tk.END)
                    proc_steps_text.delete("1.0", tk.END)
                    proc_link_entry.delete(0, tk.END)
                    return
                    
                # Adjust index for actual data (subtract 1 to account for "Create New")
                data_index = index - 1
                proc_name_entry.delete(0, tk.END)
                proc_name_entry.insert(0, self.procedures_data.iloc[data_index]['procedure_name'])
                proc_steps_text.delete("1.0", tk.END)
                proc_steps_text.insert("1.0", self.procedures_data.iloc[data_index]['steps'])
                proc_link_entry.delete(0, tk.END)
                proc_link_entry.insert(0, self.procedures_data.iloc[data_index]['link'])
        
        ttk.Button(proc_button_frame, text="Add", command=add_proc).pack(side=tk.LEFT, padx=5)
        ttk.Button(proc_button_frame, text="Update", command=update_proc).pack(side=tk.LEFT, padx=5)
        ttk.Button(proc_button_frame, text="Delete", command=delete_proc).pack(side=tk.LEFT, padx=5)
        ttk.Button(proc_button_frame, text="Validate Links", command=validate_links).pack(side=tk.LEFT, padx=5)
        
        proc_listbox.bind('<<ListboxSelect>>', lambda e: load_proc())

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatbotApp(root)
    root.mainloop() 
