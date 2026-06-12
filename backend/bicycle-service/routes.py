from flask import Blueprint, request, jsonify
from models import db, Bicycle
from auth import jwt_required
from datetime import datetime

bicycles_bp = Blueprint('bicycles', __name__, url_prefix='/api/bicycles')


@bicycles_bp.route('/', methods=['GET'])
@jwt_required
def get_bicycles():
    """Get all bicycles
    ---
    tags: [Bicycles]
    security:
      - Bearer: []
    parameters:
      - in: query
        name: status
        type: string
        required: false
    responses:
      200:
        description: List of bicycles
    """
    status = request.args.get('status')
    query = Bicycle.query
    if status:
        query = query.filter_by(status=status)
    bicycles = query.order_by(Bicycle.id).all()
    return jsonify({'bicycles': [b.to_dict() for b in bicycles]}), 200


@bicycles_bp.route('/<int:bike_id>', methods=['GET'])
@jwt_required
def get_bicycle(bike_id):
    """Get bicycle by ID
    ---
    tags: [Bicycles]
    security:
      - Bearer: []
    responses:
      200:
        description: Bicycle details
    """
    bike = Bicycle.query.get(bike_id)
    if not bike:
        return jsonify({'error': 'Bicycle not found'}), 404
    return jsonify({'bicycle': bike.to_dict()}), 200


@bicycles_bp.route('/', methods=['POST'])
@jwt_required
def create_bicycle():
    """Register a new bicycle
    ---
    tags: [Bicycles]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [bike_code, make, model]
          properties:
            bike_code: {type: string}
            make: {type: string}
            model: {type: string}
            year: {type: integer}
            color: {type: string}
            condition: {type: string}
            location: {type: string}
            purchase_date: {type: string}
    responses:
      201:
        description: Bicycle created
    """
    data = request.get_json()
    if not data or not data.get('bike_code') or not data.get('make') or not data.get('model'):
        return jsonify({'error': 'bike_code, make, and model are required'}), 400

    if Bicycle.query.filter_by(bike_code=data['bike_code']).first():
        return jsonify({'error': 'Bicycle with this code already exists'}), 400

    bike = Bicycle(
        bike_code=data['bike_code'],
        make=data['make'],
        model=data['model'],
        year=data.get('year'),
        color=data.get('color'),
        condition=data.get('condition', 'Good'),
        status='Available',
        location=data.get('location'),
        purchase_date=datetime.strptime(data['purchase_date'], '%Y-%m-%d').date() if data.get('purchase_date') else None
    )
    db.session.add(bike)
    db.session.commit()
    return jsonify({'message': 'Bicycle registered successfully', 'bicycle': bike.to_dict()}), 201


@bicycles_bp.route('/<int:bike_id>', methods=['PUT'])
@jwt_required
def update_bicycle(bike_id):
    """Update bicycle details
    ---
    tags: [Bicycles]
    security:
      - Bearer: []
    responses:
      200:
        description: Bicycle updated
    """
    bike = Bicycle.query.get(bike_id)
    if not bike:
        return jsonify({'error': 'Bicycle not found'}), 404

    data = request.get_json()
    for field in ['make', 'model', 'year', 'color', 'condition', 'location']:
        if field in data:
            setattr(bike, field, data[field])

    db.session.commit()
    return jsonify({'message': 'Bicycle updated', 'bicycle': bike.to_dict()}), 200


@bicycles_bp.route('/<int:bike_id>/status', methods=['PATCH'])
@jwt_required
def update_status(bike_id):
    """Update bicycle status
    ---
    tags: [Bicycles]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [status]
          properties:
            status: {type: string, enum: [Available, Rented, In Maintenance, Out of Service]}
    responses:
      200:
        description: Status updated
    """
    bike = Bicycle.query.get(bike_id)
    if not bike:
        return jsonify({'error': 'Bicycle not found'}), 404

    data = request.get_json()
    valid_statuses = ['Available', 'Rented', 'In Maintenance', 'Out of Service']
    new_status = data.get('status')
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

    bike.status = new_status
    if new_status == 'In Maintenance':
        bike.last_serviced = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': 'Status updated', 'bicycle': bike.to_dict()}), 200


@bicycles_bp.route('/<int:bike_id>', methods=['DELETE'])
@jwt_required
def delete_bicycle(bike_id):
    """Delete a bicycle
    ---
    tags: [Bicycles]
    security:
      - Bearer: []
    responses:
      200:
        description: Bicycle deleted
    """
    bike = Bicycle.query.get(bike_id)
    if not bike:
        return jsonify({'error': 'Bicycle not found'}), 404

    db.session.delete(bike)
    db.session.commit()
    return jsonify({'message': 'Bicycle deleted'}), 200

