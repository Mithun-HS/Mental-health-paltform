from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from app import db
from app.models import Mood
from config import Config
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from huggingface_hub import InferenceClient
import requests
from dotenv import load_dotenv
import os

HF_TOKEN = os.getenv("HF_TOKEN")


load_dotenv()



model_name = "mistralai/Mistral-7B-Instruct-v0.1"

main_bp = Blueprint('main', __name__)

# Meditation audio files
meditation_audio = {
    'sleep': {
        'title': 'Sleep Meditation',
        'file': 'sleep.mp3',
        'description': 'Guided meditation to help you fall asleep peacefully.'
    },
    'relaxation': {
        'title': 'Relaxation Sounds',
        'file': 'relaxation.mp3',
        'description': 'Calming sounds to help you relax and unwind.'
    },
    'anxiety': {
        'title': 'Anxiety Relief',
        'file': 'anxiety.mp3',
        'description': 'Meditation to reduce anxiety and calm your mind.'
    },
    'anger': {
        'title': 'Anger Management',
        'file': 'anger.mp3',
        'description': 'Exercises to help control anger and frustration.'
    },
    'happiness': {
        'title': 'Boost Happiness',
        'file': 'happiness.mp3',
        'description': 'Positive affirmations to increase happiness.'
    }
}

# Activity suggestions
activities = {
    'depression': [
        'Go for a 10-minute walk outside',
        'Write down 3 things you\'re grateful for',
        'Call or text a friend',
        'Do 5 minutes of stretching',
        'Listen to uplifting music'
    ],
    'anxiety': [
        'Practice deep breathing for 5 minutes',
        'Write down your worries in a journal',
        'Try progressive muscle relaxation',
        'Visualize your happy place',
        'Do a grounding exercise (5-4-3-2-1 technique)'
    ],
    'anger': [
        'Count slowly to 10 before reacting',
        'Squeeze a stress ball',
        'Write a letter (but don\'t send it)',
        'Do vigorous exercise for 5 minutes',
        'Practice mindful breathing'
    ],
    'stress': [
        'Take a warm bath or shower',
        'Do a 5-minute guided meditation',
        'Make a to-do list to organize thoughts',
        'Spend time with a pet',
        'Do a hobby you enjoy for 15 minutes'
    ],
    'happiness': [
        'Smile at yourself in the mirror',
        'Do something kind for someone else',
        'Dance to your favorite song',
        'Recall a happy memory in detail',
        'Spend time in nature'
    ]
}

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get mood data for the last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    mood_data = Mood.query.filter(
        Mood.user_id == current_user.id,
        Mood.date >= seven_days_ago
    ).order_by(Mood.date.asc()).all()
    
    # Prepare data for chart
    mood_chart_data = []
    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=6-i)).date()
        moods = [m.mood_level for m in mood_data if m.date.date() == date]
        avg_mood = sum(moods)/len(moods) if moods else None
        mood_chart_data.append({
            'date': date.strftime('%a'),
            'mood': avg_mood
        })
    
    # Calculate overall trend
    if mood_data:
        recent_moods = [m.mood_level for m in mood_data[-3:]]  # Last 3 entries
        avg_recent = sum(recent_moods) / len(recent_moods)
        overall_trend = "positive" if avg_recent >= 3 else "negative"
    else:
        overall_trend = "neutral"
    
    return render_template('dashboard.html', 
                         mood_chart_data=mood_chart_data,
                         overall_trend=overall_trend,
                         current_date=datetime.utcnow()) 

@main_bp.route('/update_mood', methods=['POST'])
@login_required
def update_mood():
    mood_level = int(request.form.get('mood_level'))
    note = request.form.get('note', '').strip()  # Get note or empty string
    
    new_mood = Mood(
        mood_level=mood_level,
        note=note if note else None,  # Store None if empty
        user_id=current_user.id
    )
    
    db.session.add(new_mood)
    db.session.commit()
    
    return jsonify({'success': True})

@main_bp.route('/meditation')
@login_required
def meditation():
    return render_template('meditation.html', audio_files=meditation_audio)

@main_bp.route('/activities')
@login_required
def activity_center():
    return render_template('activities.html', activities=activities)

@main_bp.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')
@main_bp.route('/chatbot_response', methods=['POST'])
@login_required
def chatbot_response():
    import os
    from huggingface_hub import InferenceClient

    HF_TOKEN = os.getenv("HF_TOKEN")
    user_message = request.form.get('message')
    prompt = f"[INST] You are a compassionate mental health assistant. Support the user. Keep it short.\nUser: {user_message} [/INST]"

    try:
        client = InferenceClient(
            model="HuggingFaceH4/zephyr-7b-beta",
            token=HF_TOKEN,
            provider="hf-inference"  # 👈 this is the fix
        )
        response_text = client.text_generation(prompt, max_new_tokens=200)
        cleaned_response = response_text.split("[/INST]")[-1].strip()
        return jsonify({'response': cleaned_response})
    except Exception as e:
        return jsonify({'response': f"Error occurred: {str(e)}"})

    
# Add to your routes.py
@main_bp.route('/log_activity', methods=['POST'])
@login_required
def log_activity():
    data = request.get_json()
    activity_name = data.get('activity_name')
    duration = data.get('duration')
    
    if activity_name and duration:
        activity_log = ActivityLog(
            activity_name=activity_name,
            duration=duration,
            user_id=current_user.id
        )
        db.session.add(activity_log)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Missing data'})

@main_bp.route('/get_monthly_moods')
@login_required
def get_monthly_moods():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    # Use the same timezone for all date operations
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 else datetime(year + 1, 1, 1, tzinfo=timezone.utc)

    moods = Mood.query.filter(
        Mood.user_id == current_user.id,
        Mood.date >= start_date,
        Mood.date < end_date
    ).all()

    mood_data = [{
        'date': mood.date.astimezone(timezone.utc).date().isoformat(),  # Convert to UTC and strip time component
        'mood_level': mood.mood_level,
        'note': mood.note
    } for mood in moods]

    return jsonify(mood_data)

@main_bp.route('/get_activity_data')
@login_required
def get_activity_data():
    # Get activity data for the last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    activity_data = db.session.query(
        func.date(ActivityLog.completed_at).label('date'),
        func.sum(ActivityLog.duration).label('total_duration')
    ).filter(
        ActivityLog.user_id == current_user.id,
        ActivityLog.completed_at >= seven_days_ago
    ).group_by(
        func.date(ActivityLog.completed_at)
    ).order_by(
        func.date(ActivityLog.completed_at)
    ).all()
    
    # Format data for chart
    dates = []
    durations = []
    
    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=6-i)).date()
        dates.append(date.strftime('%a'))
        
        # Find duration for this date if exists
        duration = 0
        for entry in activity_data:
            if entry.date == date:
                duration = entry.total_duration / 60  # Convert to minutes
                break
        durations.append(duration)
    
    return jsonify({
        'dates': dates,
        'durations': durations
    })