import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from PIL import Image
import cv2
from dotenv import load_dotenv
import google.generativeai as genai
from flask_cors import CORS
CORS(app)


load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash-latest',
    system_instruction="""
You are an AI health assistant. Always prefix your reply with:
***Disclaimer: I am an AI assistant and not a licensed medical professional. Always consult a doctor for serious concerns.***
Then provide:
1. Likely Diagnosis
2. Medication (Name, Use, Dosage, Duration)
3. Urgency Level (Low, Medium, High)
4. Recommendation (Should user visit doctor or not)
"""
)

# DB Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    test_type = db.Column(db.String(50))
    result = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error="Email already registered")
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    results = TestResult.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', results=results)

@app.route('/eye-test')
def eye_test():
    return render_template('eye_test.html')

@app.route('/color-test')
def color_test():
    return render_template('color_test.html')

@app.route('/astigmatism-test')
def astigmatism_test():
    return render_template('astigmatism_test.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/save-result', methods=['POST'])
@login_required
def save_result():
    data = request.get_json()
    test_type = data.get('testType')
    result = data.get('result')
    new_result = TestResult(user_id=current_user.id, test_type=test_type, result=result)
    db.session.add(new_result)
    db.session.commit()
    return jsonify({"status": "saved"})

@app.route('/analyze-symptom', methods=['POST'])
def analyze_symptom():
    symptom_text = request.form.get("symptom", "")
    image_file = request.files.get("image")

    if not symptom_text:
        return jsonify({"error": "Symptom description is required."}), 400

    prompt_parts = [symptom_text]

    if image_file:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(image_path)
        img = Image.open(image_path)
        prompt_parts.append(img)

    try:
        response = model.generate_content(prompt_parts)
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/capture')
def capture():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return jsonify({"error": "Webcam could not be accessed"}), 500

    ret, frame = cam.read()
    cam.release()

    if not ret:
        return jsonify({"error": "Failed to capture image"}), 500

    img_path = os.path.join(app.config['UPLOAD_FOLDER'], 'snapshot.jpg')
    cv2.imwrite(img_path, frame)

    return redirect(url_for('index'))  # Can modify to analyze if needed

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
