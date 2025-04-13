from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import google.generativeai as genai

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ✅ Configure Gemini AI
genai.configure(api_key="AIzaSyD4Eo4vk8fkRZxwVBKfoqroA_7zgXPDLxY")  # Replace with your actual Gemini key

# ✅ Connect to SQLite
def get_db_connection():
    conn = sqlite3.connect("chat_history.db")
    conn.row_factory = sqlite3.Row
    return conn

# ✅ Create required tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

create_tables()

# ✅ Gemini AI response
def generate_gemini_response(user_message):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(user_message)
        return response.text.strip() if response.text else "🤖 I couldn't generate a response."
    except Exception as e:
        print("Gemini Error:", e)
        return f"Sorry, an error occurred: {str(e)}"

# ✅ Chat route
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("user_message", "").strip()

    if not user_message:
        return jsonify({"error": "user_message is required"}), 400

    bot_response = generate_gemini_response(user_message)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (user_message, bot_response) VALUES (?, ?)", (user_message, bot_response))
    conn.commit()
    conn.close()

    return jsonify({"user_message": user_message, "bot_response": bot_response})

# ✅ Chat History route
@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chats ORDER BY timestamp DESC")
    chat_data = cursor.fetchall()
    conn.close()

    history = [
        {"id": row["id"], "user_message": row["user_message"], "bot_response": row["bot_response"], "timestamp": row["timestamp"]}
        for row in chat_data
    ]
    return jsonify(history)

# ✅ Signup route
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required"}), 400

    try:
        with sqlite3.connect("chat_history.db") as conn:
            cursor = conn.cursor()
            # Check if the user already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return jsonify({"success": False, "error": "Email already exists"}), 409

            # Insert new user
            cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            return jsonify({"success": True, "message": "User registered successfully"}), 201

    except sqlite3.Error as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500

# ✅ Login route
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True, "message": "Login successful"}), 200
    else:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401
        

import base64
import requests
from flask import request, jsonify

@app.route("/generate-image", methods=["POST"])
def generate_image():
    data = request.json
    prompt = data.get("prompt", "").strip()

    # Ensure the prompt is provided
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    headers = {
        "Authorization": "Bearer"  # ✅ Your token
    }

    payload = {"inputs": prompt}  # Pass the user input to generate the image
    url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"

    # Make the POST request to Hugging Face's inference API
    response = requests.post(url, headers=headers, json=payload)

    # If successful, convert the image content to base64 and return it
    if response.status_code == 200:
        img_base64 = base64.b64encode(response.content).decode("utf-8")
        return jsonify({"image_base64": img_base64})
    else:
        print("Hugging Face Error:", response.text)
        return jsonify({"error": "Failed to generate image"}), 500

# ✅ Run server
# ✅ Run server for Render deployment
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
