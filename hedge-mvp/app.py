from flask import Flask, request, redirect, session, render_template
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

from PyPDF2 import PdfReader
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hedge.db'
app.config['SECRET_KEY'] = 'your-secret-key'  # For session management
db = SQLAlchemy(app)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    document_type = db.Column(db.String(50))
    source_name = db.Column(db.String(100))
    document_title = db.Column(db.String(200))
    document_content = db.Column(db.Text)  # Original PDF text
    ai_content = db.Column(db.Text)  # AI-generated content

with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if username == 'admin' and password == 'password':
        session['logged_in'] = True
        return redirect('/dashboard')
    return 'Invalid credentials'

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    document_type = request.form['document_type']
    source_name = request.form['source_name']
    document_title = request.form['document_title']
    pdf_file = request.files['document']

    # Extract text from PDF
    reader = PdfReader(pdf_file)
    document_content = ""
    for page in reader.pages:
        document_content += page.extract_text() or ""

    # Analyze with xAI API
    api_key = "xai-zTJHU64V5QFQlccXcJt4CKfEHPwQ7mKiPUGCsQxK6fUabOWp1KaEvDTn5bnDeK7X1oe5wqVXImYCZArc"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "messages": [
            {"role": "system", "content": "Extract market-moving or primary source information and provide relevant context."},
            {"role": "user", "content": document_content}
        ],
        "model": "grok-2-latest",
        "stream": false,
        "temperature": 0
    }
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    ai_content = response.json()['choices'][0]['message']['content']

    # Save to database
    new_doc = Document(
        document_type=document_type,
        source_name=source_name,
        document_title=document_title,
        document_content=document_content,
        ai_content=ai_content
    )
    db.session.add(new_doc)
    db.session.commit()

    return redirect('/dashboard')

@app.route('/dashboard')
@login_required
def dashboard():
    documents = Document.query.all()
    return render_template('dashboard.html', documents=documents)

@app.route('/view_original/<int:id>')
@login_required
def view_original(id):
    doc = Document.query.get_or_404(id)
    return doc.document_content

@app.route('/view_ai/<int:id>')
@login_required
def view_ai(id):
    doc = Document.query.get_or_404(id)
    return doc.ai_content

