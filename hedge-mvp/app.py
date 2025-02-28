from flask import Flask, request, redirect, session, render_template
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader
import requests
from functools import wraps

# Initialize Flask app and database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hedge.db'
app.config['SECRET_KEY'] = 'hedge'
db = SQLAlchemy(app)

# Define the Document model
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    document_type = db.Column(db.String(50))
    source_name = db.Column(db.String(100))
    document_title = db.Column(db.String(200))
    document_content = db.Column(db.Text)
    ai_content = db.Column(db.Text)

# Create the database tables
with app.app_context():
    db.create_all()

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

# Login routes
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

# Upload route
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    pdf_file = request.files['document']

    # Extract text from PDF
    reader = PdfReader(pdf_file)
    document_content = ""
    for page in reader.pages:
        document_content += page.extract_text() or ""

    # Generate metadata with xAI API
    api_key = "your-xai-api-key-here"  # Replace with your actual API key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    metadata_prompt = "Based on the following document, provide a document type, source name, and title in the format: 'Type: [type]\nSource: [source]\nTitle: [title]'"
    data = {
        "messages": [
            {"role": "system", "content": metadata_prompt},
            {"role": "user", "content": document_content}
        ],
        "model": "grok-2-latest",
        "stream": False,
        "temperature": 0
    }
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    metadata_response = response.json()['choices'][0]['message']['content']

    # Parse metadata
    lines = metadata_response.split('\n')
    document_type = lines[0].split(': ')[1]
    source_name = lines[1].split(': ')[1]
    document_title = lines[2].split(': ')[1]

    # Analyze content with xAI API (optional AI analysis)
    analysis_prompt = "Extract market-moving or primary source information and provide relevant context."
    data = {
        "messages": [
            {"role": "system", "content": analysis_prompt},
            {"role": "user", "content": document_content}
        ],
        "model": "grok-2-latest",
        "stream": False,
        "temperature": 0
    }
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    ai_content = response.json()['choices'][0]['message']['content']

    # Save to database (assuming a Document model exists)
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

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    documents = Document.query.all()
    return render_template('dashboard.html', documents=documents)

# Routes to view content (THIS GOES HERE)
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

# Run the app (only if this is the main module)
if __name__ == '__main__':
    app.run(debug=True)