from flask import Flask, jsonify, render_template, request, redirect, url_for, session,flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from helpers import login_required
import requests
from flask_session import Session
from pathlib import Path

users = {}

app = Flask(__name__)
app.secret_key = 'Enter API KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///users.db"
db = SQLAlchemy(app)
app.app_context().push()

#create model
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)

    #create a string
    def __repr__(self):
        return '<Users %r>' % self.id
    

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username', 'Guest'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']  

        if not username or not email or not password:
            flash('Please fill out all fields')
            return redirect(url_for('register'))

        user_exists = Users.query.filter_by(email=email).first()
        if user_exists:
            flash('User already exists with this email')
            return redirect(url_for('register'))

        new_user = Users(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
    
        return redirect('/')
   
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  

        user = Users.query.filter_by(username=username).first()
        if user and user.password == password:  
            session['user_id'] = user.id
            return redirect('/')
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/Image_gen', methods=['GET', 'POST'])
def Image_gen():
    if request.method == 'POST':
        prompt = request.form['prompt']
        return redirect(url_for('generate_image', prompt=prompt))
    return render_template('Image_gen.html')

@app.route('/Gen_image', methods=['POST'])
def generate_image():
    api_key = 'Enter API KEY'  
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'dall-e-2',
        'prompt': request.form.get('prompt'),
        'n': 1,
        'size': '1024x1024'
    }

    if not data['prompt']:
        return "No prompt provided", 400

    try:
        response = requests.post('https://api.openai.com/v1/images/generations', headers=headers, json=data)
        
        # Check if the response was successful
        if response.status_code != 200:
            return jsonify({"error": f"API request failed with status {response.status_code}: {response.text}"}), response.status_code
        
        response_json = response.json()
        
        # Ensure 'data' key exists in the response and it contains items
        if 'data' not in response_json or not response_json['data']:
            return jsonify({"error": "No data found in response"}), 500
        
        image_url = response_json['data'][0]['url']
        return f"<img src='{image_url}' alt='Generated Image'/>"
    
    except KeyError as e:
        return jsonify({"error": f"Missing key in response: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tts', methods=['GET', 'POST'])
def tts():
    if request.method == 'POST':
        input_text = request.form['text']
        return redirect(url_for('generate_speech', text=input_text))
    return render_template('tts.html')  # A HTML form for inputting the text

@app.route('/Gen_speech', methods=['POST'])
def generate_speech():
    text = request.form['text']
    if not text:
        return "No text provided", 400

    api_key = 'Enter API KEY'  
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'tts-1',
        'voice': 'alloy',
        'input': text
    }

    try:
        response = requests.post('https://api.openai.com/v1/audio/speech', headers=headers, json=data)
        response.raise_for_status()  # This will raise an exception for HTTP error responses

        # Save the response content as an audio file
        target_path = './_openai_output'
        Path(target_path).mkdir(parents=True, exist_ok=True)
        speech_file_path = Path(target_path) / "speech.mp3"
        with open(speech_file_path, 'wb') as f:
            f.write(response.content)

        # Return the audio file for download
        return send_file(str(speech_file_path), as_attachment=True, download_name='speech.mp3')
    except Exception as e:
        return render_template('error.html', error=str(e))  

if __name__ == '__main__':
    app.run(debug=True)