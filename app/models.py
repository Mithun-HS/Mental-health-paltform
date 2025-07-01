from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    moods = db.relationship('Mood', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood_level = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text)  # This is the new field
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Mood('{self.mood_level}', '{self.date}')"

# Add to your existing models.py
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_name = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in seconds
    completed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"ActivityLog('{self.activity_name}', '{self.duration}', '{self.completed_at}')"