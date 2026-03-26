"""
Fake Upload Service - minimal seed app
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    # Accepts a file upload, returns fake success
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    # Simulate saving file
    return jsonify({'status': 'success', 'filename': file.filename})

if __name__ == "__main__":
    app.run(debug=True)
