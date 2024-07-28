from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import openai
import os
import random
import requests
from datetime import datetime
import logging

# Initialize Flask app
app = Flask(__name__, static_url_path='', static_folder='.', template_folder='.')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Sofia:CPS3320@localhost/art_collection'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define ArtPiece model
class ArtPiece(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    medium = db.Column(db.String(100), nullable=False)
    year = db.Column(db.String(4), nullable=False)

# Create the database
with app.app_context():
    db.create_all()

# Set OpenAI API key
# openai.api_key = ''

# Define the painters dictionary
painters = {
    "Leonardo da Vinci": 67,
    "Vincent van Gogh": 37,
    "Pablo Picasso": 91,
    "Claude Monet": 86,
    "Rembrandt": 63,
    "Michelangelo": 88,
    "Salvador Dali": 84,
    "Frida Kahlo": 47,
    "Edvard Munch": 80,
    "Georgia O'Keeffe": 98
}

correct_guesses = []
incorrect_guesses = []

EVENTBRITE_API_KEY = '5EUXCVIWDSSPI5IYUHE3'

@app.route('/')
def index():
    art_pieces = ArtPiece.query.all()
    art_images = fetch_art_images()
    return render_template('index.html', art_pieces=art_pieces, art_images=art_images)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    session['username'] = username
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/memory_game')
def memory_game():
    art_images = fetch_art_images()
    # Duplicate each image to create pairs
    art_pairs = art_images * 2
    # Shuffle the pairs
    random.shuffle(art_pairs)
    return render_template('memory_game.html', art_pairs=art_pairs)

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_message = request.json.get('message')

    if not user_message:
        return jsonify({"response": "Please provide a message."})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response['choices'][0]['message']['content'].strip()
    except Exception as e:
        reply = f"Sorry, I couldn't process your request. Error: {e}"

    return jsonify({"response": reply})

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        artist = request.form['artist']
        medium = request.form['medium']
        year = request.form['year']
        new_art = ArtPiece(title=title, artist=artist, medium=medium, year=year)
        db.session.add(new_art)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:art_id>', methods=['GET', 'POST'])
def edit(art_id):
    art_piece = ArtPiece.query.get_or_404(art_id)
    if request.method == 'POST':
        art_piece.title = request.form['title']
        art_piece.artist = request.form['artist']
        art_piece.medium = request.form['medium']
        art_piece.year = request.form['year']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', art_piece=art_piece, art_id=art_id)

@app.route('/delete/<int:art_id>', methods=['GET'])
def delete(art_id):
    art_piece = ArtPiece.query.get_or_404(art_id)
    db.session.delete(art_piece)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/refresh')
def refresh():
    art_images = fetch_art_images()
    art_pieces = ArtPiece.query.all()
    return render_template('index.html', art_pieces=art_pieces, art_images=art_images)

@app.route('/guessing_game', methods=['GET', 'POST'])
def guessing_game():
    if request.method == 'GET':
        painter = random.choice(list(painters.keys()))
        return render_template('guessing_game.html', painter=painter)
    elif request.method == 'POST':
        painter = request.form['painter']
        guess = int(request.form['guess'])
        actual_age = painters[painter]
        result_message = ""
        if guess == actual_age:
            result_message = f"Congratulations! You guessed {painter}'s age when they died correctly."
            correct_guesses.append(1)
        else:
            result_message = f"Sorry, {painter}'s actual age at death is {actual_age}."
            incorrect_guesses.append(1)
        return render_template('guessing_game.html', painter=painter, result_message=result_message)

@app.route('/guessing_results')
def guessing_results():
    return jsonify({
        "correct_guesses": len(correct_guesses),
        "incorrect_guesses": len(incorrect_guesses)
    })

@app.route('/draw')
def draw():
    return render_template('drawing.html')

@app.route('/plot')
def plot():
    return render_template('plot.html')

@app.route('/map')
def map():
    return render_template('map.html')


def fetch_art_images():
    keywords = ["art", "painting", "sculpture", "drawing", "portrait", "landscape", "abstract"]
    keyword = random.choice(keywords)
    url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
    params = {"q": keyword, "hasImages": "true"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        object_ids = data.get("objectIDs", [])[:10]
        art_images = []
        for obj_id in object_ids:
            obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
            obj_response = requests.get(obj_url)
            if obj_response.status_code == 200:
                obj_data = obj_response.json()
                artist = obj_data.get("artistDisplayName")
                # Only add the artwork if there's an image and either an artist name or it's explicitly unknown
                if obj_data.get("primaryImageSmall") and (artist or artist == ""):
                    art_images.append({
                        "title": obj_data.get("title", "Untitled"),
                        "artist": artist if artist else "Unknown",
                        "image": obj_data.get("primaryImageSmall")
                    })
        return art_images
    return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  # Set logging level
    app.run(debug=True)
