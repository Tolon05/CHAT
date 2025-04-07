from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
import pyotp
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/messenger_db'
app.config['JWT_SECRET_KEY'] = 'supersecretkey'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    otp_secret = db.Column(db.String(16), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

def generate_otp_secret():
    return pyotp.random_base32()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already in use'}), 400
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    otp_secret = generate_otp_secret()
    new_user = User(email=email, password_hash=password_hash, otp_secret=otp_secret)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully', 'otp_secret': otp_secret})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    otp_code = data.get('otp_code')
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    if not pyotp.TOTP(user.otp_secret).verify(otp_code):
        return jsonify({'error': 'Invalid 2FA code'}), 401
    access_token = create_access_token(identity=user.id)
    return jsonify({'access_token': access_token})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)