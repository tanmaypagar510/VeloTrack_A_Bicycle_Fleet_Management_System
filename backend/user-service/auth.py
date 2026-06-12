import jwt
import functools
from flask import request, jsonify, current_app
from datetime import datetime, timedelta, timezone


def create_token(user_id, email, role, secret, expiry_hours=24):
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def decode_token(token, secret):
    try:
        return jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def jwt_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        payload = decode_token(token, current_app.config['JWT_SECRET'])
        if payload is None:
            return jsonify({'error': 'Token is invalid or expired'}), 401

        request.user = payload
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @functools.wraps(f)
    @jwt_required
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

