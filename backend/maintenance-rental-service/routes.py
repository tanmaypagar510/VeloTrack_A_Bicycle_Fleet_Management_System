from flask import Blueprint, request, jsonify
from models import db, MaintenanceLog, Rental
from auth import jwt_required
from events import publish_maintenance_event, publish_rental_checkout_event, publish_rental_return_event
from datetime import datetime, timezone
import requests
import os
import logging

logger = logging.getLogger('maintenance-rental-service')

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/api/maintenance')
rentals_bp = Blueprint('rentals', __name__, url_prefix='/api/rentals')

BICYCLE_SERVICE_URL = os.environ.get('BICYCLE_SERVICE_URL', 'http://localhost:5002')

ANOMALY_THRESHOLD_MINUTES = 5  # Rentals shorter than 5 min flagged as anomalous


# ─── Helper ───

def update_bicycle_status(bike_id, status, token):
    """Call bicycle-service to update status"""
    try:
        resp = requests.patch(
            f"{BICYCLE_SERVICE_URL}/api/bicycles/{bike_id}/status",
            json={"status": status},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Failed to update bicycle status: {e}")
        return False


def get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth.split(' ')[1]
    return ''


# ─── Maintenance Routes ───

@maintenance_bp.route('/', methods=['GET'])
@jwt_required
def get_maintenance_logs():
    """Get all maintenance logs
    ---
    tags: [Maintenance]
    security:
      - Bearer: []
    parameters:
      - in: query
        name: bicycle_id
        type: integer
        required: false
    responses:
      200:
        description: List of maintenance logs
    """
    bicycle_id = request.args.get('bicycle_id', type=int)
    query = MaintenanceLog.query
    if bicycle_id:
        query = query.filter_by(bicycle_id=bicycle_id)
    logs = query.order_by(MaintenanceLog.service_date.desc()).all()
    return jsonify({'maintenance_logs': [l.to_dict() for l in logs]}), 200


@maintenance_bp.route('/<int:log_id>', methods=['GET'])
@jwt_required
def get_maintenance_log(log_id):
    """Get maintenance log by ID
    ---
    tags: [Maintenance]
    security:
      - Bearer: []
    responses:
      200:
        description: Maintenance log details
    """
    log = MaintenanceLog.query.get(log_id)
    if not log:
        return jsonify({'error': 'Maintenance log not found'}), 404
    return jsonify({'maintenance_log': log.to_dict()}), 200


@maintenance_bp.route('/', methods=['POST'])
@jwt_required
def create_maintenance_log():
    """Create a maintenance log
    ---
    tags: [Maintenance]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [bicycle_id, problem_description, work_done, technician]
          properties:
            bicycle_id: {type: integer}
            problem_description: {type: string}
            work_done: {type: string}
            cost: {type: number}
            technician: {type: string}
    responses:
      201:
        description: Maintenance log created
    """
    data = request.get_json()
    required = ['bicycle_id', 'problem_description', 'work_done', 'technician']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Block maintenance on a currently rented bicycle
    active_rental = Rental.query.filter_by(bicycle_id=data['bicycle_id'], status='Active').first()
    if active_rental:
        return jsonify({'error': 'Cannot create maintenance log: bicycle is currently rented. Return it first.'}), 400

    log = MaintenanceLog(
        bicycle_id=data['bicycle_id'],
        problem_description=data['problem_description'],
        work_done=data['work_done'],
        cost=data.get('cost', 0.0),
        technician=data['technician'],
        created_by=request.user.get('user_id')
    )
    db.session.add(log)
    db.session.commit()

    # Update bicycle status to In Maintenance
    update_bicycle_status(data['bicycle_id'], 'In Maintenance', get_token_from_request())

    # Publish event to RabbitMQ for risk score recalculation
    try:
        publish_maintenance_event(data['bicycle_id'], log.id)
    except Exception as e:
        logger.warning(f"Failed to publish maintenance event: {e}")

    return jsonify({'message': 'Maintenance log created', 'maintenance_log': log.to_dict()}), 201


@maintenance_bp.route('/history/<int:bicycle_id>', methods=['GET'])
@jwt_required
def get_bicycle_history(bicycle_id):
    """Get complete history for a bicycle (maintenance + rentals)
    ---
    tags: [Maintenance]
    security:
      - Bearer: []
    responses:
      200:
        description: Complete bicycle history
    """
    m_logs = MaintenanceLog.query.filter_by(bicycle_id=bicycle_id).order_by(MaintenanceLog.service_date.desc()).all()
    r_logs = Rental.query.filter_by(bicycle_id=bicycle_id).order_by(Rental.checkout_time.desc()).all()

    return jsonify({
        'bicycle_id': bicycle_id,
        'maintenance_logs': [l.to_dict() for l in m_logs],
        'rentals': [r.to_dict() for r in r_logs],
        'total_maintenance': len(m_logs),
        'total_rentals': len(r_logs)
    }), 200


# ─── Rental Routes ───

@rentals_bp.route('/', methods=['GET'])
@jwt_required
def get_rentals():
    """Get all rentals
    ---
    tags: [Rentals]
    security:
      - Bearer: []
    parameters:
      - in: query
        name: bicycle_id
        type: integer
        required: false
      - in: query
        name: status
        type: string
        required: false
    responses:
      200:
        description: List of rentals
    """
    bicycle_id = request.args.get('bicycle_id', type=int)
    status = request.args.get('status')
    query = Rental.query
    if bicycle_id:
        query = query.filter_by(bicycle_id=bicycle_id)
    if status:
        query = query.filter_by(status=status)
    rentals = query.order_by(Rental.checkout_time.desc()).all()
    return jsonify({'rentals': [r.to_dict() for r in rentals]}), 200


@rentals_bp.route('/checkout', methods=['POST'])
@jwt_required
def checkout():
    """Check out a bicycle (start rental)
    ---
    tags: [Rentals]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [bicycle_id, renter_name]
          properties:
            bicycle_id: {type: integer}
            renter_name: {type: string}
            renter_contact: {type: string}
            notes: {type: string}
    responses:
      201:
        description: Rental started
    """
    data = request.get_json()
    if not data.get('bicycle_id') or not data.get('renter_name'):
        return jsonify({'error': 'bicycle_id and renter_name are required'}), 400

    # Check if bike already rented
    active = Rental.query.filter_by(bicycle_id=data['bicycle_id'], status='Active').first()
    if active:
        return jsonify({'error': 'Bicycle is already rented'}), 400

    # Verify bicycle is Available before checkout
    try:
        token = get_token_from_request()
        resp = requests.get(
            f"{BICYCLE_SERVICE_URL}/api/bicycles/{data['bicycle_id']}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if resp.status_code == 200:
            bike_data = resp.json().get('bicycle', {})
            if bike_data.get('status') != 'Available':
                return jsonify({'error': f"Cannot checkout: bicycle is currently '{bike_data.get('status')}'. It must be Available."}), 400
        elif resp.status_code == 404:
            return jsonify({'error': 'Bicycle not found'}), 404
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not verify bicycle status: {e}")

    rental = Rental(
        bicycle_id=data['bicycle_id'],
        renter_name=data['renter_name'],
        renter_contact=data.get('renter_contact'),
        notes=data.get('notes'),
        rate_per_hour=float(data.get('rate_per_hour', 50.0)),
        status='Active',
        created_by=request.user.get('user_id')
    )
    db.session.add(rental)
    db.session.commit()

    # Update bicycle status
    update_bicycle_status(data['bicycle_id'], 'Rented', get_token_from_request())

    try:
        publish_rental_checkout_event(data['bicycle_id'], rental.id)
    except Exception as e:
        logger.warning(f"Failed to publish rental checkout event: {e}")

    return jsonify({'message': 'Bicycle checked out', 'rental': rental.to_dict()}), 201


@rentals_bp.route('/return/<int:rental_id>', methods=['POST'])
@jwt_required
def return_bike(rental_id):
    """Return a bicycle (end rental)
    ---
    tags: [Rentals]
    security:
      - Bearer: []
    responses:
      200:
        description: Rental completed
    """
    rental = Rental.query.get(rental_id)
    if not rental:
        return jsonify({'error': 'Rental not found'}), 404
    if rental.status == 'Returned':
        return jsonify({'error': 'Rental already returned'}), 400

    rental.return_time = datetime.now(timezone.utc)
    rental.status = 'Returned'

    # Calculate duration (normalize timezone — DB returns naive datetimes)
    checkout = rental.checkout_time
    if checkout.tzinfo is None:
        checkout = checkout.replace(tzinfo=timezone.utc)
    duration = (rental.return_time - checkout).total_seconds() / 3600.0
    rental.duration_hours = round(duration, 2)

    # Calculate rental cost (minimum 1 hour charge)
    billable_hours = max(1.0, round(duration + 0.49))  # Round up to nearest hour, min 1hr
    rental.rental_cost = round(billable_hours * (rental.rate_per_hour or 50.0), 2)

    # Anomaly detection: flag very short rentals
    if duration * 60 < ANOMALY_THRESHOLD_MINUTES:
        rental.is_anomalous = True
        rental.anomaly_reason = f"Unusually short rental: {round(duration * 60, 1)} minutes"

    db.session.commit()

    # Update bicycle status back to Available
    update_bicycle_status(rental.bicycle_id, 'Available', get_token_from_request())

    try:
        publish_rental_return_event(rental.bicycle_id, rental.id, rental.duration_hours, rental.is_anomalous)
    except Exception as e:
        logger.warning(f"Failed to publish rental return event: {e}")

    return jsonify({'message': 'Bicycle returned', 'rental': rental.to_dict()}), 200


@rentals_bp.route('/<int:rental_id>', methods=['GET'])
@jwt_required
def get_rental(rental_id):
    """Get rental by ID
    ---
    tags: [Rentals]
    security:
      - Bearer: []
    responses:
      200:
        description: Rental details
    """
    rental = Rental.query.get(rental_id)
    if not rental:
        return jsonify({'error': 'Rental not found'}), 404
    return jsonify({'rental': rental.to_dict()}), 200

