from flask import Flask, render_template, request
import csv

app = Flask(__name__)

class Chatbot:
    def __init__(self):
        self.qa_file = 'qa.csv'
        self.procedures_file = 'procedures.csv'
    
    def get_answer(self, question):
        with open(self.qa_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['question'].lower() == question.lower():
                    return row['answer']
        return "Sorry, I don't have an answer for that question."
    
    def get_procedure(self, procedure_name):
        with open(self.procedures_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['procedure_name'].lower() == procedure_name.lower():
                    return row['procedure_description']
        return "Sorry, I don't have a procedure for that request."
    
    def handle_input(self, user_input):
        if user_input.lower().startswith("how do i"):
            procedure_name = user_input[len("How do I "):].strip()
            return self.get_procedure(procedure_name)
        elif "?" in user_input:
            return self.get_answer(user_input.strip())
        else:
            return "Sorry, I didn’t understand that. Can you please rephrase?"

chatbot = Chatbot()

@app.route("/", methods=["GET", "POST"])
def index():
    response = ""
    if request.method == "POST":
        user_input = request.form["user_input"]
        response = chatbot.handle_input(user_input)
    
    return render_template("index.html", response=response)

if __name__ == "__main__":
    app.run(debug=True)
