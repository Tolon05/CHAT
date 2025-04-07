from flask import Blueprint, request, jsonify
from app import db, bcrypt, jwt
from app.models import User
import pyotp
from flask_jwt_extended import create_access_token

main = Blueprint("main", __name__)


@main.route("/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already in use"}), 400
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    otp_secret = pyotp.random_base32()
    new_user = User(email=email, password_hash=password_hash, otp_secret=otp_secret)
    db.session.add(new_user)
    db.session.commit()
    return jsonify(
        {"message": "User registered successfully", "otp_secret": otp_secret}
    )


@main.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    otp_code = data.get("otp_code")
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401
    if not pyotp.TOTP(user.otp_secret).verify(otp_code):
        return jsonify({"error": "Invalid 2FA code"}), 401
    access_token = create_access_token(identity=user.id)
    return jsonify({"access_token": access_token})
