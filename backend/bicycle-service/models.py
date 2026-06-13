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

class Bicycle(db.Model):
    __tablename__ = 'bicycles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bike_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    color = db.Column(db.String(50), nullable=True)
    condition = db.Column(db.String(50), nullable=False, default='Good')  # Good, Fair, Poor
    status = db.Column(db.String(50), nullable=False, default='Available')  # Available, Rented, In Maintenance, Out of Service
    location = db.Column(db.String(200), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    total_rentals = db.Column(db.Integer, default=0)
    last_serviced = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'bike_code': self.bike_code,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'color': self.color,
            'condition': self.condition,
            'status': self.status,
            'location': self.location,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'total_rentals': self.total_rentals,
            'last_serviced': _utc_iso(self.last_serviced),
            'created_at': _utc_iso(self.created_at),
            'updated_at': _utc_iso(self.updated_at)
        }

