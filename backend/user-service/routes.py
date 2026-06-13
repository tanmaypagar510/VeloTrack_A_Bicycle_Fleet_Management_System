from flask import Blueprint, request, jsonify, current_app
from models import db, User
from auth import create_token, jwt_required, admin_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
users_bp = Blueprint('users', __name__, url_prefix='/api/users')


# ─── Auth Routes ───

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user
    ---
    tags: [Authentication]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [email, password, full_name]
          properties:
            email: {type: string}
            password: {type: string}
            full_name: {type: string}
            role: {type: string, default: staff}
            phone: {type: string}
    responses:
      201:
        description: User registered successfully
      400:
        description: Validation error
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('full_name'):
        return jsonify({'error': 'Email, password, and full_name are required'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        email=data['email'],
        full_name=data['full_name'],
        role=data.get('role', 'staff'),
        phone=data.get('phone')
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    token = create_token(user.id, user.email, user.role,
                         current_app.config['JWT_SECRET'],
                         current_app.config['JWT_EXPIRY_HOURS'])

    return jsonify({'message': 'User registered successfully', 'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user
    ---
    tags: [Authentication]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [email, password]
          properties:
            email: {type: string}
            password: {type: string}
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
    """
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_token(user.id, user.email, user.role,
                         current_app.config['JWT_SECRET'],
                         current_app.config['JWT_EXPIRY_HOURS'])

    return jsonify({'message': 'Login successful', 'token': token, 'user': user.to_dict()}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_me():
    """Get current user profile
    ---
    tags: [Authentication]
    security:
      - Bearer: []
    responses:
      200:
        description: Current user profile
    """
    user = User.query.get(request.user['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required
def change_password():
    """Change password
    ---
    tags: [Authentication]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [current_password, new_password]
          properties:
            current_password: {type: string}
            new_password: {type: string}
    responses:
      200:
        description: Password changed successfully
    """
    data = request.get_json()
    user = User.query.get(request.user['user_id'])

    if not user.check_password(data.get('current_password', '')):
        return jsonify({'error': 'Current password is incorrect'}), 400

    user.set_password(data['new_password'])
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'}), 200


# ─── User Management Routes ───

@users_bp.route('/', methods=['GET'])
@jwt_required
def get_users():
    """Get all users
    ---
    tags: [Users]
    security:
      - Bearer: []
    responses:
      200:
        description: List of users
    """
    users = User.query.all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required
def get_user(user_id):
    """Get user by ID
    ---
    tags: [Users]
    security:
      - Bearer: []
    responses:
      200:
        description: User details
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required
def update_user(user_id):
    """Update user profile
    ---
    tags: [Users]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            full_name: {type: string}
            phone: {type: string}
    responses:
      200:
        description: User updated successfully
    """
    if request.user['user_id'] != user_id and request.user.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if data.get('full_name'):
        user.full_name = data['full_name']
    if data.get('phone'):
        user.phone = data['phone']

    db.session.commit()
    return jsonify({'message': 'User updated', 'user': user.to_dict()}), 200

