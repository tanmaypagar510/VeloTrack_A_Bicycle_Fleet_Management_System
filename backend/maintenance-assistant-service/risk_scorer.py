import numpy as np
import logging
import os
import json
from datetime import datetime, timezone

logger = logging.getLogger('risk-scorer')

try:
    import xgboost as xgb
    import shap
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("XGBoost/SHAP not available. Using rule-based scoring.")


class RiskScorer:
    """ML-powered risk scoring for bicycle maintenance prediction"""

    FEATURE_NAMES = [
        'days_since_last_service',
        'total_rentals',
        'rentals_since_last_service',
        'total_maintenance_count',
        'avg_rental_duration',
        'anomalous_rental_count',
        'total_issues_logged',
        'days_since_purchase'
    ]

    def __init__(self, model_path=None):
        self.model_path = model_path or '/app/data/models/risk_model.xgb'
        self.model = None
        self.explainer = None
        self._load_model()

    def _load_model(self):
        """Load trained XGBoost model if available"""
        if not XGB_AVAILABLE:
            return

        if os.path.exists(self.model_path):
            try:
                self.model = xgb.XGBClassifier()
                self.model.load_model(self.model_path)
                self.explainer = shap.TreeExplainer(self.model)
                logger.info("Loaded XGBoost risk model")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.model = None

    def extract_features(self, bike_data, maintenance_logs, rentals):
        """Extract features for a single bike"""
        now = datetime.now(timezone.utc)

        # Days since last service
        last_service = None
        if maintenance_logs:
            dates = []
            for log in maintenance_logs:
                sd = log.get('service_date')
                if sd:
                    if isinstance(sd, str):
                        try:
                            dates.append(datetime.fromisoformat(sd.replace('Z', '+00:00')))
                        except ValueError:
                            pass
                    else:
                        dates.append(sd)
            if dates:
                last_service = max(dates)

        days_since_last_service = (now - last_service).days if last_service else 365

        # Rental stats
        total_rentals = len(rentals)
        rentals_since_service = 0
        anomalous_count = 0
        durations = []

        for r in rentals:
            if r.get('is_anomalous'):
                anomalous_count += 1
            if r.get('duration_hours') is not None:
                durations.append(r['duration_hours'])
            if last_service:
                checkout = r.get('checkout_time')
                if checkout:
                    if isinstance(checkout, str):
                        try:
                            ct = datetime.fromisoformat(checkout.replace('Z', '+00:00'))
                            if ct > last_service:
                                rentals_since_service += 1
                        except ValueError:
                            pass
                    elif checkout > last_service:
                        rentals_since_service += 1
            else:
                rentals_since_service = total_rentals

        avg_duration = np.mean(durations) if durations else 0.0

        # Purchase age
        purchase_date = bike_data.get('purchase_date')
        if purchase_date:
            if isinstance(purchase_date, str):
                try:
                    pd_parsed = datetime.fromisoformat(purchase_date)
                    days_since_purchase = (now - pd_parsed.replace(tzinfo=timezone.utc)).days
                except ValueError:
                    days_since_purchase = 365
            else:
                days_since_purchase = (now - purchase_date.replace(tzinfo=timezone.utc)).days
        else:
            days_since_purchase = 365

        features = [
            days_since_last_service,
            total_rentals,
            rentals_since_service,
            len(maintenance_logs),
            avg_duration,
            anomalous_count,
            len(maintenance_logs),  # total issues
            days_since_purchase
        ]
        return np.array(features).reshape(1, -1)

    def compute_score(self, bike_data, maintenance_logs, rentals):
        """Compute risk score for a single bike (0-100)"""
        features = self.extract_features(bike_data, maintenance_logs, rentals)

        if self.model and XGB_AVAILABLE:
            try:
                proba = self.model.predict_proba(features)[0][1]
                score = round(proba * 100, 1)
                # SHAP explanations
                shap_values = self.explainer.shap_values(features)
                feature_imp = self._get_feature_importance(features[0], shap_values[0] if isinstance(shap_values, list) else shap_values[0])
                return score, self._risk_level(score), feature_imp
            except Exception as e:
                logger.error(f"Model prediction failed: {e}")

        # Rule-based fallback
        return self._rule_based_score(features[0])

    def _rule_based_score(self, features):
        """Rule-based fallback scoring"""
        days_since_service = features[0]
        total_rentals = features[1]
        rentals_since_service = features[2]
        anomalous_count = features[5]

        score = 0
        reasons = []

        # Days since last service (max 40 points)
        if days_since_service > 90:
            score += 40
            reasons.append(f"Last serviced {int(days_since_service)} days ago")
        elif days_since_service > 60:
            score += 25
            reasons.append(f"Last serviced {int(days_since_service)} days ago")
        elif days_since_service > 30:
            score += 15
            reasons.append(f"Last serviced {int(days_since_service)} days ago")

        # Rentals since last service (max 30 points)
        if rentals_since_service > 50:
            score += 30
            reasons.append(f"{int(rentals_since_service)} rentals since last service")
        elif rentals_since_service > 25:
            score += 20
            reasons.append(f"{int(rentals_since_service)} rentals since last service")
        elif rentals_since_service > 10:
            score += 10
            reasons.append(f"{int(rentals_since_service)} rentals since last service")

        # Anomalous rentals (max 20 points)
        if anomalous_count > 3:
            score += 20
            reasons.append(f"{int(anomalous_count)} anomalous rentals detected")
        elif anomalous_count > 0:
            score += 10
            reasons.append(f"{int(anomalous_count)} anomalous rental(s)")

        # Total maintenance issues (max 10 points)
        if features[3] > 5:
            score += 10
            reasons.append(f"{int(features[3])} maintenance issues logged")

        score = min(score, 100)
        feature_imp = [{'feature': r, 'contribution': round(score / max(len(reasons), 1), 1)} for r in reasons[:3]]

        return score, self._risk_level(score), feature_imp

    def _risk_level(self, score):
        if score <= 33:
            return 'Low'
        elif score <= 66:
            return 'Medium'
        else:
            return 'High'

    def _get_feature_importance(self, features, shap_vals):
        """Get top 3 SHAP feature explanations"""
        if not isinstance(shap_vals, np.ndarray):
            shap_vals = np.array(shap_vals)

        abs_shap = np.abs(shap_vals)
        top_indices = abs_shap.argsort()[-3:][::-1]

        explanations = []
        for idx in top_indices:
            name = self.FEATURE_NAMES[idx] if idx < len(self.FEATURE_NAMES) else f"feature_{idx}"
            value = features[idx]
            readable = self._feature_to_readable(name, value)
            explanations.append({
                'feature': readable,
                'contribution': round(float(shap_vals[idx]) * 100, 1)
            })
        return explanations

    def _feature_to_readable(self, name, value):
        mapping = {
            'days_since_last_service': f"Last serviced {int(value)} days ago",
            'total_rentals': f"{int(value)} total rentals",
            'rentals_since_last_service': f"{int(value)} rentals since last service",
            'total_maintenance_count': f"{int(value)} maintenance records",
            'avg_rental_duration': f"Avg rental: {round(value, 1)} hours",
            'anomalous_rental_count': f"{int(value)} anomalous rentals",
            'total_issues_logged': f"{int(value)} logged issues",
            'days_since_purchase': f"Bike age: {int(value)} days"
        }
        return mapping.get(name, f"{name}: {value}")

    def train(self, training_data):
        """Train or retrain the XGBoost model"""
        if not XGB_AVAILABLE:
            logger.warning("XGBoost not available, cannot train")
            return False

        try:
            X = np.array([d['features'] for d in training_data])
            y = np.array([d['label'] for d in training_data])

            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                objective='binary:logistic',
                random_state=42
            )
            self.model.fit(X, y)

            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save_model(self.model_path)
            self.explainer = shap.TreeExplainer(self.model)

            logger.info("Risk model trained and saved successfully")
            return True
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False

