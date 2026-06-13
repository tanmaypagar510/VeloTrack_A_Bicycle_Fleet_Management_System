from flask import Blueprint, request, jsonify, current_app
from models import db, RiskScore, RiskScoreHistory, ChatHistory
from auth import jwt_required, admin_required
from datetime import datetime, timezone, timedelta
import requests
import logging

logger = logging.getLogger('assistant-routes')

assistant_bp = Blueprint('assistant', __name__, url_prefix='/api/maintenance-assistant')
risk_bp = Blueprint('risk', __name__, url_prefix='/api/risk-scores')


def get_rag_pipeline():
    from flask import current_app
    return current_app.config.get('RAG_PIPELINE')


def get_risk_scorer():
    from flask import current_app
    return current_app.config.get('RISK_SCORER')


def get_auth_header():
    return {'Authorization': request.headers.get('Authorization', '')}


def fetch_bike_history(bicycle_id, headers):
    """Fetch maintenance and rental history from maintenance-rental-service"""
    base_url = current_app.config.get('MAINTENANCE_RENTAL_SERVICE_URL', 'http://localhost:5003')
    try:
        resp = requests.get(f"{base_url}/api/maintenance/history/{bicycle_id}", headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch bike history: {e}")
    return {'maintenance_logs': [], 'rentals': []}


def fetch_all_bicycles(headers):
    """Fetch all bicycles from bicycle-service"""
    base_url = current_app.config.get('BICYCLE_SERVICE_URL', 'http://localhost:5002')
    try:
        resp = requests.get(f"{base_url}/api/bicycles/", headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('bicycles', [])
    except Exception as e:
        logger.error(f"Failed to fetch bicycles: {e}")
    return []


# ─── Maintenance Assistant (RAG) Routes ───

@assistant_bp.route('/ask', methods=['POST'])
@jwt_required
def ask_assistant():
    """Ask the Maintenance Assistant a question
    ---
    tags: [Maintenance Assistant]
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [question]
          properties:
            question: {type: string}
            bike_id: {type: integer}
    responses:
      200:
        description: AI-generated response with context
    """
    data = request.get_json()
    question = data.get('question')
    bike_id = data.get('bike_id')

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    pipeline = get_rag_pipeline()
    headers = get_auth_header()

    # If a specific bike is referenced, index its latest history
    if bike_id:
        history = fetch_bike_history(bike_id, headers)
        if history.get('maintenance_logs') or history.get('rentals'):
            pipeline.index_bike_history(bike_id, history['maintenance_logs'], history['rentals'])

    # Run RAG pipeline
    result = pipeline.ask(question, bike_id=bike_id)

    # Save chat history
    try:
        chat = ChatHistory(
            user_id=request.user.get('user_id'),
            bicycle_id=bike_id,
            question=question,
            answer=result['answer'],
            context_used=result.get('context_used')
        )
        db.session.add(chat)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")

    return jsonify(result), 200


@assistant_bp.route('/history', methods=['GET'])
@jwt_required
def get_chat_history():
    """Get chat history
    ---
    tags: [Maintenance Assistant]
    security:
      - Bearer: []
    responses:
      200:
        description: Chat history
    """
    chats = ChatHistory.query.order_by(ChatHistory.created_at.desc()).limit(50).all()
    return jsonify({'history': [c.to_dict() for c in chats]}), 200


# ─── Risk Scoring Routes ───

@risk_bp.route('/', methods=['GET'])
@jwt_required
def get_all_risk_scores():
    """Get risk scores for all bikes
    ---
    tags: [Risk Scores]
    security:
      - Bearer: []
    responses:
      200:
        description: Risk scores for all bikes
    """
    scores = RiskScore.query.all()
    if not scores:
        # Compute on-the-fly if no cached scores
        return _compute_all_scores()

    return jsonify({'risk_scores': [s.to_dict() for s in scores]}), 200


@risk_bp.route('/<int:bike_id>', methods=['GET'])
@jwt_required
def get_bike_risk_score(bike_id):
    """Get risk score for a specific bike
    ---
    tags: [Risk Scores]
    security:
      - Bearer: []
    responses:
      200:
        description: Risk score with feature breakdown
    """
    # Get cached score
    score = RiskScore.query.filter_by(bicycle_id=bike_id).first()

    if not score:
        # Compute on-the-fly
        return _compute_single_score(bike_id)

    # Get trend data (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    trend = RiskScoreHistory.query.filter(
        RiskScoreHistory.bicycle_id == bike_id,
        RiskScoreHistory.recorded_at >= thirty_days_ago
    ).order_by(RiskScoreHistory.recorded_at).all()

    return jsonify({
        'risk_score': score.to_dict(),
        'trend': [t.to_dict() for t in trend]
    }), 200


@risk_bp.route('/retrain', methods=['POST'])
@admin_required
def retrain_model():
    """Trigger model retraining (admin only)
    ---
    tags: [Risk Scores]
    security:
      - Bearer: []
    responses:
      200:
        description: Retraining triggered
    """
    scorer = get_risk_scorer()
    # Generate training data from existing records
    training_data = _generate_training_data()

    if not training_data:
        return jsonify({'message': 'Not enough data for training', 'samples': 0}), 200

    success = scorer.train(training_data)
    return jsonify({
        'message': 'Model retrained successfully' if success else 'Training failed',
        'samples': len(training_data)
    }), 200


@risk_bp.route('/batch-update', methods=['POST'])
@jwt_required
def batch_update_scores():
    """Recalculate scores for all bikes (nightly cron)
    ---
    tags: [Risk Scores]
    security:
      - Bearer: []
    responses:
      200:
        description: Batch update completed
    """
    return _compute_all_scores()


def _compute_all_scores():
    """Compute risk scores for all bikes"""
    headers = get_auth_header()
    bikes = fetch_all_bicycles(headers)
    scorer = get_risk_scorer()
    results = []

    for bike in bikes:
        history = fetch_bike_history(bike['id'], headers)
        score_val, level, features = scorer.compute_score(
            bike,
            history.get('maintenance_logs', []),
            history.get('rentals', [])
        )

        # Upsert score
        existing = RiskScore.query.filter_by(bicycle_id=bike['id']).first()
        if existing:
            existing.score = score_val
            existing.risk_level = level
            existing.feature_importance = features
            existing.computed_at = datetime.now(timezone.utc)
        else:
            existing = RiskScore(
                bicycle_id=bike['id'],
                score=score_val,
                risk_level=level,
                feature_importance=features
            )
            db.session.add(existing)

        # Record history
        history_entry = RiskScoreHistory(bicycle_id=bike['id'], score=score_val)
        db.session.add(history_entry)

        results.append(existing.to_dict() if hasattr(existing, 'to_dict') else {
            'bicycle_id': bike['id'], 'score': score_val, 'risk_level': level
        })

    db.session.commit()
    return jsonify({'risk_scores': results, 'updated': len(results)}), 200


def _compute_single_score(bike_id):
    """Compute risk score for a single bike"""
    headers = get_auth_header()
    base_url = current_app.config.get('BICYCLE_SERVICE_URL', 'http://localhost:5002')

    try:
        resp = requests.get(f"{base_url}/api/bicycles/{bike_id}", headers=headers, timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'Bicycle not found'}), 404
        bike = resp.json().get('bicycle', {})
    except Exception:
        return jsonify({'error': 'Failed to fetch bicycle data'}), 500

    history = fetch_bike_history(bike_id, headers)
    scorer = get_risk_scorer()
    score_val, level, features = scorer.compute_score(
        bike,
        history.get('maintenance_logs', []),
        history.get('rentals', [])
    )

    # Save score
    existing = RiskScore.query.filter_by(bicycle_id=bike_id).first()
    if existing:
        existing.score = score_val
        existing.risk_level = level
        existing.feature_importance = features
        existing.computed_at = datetime.now(timezone.utc)
    else:
        existing = RiskScore(bicycle_id=bike_id, score=score_val, risk_level=level, feature_importance=features)
        db.session.add(existing)

    db.session.add(RiskScoreHistory(bicycle_id=bike_id, score=score_val))
    db.session.commit()

    return jsonify({'risk_score': existing.to_dict()}), 200


def _generate_training_data():
    """Generate training data from existing bike histories"""
    # For demonstration: generate synthetic training data based on rule-based heuristics
    import numpy as np
    np.random.seed(42)

    training_data = []
    for _ in range(200):
        days_service = np.random.randint(1, 365)
        total_rentals = np.random.randint(0, 200)
        rentals_since = np.random.randint(0, total_rentals + 1)
        maint_count = np.random.randint(0, 20)
        avg_dur = np.random.uniform(0.5, 8.0)
        anomalous = np.random.randint(0, 5)
        issues = maint_count
        age = np.random.randint(30, 1500)

        # Label: 1 if bike likely needs maintenance within 14 days
        risk = (days_service > 60) * 0.3 + (rentals_since > 30) * 0.25 + (anomalous > 2) * 0.2 + (maint_count > 5) * 0.15
        label = 1 if risk + np.random.uniform(-0.15, 0.15) > 0.4 else 0

        training_data.append({
            'features': [days_service, total_rentals, rentals_since, maint_count, avg_dur, anomalous, issues, age],
            'label': label
        })

    return training_data

