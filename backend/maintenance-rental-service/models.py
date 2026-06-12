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


class MaintenanceLog(db.Model):
    __tablename__ = 'maintenance_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bicycle_id = db.Column(db.Integer, nullable=False, index=True)
    problem_description = db.Column(db.Text, nullable=False)
    work_done = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float, default=0.0)
    technician = db.Column(db.String(255), nullable=False)
    service_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'bicycle_id': self.bicycle_id,
            'problem_description': self.problem_description,
            'work_done': self.work_done,
            'cost': self.cost,
            'technician': self.technician,
            'service_date': _utc_iso(self.service_date),
            'created_by': self.created_by,
            'created_at': _utc_iso(self.created_at)
        }


class Rental(db.Model):
    __tablename__ = 'rentals'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bicycle_id = db.Column(db.Integer, nullable=False, index=True)
    renter_name = db.Column(db.String(255), nullable=False)
    renter_contact = db.Column(db.String(100), nullable=True)
    checkout_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    return_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='Active')  # Active, Returned
    duration_hours = db.Column(db.Float, nullable=True)
    rate_per_hour = db.Column(db.Float, default=50.0)  # ₹50/hour default
    rental_cost = db.Column(db.Float, nullable=True)  # Calculated on return
    is_anomalous = db.Column(db.Boolean, default=False)
    anomaly_reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'bicycle_id': self.bicycle_id,
            'renter_name': self.renter_name,
            'renter_contact': self.renter_contact,
            'checkout_time': _utc_iso(self.checkout_time),
            'return_time': _utc_iso(self.return_time),
            'status': self.status,
            'duration_hours': self.duration_hours,
            'rate_per_hour': self.rate_per_hour,
            'rental_cost': self.rental_cost,
            'is_anomalous': self.is_anomalous,
            'anomaly_reason': self.anomaly_reason,
            'notes': self.notes,
            'created_by': self.created_by,
            'created_at': _utc_iso(self.created_at)
        }

