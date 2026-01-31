import os
from flask import Flask, render_template, request, url_for
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500))
    msg_type = db.Column(db.String(10), default='text') # 'text' or 'image'

with app.app_context():
    db.create_all()

socketio = SocketIO(app)

@app.route('/')
def index():
    messages = Message.query.all()
    return render_template('index.html', messages=messages)

# Route to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Save image message to DB
        # Format: /static/uploads/filename.jpg
        img_url = f"/static/uploads/{filename}"
        new_message = Message(content=img_url, msg_type='image')
        db.session.add(new_message)
        db.session.commit()
        
        # Broadcast image to chat
        socketio.emit('message', {'msg': img_url, 'id': new_message.id, 'type': 'image'})
        return 'Success', 200

@socketio.on('message')
def handle_message(msg):
    new_message = Message(content=msg, msg_type='text')
    db.session.add(new_message)
    db.session.commit()
    emit('message', {'msg': msg, 'id': new_message.id, 'type': 'text'}, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    msg_id = data['id']
    msg = Message.query.get(msg_id)
    if msg:
        # If it's an image, try to delete the file too (Optional)
        if msg.msg_type == 'image':
            try:
                # Remove the first character '/' to find path
                os.remove(msg.content[1:]) 
            except:
                pass 
                
        db.session.delete(msg)
        db.session.commit()
        emit('delete_message', {'id': msg_id}, broadcast=True)

if __name__ == '__main__':
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    socketio.run(app, host='0.0.0.0', debug=True)