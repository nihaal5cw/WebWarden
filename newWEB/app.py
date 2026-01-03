from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_mail import Mail, Message
import os
import json
import openai

app = Flask(__name__)

# Flask-Mail Configuration (Using Environment Variables for Security)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# OpenAI API Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# JSON file for persistent storage
DATA_FILE = "outpass_requests.json"

def generate_ai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"Generate a formal outpass request explanation for the reason: {prompt}"}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "AI response unavailable."

def load_requests():
    """Load existing requests from the JSON file."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_requests(requests):
    """Save updated requests to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(requests, f, indent=4)

# Load existing requests
outpass_requests = load_requests()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        student_name = request.form.get('studentName')
        roll_number = request.form.get('rollNumber')
        student_mobile = request.form.get('studentMobile')
        parent_mobile = request.form.get('parentMobile')
        reason = request.form.get('reason')
        student_email = request.form.get('studentEmail')  # FIXED

        request_index = len(outpass_requests)

        outpass_requests.append({
            'student_name': student_name,
            'roll_number': roll_number,
            'student_mobile': student_mobile,
            'parent_mobile': parent_mobile,
            'reason': reason,
            'status': 'Pending',
            'student_email': student_email  # FIXED
        })

        save_requests(outpass_requests)

        ai_generated_response = generate_ai_response(reason)

        send_approval_email(student_name, roll_number, student_mobile, parent_mobile, reason, request_index, ai_generated_response)

        return redirect(url_for('status'))  # FIXED
    except Exception as e:
        return f"An error occurred: {str(e)}"


@app.route('/status')
def status():
    return render_template('status.html', requests=outpass_requests)

@app.route('/approve/<int:request_index>')
def approve_request(request_index):
    print("Approve clicked for index:", request_index)
    if 0 <= request_index < len(outpass_requests):
        request_data = outpass_requests[request_index]
        request_data['status'] = 'Approved'

        notify_student(
            student_email=request_data['student_email'],
            student_name=request_data['student_name'],
            status='approved'
        )

        save_requests(outpass_requests)

    return redirect(url_for('status'))

@app.route('/reject/<int:request_index>')
def reject_request(request_index):
    print("Approve clicked for index:", request_index)
    if 0 <= request_index < len(outpass_requests):
        request_data = outpass_requests[request_index]
        request_data['status'] = 'Rejected'

        notify_student(
            student_email=request_data['student_email'],
            student_name=request_data['student_name'],
            status='rejected'
        )

        save_requests(outpass_requests)

    return redirect(url_for('status'))

def send_approval_email(student_name, roll_number, student_mobile, parent_mobile, reason, request_index, ai_generated_response):
    try:
        approve_url = url_for('approve_request', request_index=request_index, _external=True)
        reject_url = url_for('reject_request', request_index=request_index, _external=True)

        msg = Message(
            subject=f"Outpass Request from {student_name}",
            recipients=["warden@example.com"],  # Update to real warden email
        )

        msg.body = (
            f"New Outpass Request:\n\n"
            f"Name: {student_name}\n"
            f"Roll Number: {roll_number}\n"
            f"Student Mobile: {student_mobile}\n"
            f"Parent Mobile: {parent_mobile}\n"
            f"Reason: {reason}\n\n"
            f"AI-Suggested Message:\n{ai_generated_response}\n\n"
            f"Approve: {approve_url}\n"
            f"Reject: {reject_url}\n"
        )

        mail.send(msg)
        print("Email sent to warden successfully!")
    except Exception as e:
        print(f"Error sending email to warden: {e}")

def notify_student(student_email, student_name, status):
    try:
        msg = Message(
            subject="Outpass Request Status",
            recipients=[student_email],
        )
        msg.body = (
            f"Hello {student_name},\n\n"
            f"Your outpass request has been {status}.\n\n"
            f"Regards,\nHostel Management"
        )
        mail.send(msg)
        print(f"Notification sent to {student_email}")
    except Exception as e:
        print(f"Error sending status email to student: {e}")

if __name__ == '__main__':
    app.run(debug=True)
