from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    User database model representing registered users.
    Inherits from UserMixin for easy integration with Flask-Login.
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to track compression history
    uploads = db.relationship('UploadLog', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the user's password."""
        return check_password_hash(self.password_hash, password)

    def get_remaining_uploads(self, free_limit=2):
        """
        Check how many free uploads this user has left.
        Only applicable if is_premium is False.
        """
        if self.is_premium:
            return float('inf')
        
        # Count all successful/failed compression attempts by this user
        count = UploadLog.query.filter_by(user_id=self.id).count()
        return max(0, free_limit - count)

    def __repr__(self):
        return f"<User {self.username}>"


class UploadLog(db.Model):
    """
    Database model to log every compression task.
    Supports anonymous tracking via IP address and Session Cookies.
    """
    __tablename__ = 'upload_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Supports IPv6
    session_token = db.Column(db.String(64), nullable=True) # Cookie token
    original_name = db.Column(db.String(255), nullable=False)
    original_size = db.Column(db.Integer, nullable=False)
    compressed_size = db.Column(db.Integer, nullable=True)
    compression_time = db.Column(db.Float, nullable=True)
    preset = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='failed')  # 'success' or 'failed'
    error_message = db.Column(db.String(500), nullable=True)
    stages_used = db.Column(db.String(255), nullable=True) # comma-separated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def reduction_percent(self):
        """Calculate the percentage size reduction."""
        if not self.compressed_size or self.original_size <= 0:
            return 0.0
        if self.compressed_size >= self.original_size:
            return 0.0
        return ((self.original_size - self.compressed_size) / self.original_size) * 100.0

    def __repr__(self):
        return f"<UploadLog {self.original_name} - {self.status}>"


class SystemSetting(db.Model):
    """
    Key-Value pair configuration for flexible runtime options.
    Adjustable directly via the admin dashboard.
    """
    __tablename__ = 'system_setting'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @staticmethod
    def get_val(key, default=None):
        """Get setting value by key."""
        setting = SystemSetting.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_val(key, value, description=None):
        """Set key-value pair. Creates it if not existing."""
        setting = SystemSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            if description:
                setting.description = description
        else:
            setting = SystemSetting(key=key, value=str(value), description=description)
            db.session.add(setting)
        db.session.commit()

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"


class Transaction(db.Model):
    """
    Database model representing paid subscription transactions.
    """
    __tablename__ = 'transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'settlement', 'success', 'pending', 'expire', etc.
    payment_type = db.Column(db.String(50), nullable=True) # 'gopay', 'credit_card', 'bank_transfer', 'mock', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to user
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f"<Transaction {self.order_id} - {self.amount} - {self.status}>"
