from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


def _utc_iso(dt):
    """Format datetime as ISO string with UTC timezone marker"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class RiskScore(db.Model):
    __tablename__ = 'risk_scores'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bicycle_id = db.Column(db.Integer, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False, default=0.0)
    risk_level = db.Column(db.String(20), nullable=False, default='Low')  # Low, Medium, High
    feature_importance = db.Column(db.JSON, nullable=True)  # SHAP feature contributions
    computed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'bicycle_id': self.bicycle_id,
            'score': self.score,
            'risk_level': self.risk_level,
            'feature_importance': self.feature_importance,
            'computed_at': _utc_iso(self.computed_at)
        }


class RiskScoreHistory(db.Model):
    __tablename__ = 'risk_score_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bicycle_id = db.Column(db.Integer, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'bicycle_id': self.bicycle_id,
            'score': self.score,
            'recorded_at': _utc_iso(self.recorded_at)
        }


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=True)
    bicycle_id = db.Column(db.Integer, nullable=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    context_used = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bicycle_id': self.bicycle_id,
            'question': self.question,
            'answer': self.answer,
            'context_used': self.context_used,
            'created_at': _utc_iso(self.created_at)
        }

