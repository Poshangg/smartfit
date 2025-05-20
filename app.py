from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify # Add jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date, time, timedelta # Import date, time
from sqlalchemy import Text, Date, cast, func, desc # Add desc
from functools import wraps # Import wraps
from collections import defaultdict # Import defaultdict

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'smartfit.db') # Define db path explicitly

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-dev') # Use environment variable in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path # Use the explicit path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirect to login page if user tries to access protected page
login_manager.login_message_category = 'info' # Flash message category

# --- Database Models ---

# Association Table for User Saved Workouts (Many-to-Many)
user_saved_workouts = db.Table('user_saved_workouts',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('workout_id', db.Integer, db.ForeignKey('workout.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='user') # Added role field
    # Add cascade delete for related objects
    profile = db.relationship('Profile', backref='user', uselist=False, cascade="all, delete-orphan") # One-to-one relationship
    workout_logs = db.relationship('WorkoutLog', backref='logger', lazy='dynamic', cascade="all, delete-orphan")
    meal_logs = db.relationship('MealLog', backref='logger', lazy='dynamic', cascade="all, delete-orphan")
    # Many-to-Many relationship with Workout - Association table handles deletes automatically
    saved_workouts = db.relationship('Workout', secondary=user_saved_workouts, lazy='dynamic',
                                     backref=db.backref('saved_by_users', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float)
    height = db.Column(db.Float) # Consider storing in cm or inches consistently
    goal = db.Column(db.String(200)) # e.g., 'Lose Weight', 'Build Muscle', 'Improve Endurance'
    goal_weight = db.Column(db.Float, nullable=True) # New: Goal Weight
    fitness_level = db.Column(db.String(50)) # e.g., 'Beginner', 'Intermediate', 'Advanced'
    dietary_preferences = db.Column(db.String(200)) # e.g., 'Vegan', 'Keto', 'None'
    # Added Macro Goals
    goal_calories = db.Column(db.Integer, nullable=True)
    goal_protein = db.Column(db.Integer, nullable=True) # Store goals in grams
    goal_carbs = db.Column(db.Integer, nullable=True)
    goal_fat = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Add more fields: dob, activity_level, etc.

# --- New Models ---

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='General') # New: Gym, Home, General
    intensity = db.Column(db.String(50), nullable=True) # Low, Medium, High
    duration_est = db.Column(db.Integer, nullable=True) # Estimated duration in minutes
    equipment = db.Column(db.String(200), nullable=True) # e.g., Dumbbells, None
    instructions = db.Column(db.Text, nullable=True) # New: Step-by-step instructions
    reps_sets = db.Column(db.String(100), nullable=True) # New: e.g., "3 sets of 10-12 reps"
    form_tips = db.Column(db.Text, nullable=True) # New: Tips for proper form
    video_url = db.Column(db.String(255), nullable=True) # New: URL for video tutorial

    def __repr__(self):
        return f'<Workout {self.name}>'

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    meal_type = db.Column(db.String(50), nullable=True) # Breakfast, Lunch, Dinner, Snack
    diet_type = db.Column(db.String(100), nullable=True) # e.g., Vegan, Keto
    calories_est = db.Column(db.Integer, nullable=True) # Estimated calories
    # Added estimated macros and nutrients
    protein_est = db.Column(db.Float, nullable=True)
    carbs_est = db.Column(db.Float, nullable=True)
    fat_est = db.Column(db.Float, nullable=True)
    fiber_est = db.Column(db.Float, nullable=True)
    sugar_est = db.Column(db.Float, nullable=True)
    recipe_link = db.Column(db.String(255), nullable=True) # Link to full recipe

    def __repr__(self):
        return f'<Meal {self.name}>'

class WorkoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_name = db.Column(db.String(100), nullable=False)
    intensity_level = db.Column(db.String(50), nullable=True) # e.g., 'High', 'Medium', 'Low', '7/10'
    repetitions = db.Column(db.String(100), nullable=True) # e.g., '3x10', '5x5 @ 100kg', '15 reps'
    notes = db.Column(db.Text, nullable=True)
    log_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<WorkoutLog {self.workout_name} by {self.user_id}>'

class MealLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_name = db.Column(db.String(100), nullable=False) # Could link to Meal.id later
    meal_type = db.Column(db.String(50), nullable=True)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Float, nullable=True)
    carbs = db.Column(db.Float, nullable=True)
    fat = db.Column(db.Float, nullable=True)
    # Added fiber and sugar tracking
    fiber = db.Column(db.Float, nullable=True)
    sugar = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    log_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<MealLog {self.meal_name} by {self.user_id}>'

# New Model for Weight History
class WeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    log_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<WeightLog {self.weight}kg on {self.log_time.strftime("%Y-%m-%d")} by {self.user_id}>'


@login_manager.user_loader
def load_user(user_id):
    # Use the recommended db.session.get() method
    return db.session.get(User, int(user_id))

# --- Decorators ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper Function for Nutrition Goal Estimation ---
def estimate_nutrition_goals(weight_kg, height_cm, goal_text, fitness_level, goal_weight_kg=None): # Added goal_weight_kg
    """
    Estimates daily nutrition goals based on basic inputs.
    If goal_weight_kg is provided, calculates TDEE based on goal weight,
    then adjusts calories based on the difference between current and goal weight.
    Returns a dictionary: {'calories': int, 'protein': int, 'carbs': int, 'fat': int}
    Returns None if essential data (current weight, height) is missing.
    """
    if not weight_kg or not height_cm or weight_kg <= 0 or height_cm <= 0:
        return None # Cannot calculate without current weight and height

    # --- Determine the weight to use for BMR/TDEE calculation ---
    calculation_weight = weight_kg # Default to current weight
    if goal_weight_kg is not None and goal_weight_kg > 0:
        calculation_weight = goal_weight_kg # Use goal weight if provided and valid

    # --- Estimate TDEE based on the calculation_weight ---
    estimated_bmr = calculation_weight * 22 # Rough BMR estimate using calculation_weight
    activity_multiplier = 1.3 # Default to light activity
    if fitness_level == 'Beginner':
        activity_multiplier = 1.2
    elif fitness_level == 'Intermediate':
        activity_multiplier = 1.4
    elif fitness_level == 'Advanced':
        activity_multiplier = 1.6

    # TDEE based on the chosen weight (current or goal)
    base_tdee = estimated_bmr * activity_multiplier

    # --- Adjust Calories based on the *difference* between current and goal weight ---
    goal_calories = base_tdee # Start with TDEE calculated using calculation_weight
    calorie_adjustment = 0

    # Determine adjustment based on current vs goal weight (if goal weight exists)
    if goal_weight_kg is not None and goal_weight_kg > 0:
        if goal_weight_kg < weight_kg: # Goal is to lose weight
            calorie_adjustment = -400 # Apply deficit
        elif goal_weight_kg > weight_kg: # Goal is to gain weight
            calorie_adjustment = 400  # Apply surplus
        # If goal_weight == weight_kg, adjustment remains 0 (maintenance)
    else:
        # Fallback to goal_text if goal_weight is not set (applied to current weight TDEE)
        goal_text_lower = goal_text.lower() if goal_text else ""
        if "lose" in goal_text_lower or "weight loss" in goal_text_lower or "cut" in goal_text_lower:
            calorie_adjustment = -400
        elif "gain" in goal_text_lower or "build muscle" in goal_text_lower or "bulk" in goal_text_lower:
            calorie_adjustment = 400

    goal_calories += calorie_adjustment

    # Ensure minimum calories
    goal_calories = max(1200, goal_calories) # Set a minimum floor

    # --- Calculate Macronutrients based on Goal Text and final goal_calories ---
    # Goal text still influences macro splits
    protein_percent = 0.30 # Default 30%
    carb_percent = 0.40    # Default 40%
    fat_percent = 0.30     # Default 30%
    goal_text_lower = goal_text.lower() if goal_text else "" # Recalculate goal_text_lower here

    # ... existing macro percentage adjustments based on goal_text_lower ...
    if "lose" in goal_text_lower or "weight loss" in goal_text_lower or "cut" in goal_text_lower:
        protein_percent = 0.35 # Higher protein for satiety/muscle preservation
        carb_percent = 0.35    # Lower carbs
        fat_percent = 0.30
    elif "gain" in goal_text_lower or "build muscle" in goal_text_lower or "bulk" in goal_text_lower:
        protein_percent = 0.30 # High protein
        carb_percent = 0.45    # Higher carbs for energy/glycogen
        fat_percent = 0.25
    elif "endurance" in goal_text_lower or "run" in goal_text_lower or "cardio" in goal_text_lower:
        protein_percent = 0.25 # Moderate protein
        carb_percent = 0.50    # Higher carbs for fuel
        fat_percent = 0.25


    # Calculate grams from percentages using the *final* goal_calories
    goal_protein_g = (goal_calories * protein_percent) / 4
    goal_carbs_g = (goal_calories * carb_percent) / 4
    goal_fat_g = (goal_calories * fat_percent) / 9

    # Optional: Ensure minimum protein based on *current* weight as a fallback/check
    # Using current weight here might be safer, especially during weight loss
    min_protein_g = weight_kg * 1.2 # Example minimum based on current weight
    goal_protein_g = max(goal_protein_g, min_protein_g)

    # Ensure non-negative values
    goal_protein_g = max(0, goal_protein_g)
    goal_carbs_g = max(0, goal_carbs_g)
    goal_fat_g = max(0, goal_fat_g)

    return {
        'calories': int(round(goal_calories)),
        'protein': int(round(goal_protein_g)),
        'carbs': int(round(goal_carbs_g)),
        'fat': int(round(goal_fat_g))
    }

# --- Routes ---

@app.route('/')
@login_required # Protect the dashboard
def index():
    profile_data = current_user.profile
    # Fetch recent logs
    recent_workout = current_user.workout_logs.order_by(WorkoutLog.log_time.desc()).first()
    recent_meal = current_user.meal_logs.order_by(MealLog.log_time.desc()).first()

    # Fetch latest weight for progress overview text
    latest_weight = profile_data.weight if profile_data else None
    goal_weight = profile_data.goal_weight if profile_data else None # Get goal weight

    # --- Prepare Weight Chart Data ---
    weight_logs = WeightLog.query.filter_by(user_id=current_user.id)\
                                 .order_by(WeightLog.log_time.asc())\
                                 .limit(30).all() # Get last 30 entries for the chart

    weight_chart_labels = [log.log_time.strftime('%Y-%m-%d') for log in weight_logs]
    weight_chart_data = [log.weight for log in weight_logs]
    # --- End Weight Chart Data ---

    # --- Calculate Today's Summary ---
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)

    # Meal Totals
    todays_meals = MealLog.query.filter(
        MealLog.user_id == current_user.id,
        MealLog.log_time >= today_start,
        MealLog.log_time <= today_end
    ).all()
    calories_consumed = sum(meal.calories for meal in todays_meals if meal.calories)
    protein_consumed = sum(meal.protein for meal in todays_meals if meal.protein)
    carbs_consumed = sum(meal.carbs for meal in todays_meals if meal.carbs)
    fat_consumed = sum(meal.fat for meal in todays_meals if meal.fat)

    # Workout Totals
    todays_workouts = WorkoutLog.query.filter(
        WorkoutLog.user_id == current_user.id,
        WorkoutLog.log_time >= today_start,
        WorkoutLog.log_time <= today_end
    ).all()
    # Explicitly set calories_burned to 0 as WorkoutLog doesn't track it yet
    calories_burned = 0
    # calories_burned = sum(workout.calories_burned for workout in todays_workouts if hasattr(workout, 'calories_burned') and workout.calories_burned) # Original line (commented out)

    # Net Calories
    net_calories = calories_consumed - calories_burned
    # --- End Today's Summary ---

    # Get current date/time for the template
    now = datetime.utcnow() # Or datetime.now() depending on timezone needs

    # Placeholder data for dashboard widgets (can be removed or enhanced)
    today_workout = "Plan your workout!" # Default message
    meal_plan_summary = "Log your meals!" # Default message
    # Add current_year to context for footer
    current_year = now.year # Use 'now' to get the year

    return render_template('index.html', title='Dashboard', user=current_user, profile=profile_data,
                           today_workout=today_workout, meal_plan_summary=meal_plan_summary,
                           recent_workout=recent_workout, recent_meal=recent_meal,
                           latest_weight=latest_weight, # Pass latest weight for text display
                           goal_weight=goal_weight,     # Pass goal weight
                           weight_chart_labels=weight_chart_labels, # Pass chart labels
                           weight_chart_data=weight_chart_data,     # Pass chart data
                           # Pass Today's Summary Data
                           calories_consumed=calories_consumed,
                           calories_burned=calories_burned, # Pass the calculated (now 0) value
                           net_calories=net_calories,
                           protein_consumed=protein_consumed,
                           carbs_consumed=carbs_consumed,
                           fat_consumed=fat_consumed,
                           now=now, # Pass the current datetime object
                           current_year=current_year) # Pass current_year

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember')) # Add 'remember me' checkbox in template
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', title='Login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        # Account Info
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Basic Validation for Account Info
        if not username or not email or not password:
             flash('Username, email, and password are required.', 'warning')
             return redirect(url_for('register')) # Consider re-rendering with entered data

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists.', 'warning')
            return redirect(url_for('register'))

        # Profile Info (from new fields) - use .get with type and default=None
        weight = request.form.get('weight', type=float) # Get as float first
        height = request.form.get('height', type=float) # Get as float first
        goal = request.form.get('goal')
        goal_weight = request.form.get('goal_weight', type=float, default=None)
        fitness_level = request.form.get('fitness_level')
        dietary_preferences = request.form.get('dietary_preferences')

        # --- Server-Side Validation for Required Profile Fields ---
        error_messages = []
        if weight is None or weight <= 0:
            error_messages.append('Valid current weight is required.')
        if height is None or height <= 0:
            error_messages.append('Valid height is required.')
        if not goal:
            error_messages.append('Primary goal is required.')
        if not fitness_level:
            error_messages.append('Fitness level is required.')

        if error_messages:
            for msg in error_messages:
                flash(msg, 'danger')
            # Re-render the template, passing back the entered data to repopulate the form
            return render_template('register.html', title='Register',
                                   username=username, email=email, # Pass back account info
                                   weight=request.form.get('weight'), # Pass back raw string values
                                   height=request.form.get('height'),
                                   goal=goal,
                                   goal_weight=request.form.get('goal_weight'),
                                   fitness_level=fitness_level,
                                   dietary_preferences=dietary_preferences)
        # --- End Validation ---


        # --- Calculate Initial Nutrition Goals ---
        # Pass goal_weight to the estimation function
        estimated_goals = estimate_nutrition_goals(weight, height, goal, fitness_level, goal_weight_kg=goal_weight)
        goal_calories = estimated_goals['calories'] if estimated_goals else None
        goal_protein = estimated_goals['protein'] if estimated_goals else None
        goal_carbs = estimated_goals['carbs'] if estimated_goals else None
        goal_fat = estimated_goals['fat'] if estimated_goals else None

        # Create User
        new_user = User(username=username, email=email, role='user')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush() # Flush to get the new_user.id

        # Create Profile with data from form AND calculated goals
        new_profile = Profile(
            user_id=new_user.id,
            weight=weight,
            height=height,
            goal=goal,
            goal_weight=goal_weight,
            fitness_level=fitness_level,
            dietary_preferences=dietary_preferences,
            goal_calories=goal_calories,
            goal_protein=goal_protein,
            goal_carbs=goal_carbs,
            goal_fat=goal_fat
        )
        db.session.add(new_profile)

        # Log initial weight if provided (already validated to be not None)
        initial_weight_log = WeightLog(weight=weight, user_id=new_user.id)
        db.session.add(initial_weight_log)

        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    # GET request
    return render_template('register.html', title='Register')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_data = current_user.profile
    if not profile_data: # Should not happen if profile created on register, but good check
        profile_data = Profile(user_id=current_user.id)
        db.session.add(profile_data)
        # db.session.commit() # Commit later after potential updates

    if request.method == 'POST':
        # --- Store OLD values before getting new ones ---
        old_weight = profile_data.weight
        old_height = profile_data.height
        old_goal = profile_data.goal
        old_goal_weight = profile_data.goal_weight
        old_fitness_level = profile_data.fitness_level
        old_goal_calories = profile_data.goal_calories
        old_goal_protein = profile_data.goal_protein
        old_goal_carbs = profile_data.goal_carbs
        old_goal_fat = profile_data.goal_fat
        # --- End Store OLD values ---

        # Get new values from form
        new_weight = request.form.get('weight', type=float)
        new_height = request.form.get('height', type=float)
        new_goal = request.form.get('goal')
        new_goal_weight = request.form.get('goal_weight', type=float, default=None) # Get new goal weight
        new_fitness_level = request.form.get('fitness_level')
        new_dietary_preferences = request.form.get('dietary_preferences')
        # Get manual nutrition goals (None if empty/invalid)
        manual_goal_calories = request.form.get('goal_calories', type=int, default=None)
        manual_goal_protein = request.form.get('goal_protein', type=int, default=None)
        manual_goal_carbs = request.form.get('goal_carbs', type=int, default=None)
        manual_goal_fat = request.form.get('goal_fat', type=int, default=None)

        # --- Determine if recalculation is needed ---
        recalculate = False
        # Check if any core profile field affecting calculation has changed
        if (new_weight is not None and new_weight != old_weight) or \
           (new_height is not None and new_height != old_height) or \
           (new_goal != old_goal) or \
           (new_fitness_level != old_fitness_level) or \
           (new_goal_weight != old_goal_weight): # Check includes None comparison
             recalculate = True

        # Also recalculate if user explicitly cleared manual goals
        if not recalculate: # Only check this if core fields didn't change
            if (manual_goal_calories is None and old_goal_calories is not None) or \
               (manual_goal_protein is None and old_goal_protein is not None) or \
               (manual_goal_carbs is None and old_goal_carbs is not None) or \
               (manual_goal_fat is None and old_goal_fat is not None):
                recalculate = True # Trigger recalculation if manual goals were cleared
        # --- End Recalculation Check ---

        # --- Update basic profile fields first ---
        profile_data.weight = new_weight
        profile_data.height = new_height
        profile_data.goal = new_goal
        profile_data.goal_weight = new_goal_weight # Update goal_weight in profile
        profile_data.fitness_level = new_fitness_level
        profile_data.dietary_preferences = new_dietary_preferences
        # --- End Update basic profile fields ---

        # --- Calculate Nutrition Goals if needed ---
        calculated_goals = None
        if recalculate and new_weight is not None and new_height is not None:
            # Pass new_goal_weight to the estimation function
            calculated_goals = estimate_nutrition_goals(new_weight, new_height, new_goal, new_fitness_level, goal_weight_kg=new_goal_weight)
            if calculated_goals:
                 flash('Nutrition goals automatically recalculated based on profile changes.', 'info')
            elif new_weight > 0 and new_height > 0: # Only flash error if input was valid
                 flash('Could not automatically recalculate nutrition goals. Please check profile data.', 'warning')
        # --- End Calculate Nutrition Goals ---


        # --- Set Final Nutrition Goals ---
        # Priority:
        # 1. Manual goals submitted *in this request*.
        # 2. Calculated goals if recalculation was triggered and successful.
        # 3. Old goals if no manual input and no recalculation needed/successful.

        if manual_goal_calories is not None:
            profile_data.goal_calories = manual_goal_calories
        elif recalculate and calculated_goals: # Use calculated if recalculate triggered & successful
            profile_data.goal_calories = calculated_goals['calories']
        else: # Keep old value otherwise
            profile_data.goal_calories = old_goal_calories

        if manual_goal_protein is not None:
            profile_data.goal_protein = manual_goal_protein
        elif recalculate and calculated_goals:
            profile_data.goal_protein = calculated_goals['protein']
        else:
            profile_data.goal_protein = old_goal_protein

        if manual_goal_carbs is not None:
            profile_data.goal_carbs = manual_goal_carbs
        elif recalculate and calculated_goals:
            profile_data.goal_carbs = calculated_goals['carbs']
        else:
            profile_data.goal_carbs = old_goal_carbs

        if manual_goal_fat is not None:
            profile_data.goal_fat = manual_goal_fat
        elif recalculate and calculated_goals:
            profile_data.goal_fat = calculated_goals['fat']
        else:
            profile_data.goal_fat = old_goal_fat
        # --- End Set Final Nutrition Goals ---

        # Log weight change if it's different and valid
        if new_weight is not None and new_weight != old_weight:
            weight_log_entry = WeightLog(weight=new_weight, user_id=current_user.id)
            db.session.add(weight_log_entry)

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile')) # Redirect back to profile page

    # --- Prepare Weight Chart Data (for GET request) ---
    weight_logs = WeightLog.query.filter_by(user_id=current_user.id)\
                                 .order_by(WeightLog.log_time.asc())\
                                 .all() # Get all entries for the profile chart

    weight_chart_labels = [log.log_time.strftime('%Y-%m-%d') for log in weight_logs]
    weight_chart_data = [log.weight for log in weight_logs]
    # --- End Weight Chart Data ---

    # --- Prepare Workout Progress Chart Data (Last 30 Days) ---
    thirty_days_ago = date.today() - timedelta(days=29)
    workout_counts_by_day = db.session.query(
        cast(WorkoutLog.log_time, Date).label('log_date'),
        func.count(WorkoutLog.id).label('workout_count')
    ).filter(
        WorkoutLog.user_id == current_user.id,
        cast(WorkoutLog.log_time, Date) >= thirty_days_ago
    ).group_by(
        cast(WorkoutLog.log_time, Date)
    ).order_by(
        cast(WorkoutLog.log_time, Date)
    ).all()

    # Create a dictionary for quick lookup
    logs_dict = {log.log_date.strftime('%Y-%m-%d'): log.workout_count for log in workout_counts_by_day}

    # Generate labels and data for the last 30 days, filling in 0s for days with no logs
    progress_chart_labels = [(thirty_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    progress_chart_data = [logs_dict.get(label_date, 0) for label_date in progress_chart_labels]
    # --- End Workout Progress Chart Data ---

    # --- Prepare Calorie Intake Progress Chart Data (Last 30 Days) ---
    thirty_days_ago_calories = date.today() - timedelta(days=29) # Reuse or redefine if needed
    daily_calorie_logs = db.session.query(
        cast(MealLog.log_time, Date).label('log_date'),
        func.sum(MealLog.calories).label('total_calories')
    ).filter(
        MealLog.user_id == current_user.id,
        cast(MealLog.log_time, Date) >= thirty_days_ago_calories
    ).group_by(
        cast(MealLog.log_time, Date)
    ).order_by(
        cast(MealLog.log_time, Date)
    ).all()

    # Create a dictionary for quick lookup
    calorie_logs_dict = {log.log_date.strftime('%Y-%m-%d'): log.total_calories for log in daily_calorie_logs}

    # Generate labels and data for the last 30 days, filling in 0s for days with no logs
    calorie_progress_labels = [(thirty_days_ago_calories + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    calorie_progress_data = [calorie_logs_dict.get(label_date, 0) for label_date in calorie_progress_labels]

    # Get calorie goal from profile
    calorie_goal = profile_data.goal_calories if profile_data else None
    # --- End Calorie Intake Progress Chart Data ---


    return render_template('profile.html', title='Profile', user=current_user, profile_data=profile_data,
                           weight_chart_labels=weight_chart_labels, # Pass weight chart labels
                           weight_chart_data=weight_chart_data,     # Pass weight chart data
                           progress_chart_labels=progress_chart_labels, # Pass progress chart labels
                           progress_chart_data=progress_chart_data,     # Pass progress chart data
                           # Pass calorie progress chart data
                           calorie_progress_labels=calorie_progress_labels,
                           calorie_progress_data=calorie_progress_data,
                           calorie_goal=calorie_goal)

# --- Feature Routes ---

@app.route('/workouts')
@login_required
def workouts():
    # Fetch workouts grouped by the new category structure
    # Define the desired order of categories
    category_order = ['Push', 'Pull', 'Legs', 'Full Body', 'Cardio', 'Yoga/Flexibility']

    # Fetch all workouts first
    all_workouts_query = Workout.query

    # Apply filters if implemented (based on request.args)
    search_term = request.args.get('search')
    intensity_filter = request.args.get('intensity')
    duration_filter = request.args.get('duration')
    category_filter = request.args.get('category') # Use the new category filter

    if search_term:
        all_workouts_query = all_workouts_query.filter(Workout.name.ilike(f"%{search_term}%"))
    if intensity_filter:
        all_workouts_query = all_workouts_query.filter_by(intensity=intensity_filter)
    if duration_filter:
        # Example duration filtering logic (adjust ranges as needed)
        if duration_filter == '1': # < 15 min
            all_workouts_query = all_workouts_query.filter(Workout.duration_est < 15)
        elif duration_filter == '2': # 15-30 min
            all_workouts_query = all_workouts_query.filter(Workout.duration_est >= 15, Workout.duration_est <= 30)
        elif duration_filter == '3': # > 30 min
            all_workouts_query = all_workouts_query.filter(Workout.duration_est > 30)
    if category_filter:
        all_workouts_query = all_workouts_query.filter_by(category=category_filter)


    all_workouts = all_workouts_query.order_by(Workout.name).all()

    # Group workouts by category
    grouped_workouts = defaultdict(list)
    for workout in all_workouts:
        grouped_workouts[workout.category].append(workout)

    # Create an ordered list of tuples (category, workouts_list) based on category_order
    ordered_grouped_workouts = [
        (category, grouped_workouts[category])
        for category in category_order if category in grouped_workouts
    ]
    # Add any remaining categories not in the defined order
    for category, workouts_list in grouped_workouts.items():
        if category not in category_order:
            ordered_grouped_workouts.append((category, workouts_list))


    # Pass current_user's saved workout IDs to template for button state
    saved_workout_ids = {w.id for w in current_user.saved_workouts}

    # Get distinct categories for the filter dropdown
    available_categories = sorted([cat[0] for cat in db.session.query(Workout.category).distinct().all()])


    return render_template('workouts.html', title='Workouts',
                           ordered_grouped_workouts=ordered_grouped_workouts, # Pass the ordered list
                           saved_workout_ids=saved_workout_ids,
                           available_categories=available_categories) # Pass categories for filter

# New route to add a workout to the user's saved list
@app.route('/workouts/add/<int:workout_id>', methods=['POST'])
@login_required
def add_workout(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    if workout not in current_user.saved_workouts:
        current_user.saved_workouts.append(workout)
        db.session.commit()
        flash(f'"{workout.name}" added to My Workouts!', 'success')
    else:
        flash(f'"{workout.name}" is already in My Workouts.', 'info')
    # Redirect back to the workouts page (or potentially the 'my_workouts' page)
    return redirect(request.referrer or url_for('workouts'))

# New route to remove a workout from the user's saved list (Optional but good practice)
@app.route('/workouts/remove/<int:workout_id>', methods=['POST'])
@login_required
def remove_workout(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    if workout in current_user.saved_workouts:
        current_user.saved_workouts.remove(workout)
        db.session.commit()
        flash(f'"{workout.name}" removed from My Workouts.', 'success')
    else:
        flash(f'"{workout.name}" was not found in My Workouts.', 'info')
    # Redirect back to the page the user came from (likely my_workouts)
    return redirect(request.referrer or url_for('my_workouts'))

# Renamed route for displaying saved workouts
@app.route('/my_workouts')
@login_required
def my_workouts():
    # Fetch the workouts saved by the current user
    user_workouts = current_user.saved_workouts.order_by(Workout.name).all()
    return render_template('my_workouts.html', title='My Workouts', workouts=user_workouts)

# Renamed route for logging and viewing progress of a SPECIFIC workout
@app.route('/workout_progress/<string:workout_name>', methods=['GET', 'POST'])
@login_required
def workout_progress(workout_name):
    # Ensure the workout exists in the user's saved list (optional but good practice)
    # workout = current_user.saved_workouts.filter_by(name=workout_name).first_or_404()

    if request.method == 'POST':
        # Logic to save workout log to DB for THIS workout
        # workout_name is already known
        intensity_level = request.form.get('intensity_level')
        repetitions = request.form.get('repetitions')
        notes = request.form.get('notes')

        if not intensity_level and not repetitions: # Require at least one detail
            flash('Please provide intensity level or repetitions.', 'warning')
            return redirect(url_for('workout_progress',
                                    workout_name=workout_name,
                                    intensity_level=intensity_level, # Pass back submitted values
                                    repetitions=repetitions,
                                    notes=notes))

        log = WorkoutLog(
            workout_name=workout_name,
            intensity_level=intensity_level, # Save new field
            repetitions=repetitions,         # Save new field
            notes=notes,
            logger=current_user
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Workout "{workout_name}" logged successfully!', 'success')
        # Redirect back to the same page to show the updated history
        return redirect(url_for('workout_progress', workout_name=workout_name))

    # GET request - Display the form and history
    # Fetch historical logs for this specific workout for the current user
    logs = WorkoutLog.query.filter_by(logger=current_user, workout_name=workout_name)\
                           .order_by(WorkoutLog.log_time.desc())\
                           .all()

    # Render the template, passing workout name, pre-fill data, and logs
    return render_template('workout_progress.html',
                           title=f'Log & Progress: {workout_name}',
                           workout_name=workout_name,
                           logs=logs) # Pass the historical logs

# New route for suggestions
@app.route('/workouts/suggest')
@login_required
def workout_suggest():
    query = request.args.get('q', '') # Get search query from request args
    suggestions = []
    if query:
        # Find workouts where the name contains the query (case-insensitive)
        search = f"%{query}%"
        results = Workout.query.filter(Workout.name.ilike(search)).limit(10).all() # Limit results
        suggestions = [w.name for w in results]
    return jsonify(suggestions)

@app.route('/meals')
@login_required
def meals():
    # Fetch profile for goals
    profile_data = current_user.profile

    # --- Prepare 7-Day Chart Data ---
    today = date.today()
    seven_days_ago = today - timedelta(days=6) # Corrected syntax

    # Query daily sums for the last 7 days
    daily_logs_7_days = db.session.query(
        cast(MealLog.log_time, Date).label('log_date'),
        func.sum(MealLog.calories).label('total_calories'),
        func.sum(MealLog.protein).label('total_protein'),
        func.sum(MealLog.carbs).label('total_carbs'),
        func.sum(MealLog.fat).label('total_fat')
    ).filter(
        MealLog.user_id == current_user.id,
        cast(MealLog.log_time, Date) >= seven_days_ago,
        cast(MealLog.log_time, Date) <= today
    ).group_by(
        cast(MealLog.log_time, Date)
    ).order_by(
        cast(MealLog.log_time, Date)
    ).all()

    # Prepare data for Chart.js (7-day chart) - Restored Logic
    chart_labels_7_days = [(seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    chart_data_7_days = {
        'calories': [0] * 7,
        'protein': [0] * 7,
        'carbs': [0] * 7,
        'fat': [0] * 7,
    }
    logs_dict_7_days = {log.log_date.strftime('%Y-%m-%d'): log for log in daily_logs_7_days}

    for i, label_date_str in enumerate(chart_labels_7_days):
        log = logs_dict_7_days.get(label_date_str)
        if log:
            chart_data_7_days['calories'][i] = log.total_calories or 0
            chart_data_7_days['protein'][i] = log.total_protein or 0
            chart_data_7_days['carbs'][i] = log.total_carbs or 0
            chart_data_7_days['fat'][i] = log.total_fat or 0
    # --- End 7-Day Chart Data ---

    # --- Calculate Today's Summary & Fetch Logs ---
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)

    todays_meal_logs = MealLog.query.filter(
        MealLog.user_id == current_user.id,
        MealLog.log_time >= today_start,
        MealLog.log_time <= today_end
    ).order_by(MealLog.log_time.asc()).all() # Fetch individual logs for today

    today_calories = sum(meal.calories for meal in todays_meal_logs if meal.calories)
    today_protein = sum(meal.protein for meal in todays_meal_logs if meal.protein)
    today_carbs = sum(meal.carbs for meal in todays_meal_logs if meal.carbs)
    today_fat = sum(meal.fat for meal in todays_meal_logs if meal.fat)

    # --- Group Today's Logs by Meal Type ---
    grouped_meals = defaultdict(list)
    meal_types_order = ['Breakfast', 'Lunch', 'Dinner', 'Snack', None] # Define order, None for uncategorized
    for meal in todays_meal_logs:
        grouped_meals[meal.meal_type].append(meal)

    # Create an ordered dictionary or list of tuples for the template
    ordered_grouped_meals = {
        meal_type: grouped_meals[meal_type]
        for meal_type in meal_types_order if meal_type in grouped_meals
    }
    # --- End Grouping ---


    # Pass grouped meals, profile (for goals), 7-day chart data, and today's data
    return render_template('meals.html', title='Meal Log History', # Changed title
                           profile=profile_data,
                           chart_labels=chart_labels_7_days,
                           chart_data=chart_data_7_days,
                           # Pass grouped meals instead of individual list
                           ordered_grouped_meals=ordered_grouped_meals,
                           today_calories=today_calories,
                           today_protein=today_protein,
                           today_carbs=today_carbs,
                           today_fat=today_fat)

# Original route (GET only now, for pre-filling form from links)
@app.route('/track/meal', methods=['GET']) # Changed methods to only allow GET
@login_required
def track_meal():
    # Removed the entire 'if request.method == 'POST':' block

    # GET request: Pre-fill form if data is passed in URL (Still useful if linking from meals page)
    meal_name_prefill = request.args.get('meal_name')
    meal_type_prefill = request.args.get('meal_type')
    calories_prefill = request.args.get('calories')
    protein_prefill = request.args.get('protein')
    carbs_prefill = request.args.get('carbs')
    fat_prefill = request.args.get('fat')
    fiber_prefill = request.args.get('fiber')
    sugar_prefill = request.args.get('sugar')

    # Pass WTForm instance for potential CSRF token and structure
    return render_template('track_meal.html', title='Log Meal',
                           meal_name_prefill=meal_name_prefill,
                           meal_type_prefill=meal_type_prefill,
                           calories_prefill=calories_prefill,
                           protein_prefill=protein_prefill,
                           carbs_prefill=carbs_prefill,
                           fat_prefill=fat_prefill,
                           fiber_prefill=fiber_prefill,
                           sugar_prefill=sugar_prefill)


# New AJAX route for logging meals
@app.route('/track/meal_ajax', methods=['POST'])
@login_required
def track_meal_ajax():
    try:
        # Get data directly from request.form as it's AJAX
        meal_name = request.form.get('meal_name')
        meal_type = request.form.get('meal_type')
        calories = request.form.get('calories', type=int)
        protein = request.form.get('protein', type=float, default=None)
        carbs = request.form.get('carbs', type=float, default=None)
        fat = request.form.get('fat', type=float, default=None)
        fiber = request.form.get('fiber', type=float, default=None)
        sugar = request.form.get('sugar', type=float, default=None)
        notes = request.form.get('notes')

        # Basic validation (similar to original route)
        if not meal_name or calories is None or calories < 0:
             # Return error as JSON
             return jsonify(success=False, message='Meal name and valid calories are required.')

        # Create and save new log entry
        log = MealLog(
            meal_name=meal_name, meal_type=meal_type, calories=calories,
            protein=protein, carbs=carbs, fat=fat, fiber=fiber, sugar=sugar,
            notes=notes, logger=current_user
        )
        db.session.add(log)
        db.session.commit()

        # Recalculate today's summary after saving
        today_start = datetime.combine(date.today(), time.min)
        today_end = datetime.combine(date.today(), time.max)

        # Meal Totals
        todays_meals = MealLog.query.filter(
            MealLog.user_id == current_user.id,
            MealLog.log_time >= today_start, MealLog.log_time <= today_end
        ).all()
        calories_consumed = sum(meal.calories for meal in todays_meals if meal.calories)
        protein_consumed = sum(meal.protein for meal in todays_meals if meal.protein)
        carbs_consumed = sum(meal.carbs for meal in todays_meals if meal.carbs)
        fat_consumed = sum(meal.fat for meal in todays_meals if meal.fat)

        # Workout Totals
        todays_workouts = WorkoutLog.query.filter(
            WorkoutLog.user_id == current_user.id,
            WorkoutLog.log_time >= today_start,
            WorkoutLog.log_time <= today_end
        ).all()
        # Explicitly set calories_burned to 0 as WorkoutLog doesn't track it yet
        calories_burned = 0
        # calories_burned = sum(workout.calories_burned for workout in todays_workouts if hasattr(workout, 'calories_burned') and workout.calories_burned) # Original line (commented out)

        # Net Calories
        net_calories = calories_consumed - calories_burned

        # Get user goals
        profile = current_user.profile
        goal_calories = profile.goal_calories if profile else None
        goal_protein = profile.goal_protein if profile else None
        goal_carbs = profile.goal_carbs if profile else None
        goal_fat = profile.goal_fat if profile else None

        # Return success and updated totals as JSON
        return jsonify(
            success=True,
            calories_consumed=calories_consumed,
            protein_consumed=protein_consumed,
            carbs_consumed=carbs_consumed,
            fat_consumed=fat_consumed,
            net_calories=net_calories,
            calories_burned=calories_burned, # Send the calculated (now 0) value
            goal_calories=goal_calories,
            goal_protein=goal_protein,
            goal_carbs=goal_carbs,
            goal_fat=goal_fat
            # Optionally include details of the last logged meal if needed for another card update
            # last_meal={'name': log.meal_name, 'calories': log.calories, ...}
        )

    except Exception as e:
        db.session.rollback() # Rollback in case of error during commit
        print(f"Error in track_meal_ajax: {e}") # Log the error
        return jsonify(success=False, message='An internal error occurred.')


# New route for meal suggestions with details
@app.route('/meals/suggest')
@login_required
def meal_suggest():
    query = request.args.get('q', '') # Get search query
    suggestions = []
    if query and len(query) > 1: # Only search if query is long enough
        search = f"%{query}%"
        results = Meal.query.filter(Meal.name.ilike(search)).limit(10).all()
        # Return a list of dictionaries with meal details
        suggestions = [
            {
                'name': meal.name,
                'calories': meal.calories_est,
                'protein': meal.protein_est,
                'carbs': meal.carbs_est,
                'fat': meal.fat_est,
                'fiber': meal.fiber_est,
                'sugar': meal.sugar_est,
                'meal_type': meal.meal_type # Include meal_type if needed
            }
            for meal in results
        ]
    return jsonify(suggestions)

# Food Database Search Endpoint (with AI potential)
@app.route('/search_food')
@login_required
def search_food():
    query = request.args.get('q', '').lower()
    if not query or len(query) < 2:
        return jsonify([])

    # --- AI/NLP Integration Point (Future) ---
    # 1. Pre-process query: Correct typos, expand abbreviations, identify units/quantities.
    #    Example: "1 med apple" -> query="apple", quantity=1, unit="medium"
    # 2. Semantic Search: Understand intent beyond keywords.
    #    Example: "morning oats with berries" -> search for "oatmeal", "blueberries", "strawberries" etc.
    # ---

    # --- Placeholder Data & Search Logic ---
    # In a real app, query an external API or local DB using the (potentially AI-processed) query.
    placeholder_db = [
        # Fruits
        {
            "id": "1", "name": "Apple, raw, with skin", "serving_description": "1 medium (182g)",
            "calories": 95, "protein": 0.5, "carbs": 25.1, "fat": 0.3, "fiber": 4.4, "sugar": 18.9
        },
        {
            "id": "2", "name": "Banana, raw", "serving_description": "1 medium (118g)",
            "calories": 105, "protein": 1.3, "carbs": 27, "fat": 0.4, "fiber": 3.1, "sugar": 14.4
        },
        {
            "id": "7", "name": "Orange, raw", "serving_description": "1 medium (154g)",
            "calories": 73, "protein": 1.3, "carbs": 18.1, "fat": 0.2, "fiber": 3.4, "sugar": 14.0
        },
        {
            "id": "8", "name": "Strawberries, raw", "serving_description": "1 cup, whole (144g)",
            "calories": 46, "protein": 1.0, "carbs": 11.1, "fat": 0.4, "fiber": 2.9, "sugar": 7.0
        },
        {
            "id": "9", "name": "Blueberries, raw", "serving_description": "1 cup (148g)",
            "calories": 84, "protein": 1.1, "carbs": 21.4, "fat": 0.5, "fiber": 3.6, "sugar": 14.7
        },
        # Vegetables
        {
            "id": "10", "name": "Broccoli, raw", "serving_description": "1 cup, chopped (91g)",
            "calories": 31, "protein": 2.5, "carbs": 6.0, "fat": 0.3, "fiber": 2.4, "sugar": 1.5
        },
        {
            "id": "11", "name": "Spinach, raw", "serving_description": "1 cup (30g)",
            "calories": 7, "protein": 0.9, "carbs": 1.1, "fat": 0.1, "fiber": 0.7, "sugar": 0.1
        },
        {
            "id": "12", "name": "Carrot, raw", "serving_description": "1 medium (61g)",
            "calories": 25, "protein": 0.6, "carbs": 5.8, "fat": 0.1, "fiber": 1.7, "sugar": 2.9
        },
        {
            "id": "13", "name": "Bell Pepper, red, raw", "serving_description": "1 medium (119g)",
            "calories": 30, "protein": 1.2, "carbs": 6.3, "fat": 0.3, "fiber": 2.1, "sugar": 4.2
        },
        # Grains & Breads
        {
            "id": "5", "name": "Oatmeal, cooked with water", "serving_description": "1 cup cooked (234g)",
            "calories": 158, "protein": 5.9, "carbs": 27.3, "fat": 3.2, "fiber": 4.0, "sugar": 1.1
        },
        {
            "id": "14", "name": "Brown Rice, cooked", "serving_description": "1 cup (195g)",
            "calories": 216, "protein": 5.0, "carbs": 44.8, "fat": 1.8, "fiber": 3.5, "sugar": 0.4
        },
        {
            "id": "15", "name": "White Rice, cooked", "serving_description": "1 cup (158g)",
            "calories": 205, "protein": 4.3, "carbs": 44.5, "fat": 0.4, "fiber": 0.6, "sugar": 0.1
        },
        {
            "id": "16", "name": "Whole Wheat Bread", "serving_description": "1 slice (32g)",
            "calories": 81, "protein": 3.9, "carbs": 13.8, "fat": 1.1, "fiber": 1.9, "sugar": 1.4
        },
        {
            "id": "17", "name": "White Bread", "serving_description": "1 slice (25g)",
            "calories": 66, "protein": 1.9, "carbs": 12.7, "fat": 0.8, "fiber": 0.6, "sugar": 1.1
        },
        # Proteins
        {
            "id": "3", "name": "Chicken Breast, grilled", "serving_description": "3 oz (85g)",
            "calories": 140, "protein": 26, "carbs": 0, "fat": 3, "fiber": 0, "sugar": 0
        },
        {
            "id": "18", "name": "Salmon, Atlantic, cooked", "serving_description": "3 oz (85g)",
            "calories": 175, "protein": 22.1, "carbs": 0, "fat": 8.9, "fiber": 0, "sugar": 0
        },
        {
            "id": "19", "name": "Egg, large, boiled", "serving_description": "1 large (50g)",
            "calories": 78, "protein": 6.3, "carbs": 0.6, "fat": 5.3, "fiber": 0, "sugar": 0.6
        },
        {
            "id": "20", "name": "Tofu, firm", "serving_description": "1/2 cup (126g)",
            "calories": 181, "protein": 21.8, "carbs": 3.5, "fat": 11.0, "fiber": 2.9, "sugar": 0.9
        },
        {
            "id": "21", "name": "Lentils, cooked", "serving_description": "1 cup (198g)",
            "calories": 230, "protein": 17.9, "carbs": 39.9, "fat": 0.8, "fiber": 15.6, "sugar": 1.8
        },
        {
            "id": "22", "name": "Ground Beef, 90% lean, cooked", "serving_description": "3 oz (85g)",
            "calories": 184, "protein": 24.2, "carbs": 0, "fat": 8.8, "fiber": 0, "sugar": 0
        },
        # Dairy & Alternatives
        {
            "id": "23", "name": "Milk, 2% fat", "serving_description": "1 cup (244g)",
            "calories": 122, "protein": 8.1, "carbs": 11.7, "fat": 4.8, "fiber": 0, "sugar": 12.3
        },
        {
            "id": "24", "name": "Yogurt, Greek, plain, nonfat", "serving_description": "1 container (170g)",
            "calories": 97, "protein": 17.3, "carbs": 6.1, "fat": 0.4, "fiber": 0, "sugar": 6.1
        },
        {
            "id": "25", "name": "Cheddar Cheese", "serving_description": "1 oz (28g)",
            "calories": 114, "protein": 6.7, "carbs": 0.9, "fat": 9.4, "fiber": 0, "sugar": 0.1
        },
        {
            "id": "26", "name": "Almond Milk, unsweetened", "serving_description": "1 cup (240ml)",
            "calories": 30, "protein": 1.0, "carbs": 1.0, "fat": 2.5, "fiber": 1.0, "sugar": 0
        },
        # Fats & Oils
        {
            "id": "27", "name": "Olive Oil", "serving_description": "1 tbsp (14g)",
            "calories": 119, "protein": 0, "carbs": 0, "fat": 13.5, "fiber": 0, "sugar": 0
        },
        {
            "id": "28", "name": "Avocado, raw", "serving_description": "1/2 medium (100g)",
            "calories": 160, "protein": 2.0, "carbs": 8.5, "fat": 14.7, "fiber": 6.7, "sugar": 0.7
        },
        {
            "id": "29", "name": "Almonds", "serving_description": "1 oz (approx 23 nuts, 28g)",
            "calories": 164, "protein": 6.0, "carbs": 6.1, "fat": 14.2, "fiber": 3.5, "sugar": 1.2
        },
        # Beverages
        {
            "id": "6", "name": "Apple Juice, unsweetened", "serving_description": "1 cup (248g)",
            "calories": 114, "protein": 0.2, "carbs": 28, "fat": 0.3, "fiber": 0.5, "sugar": 24
        },
        {
            "id": "30", "name": "Coffee, black, brewed", "serving_description": "1 cup (8 fl oz)",
            "calories": 2, "protein": 0.3, "carbs": 0, "fat": 0, "fiber": 0, "sugar": 0
        },
        # Prepared/Mixed Foods (Examples - highly variable)
        {
            "id": "4", "name": "Chicken Salad Sandwich", "serving_description": "1 sandwich",
            "calories": 450, "protein": 20, "carbs": 40, "fat": 22, "fiber": 3, "sugar": 5 # Example estimate
        },
        {
            "id": "31", "name": "Pizza, Cheese, regular crust", "serving_description": "1 slice (1/8 of 14\" pizza)",
            "calories": 285, "protein": 12.2, "carbs": 35.7, "fat": 10.4, "fiber": 2.5, "sugar": 3.8 # Example estimate
        },
        {
            "id": "32", "name": "Caesar Salad with Grilled Chicken", "serving_description": "1 large serving",
            "calories": 550, "protein": 40, "carbs": 15, "fat": 35, "fiber": 5, "sugar": 3 # Example estimate
        },

    ]
    # Simple placeholder keyword matching
    results = [
        food for food in placeholder_db
        if query in food['name'].lower()
    ]
    # --- End Placeholder ---

    # --- AI/NLP Integration Point (Future) ---
    # 3. Rank/Filter Results: Use AI to prioritize the most relevant results based on context or user history.
    # ---

    return jsonify(results[:15]) # Return top 15 matches

# --- Admin Routes ---

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard page."""
    all_users = User.query.order_by(User.username).all()
    # Add current_year to context for footer
    current_year = datetime.utcnow().year
    # Define available roles to pass to the template
    available_roles = ['user', 'admin']
    # Count content items
    workout_count = Workout.query.count()
    meal_count = Meal.query.count()
    return render_template('admin_dashboard.html', title='Admin Dashboard', users=all_users, current_year=current_year, available_roles=available_roles, workout_count=workout_count, meal_count=meal_count) # Pass counts

@app.route('/admin/user/<int:user_id>/set_role', methods=['POST'])
@login_required
@admin_required
def set_user_role(user_id):
    """Allows an admin to change a user's role."""
    user_to_modify = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    available_roles = ['user', 'admin'] # Ensure consistency

    if user_to_modify == current_user:
        flash('Admins cannot change their own role.', 'warning')
        return redirect(url_for('admin_dashboard'))

    if new_role not in available_roles:
        flash(f'Invalid role specified: {new_role}.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if user_to_modify.role != new_role:
        user_to_modify.role = new_role
        db.session.commit()
        flash(f'Successfully updated role for {user_to_modify.username} to {new_role}.', 'success')
    else:
        flash(f'{user_to_modify.username} already has the role {new_role}.', 'info')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Allows an admin to delete a user."""
    user_to_delete = User.query.get_or_404(user_id)

    if user_to_delete == current_user:
        flash('Admins cannot delete their own account.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Check if user is the last admin (optional safeguard)
    admin_count = User.query.filter_by(role='admin').count()
    if user_to_delete.role == 'admin' and admin_count <= 1:
         flash('Cannot delete the last remaining admin account.', 'danger')
         return redirect(url_for('admin_dashboard'))

    username = user_to_delete.username # Get username before deleting
    # Cascading deletes should handle Profile, WorkoutLog, MealLog due to model setup
    # The user_saved_workouts association table entries are also handled automatically
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Successfully deleted user {username} and their associated data.', 'success')
    return redirect(url_for('admin_dashboard'))

# --- Admin Content Management Routes ---

@app.route('/admin/workouts')
@login_required
@admin_required
def admin_workouts():
    """List all predefined workouts for management."""
    all_workouts = Workout.query.order_by(Workout.category, Workout.name).all()
    current_year = datetime.utcnow().year
    return render_template('admin_workouts.html', title='Manage Workouts', workouts=all_workouts, current_year=current_year)

@app.route('/admin/workout/<int:workout_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_workout(workout_id):
    """Deletes a predefined workout."""
    workout_to_delete = Workout.query.get_or_404(workout_id)
    workout_name = workout_to_delete.name

    # Need to handle users who have saved this workout.
    # Option 1: Just delete the workout, saved references will break (bad).
    # Option 2: Remove from user's saved list first (better).
    # Option 3: Prevent deletion if saved by users (safest for now).

    if workout_to_delete.saved_by_users.count() > 0:
        flash(f'Cannot delete workout "{workout_name}" because it is saved by one or more users.', 'warning')
        return redirect(url_for('admin_workouts'))

    # Also consider WorkoutLogs that reference this workout by name.
    # For now, we are not linking logs directly by ID, so deletion is simpler,
    # but logs referencing the deleted name will remain.

    db.session.delete(workout_to_delete)
    db.session.commit()
    flash(f'Successfully deleted workout "{workout_name}".', 'success')
    return redirect(url_for('admin_workouts'))

# New route to display the edit workout form
@app.route('/admin/workout/edit/<int:workout_id>', methods=['GET'])
@login_required
@admin_required
def edit_workout_form(workout_id):
    """Displays the form to edit an existing workout."""
    workout = Workout.query.get_or_404(workout_id)
    current_year = datetime.utcnow().year
    # Pass distinct categories for dropdown
    available_categories = sorted([cat[0] for cat in db.session.query(Workout.category).distinct().all()])
    return render_template('admin_edit_workout.html', title=f'Edit Workout: {workout.name}', workout=workout, current_year=current_year, available_categories=available_categories)

# New route to handle the edit workout form submission
@app.route('/admin/workout/edit/<int:workout_id>', methods=['POST'])
@login_required
@admin_required
def edit_workout(workout_id):
    """Updates an existing workout based on form submission."""
    workout = Workout.query.get_or_404(workout_id)
    original_video_url = workout.video_url # Store original URL before updates

    # Update fields from form data
    workout.name = request.form.get('name', workout.name)
    workout.description = request.form.get('description', workout.description)
    workout.category = request.form.get('category', workout.category)
    workout.intensity = request.form.get('intensity', workout.intensity)
    # Handle potential ValueError if duration is not an integer
    try:
        duration_str = request.form.get('duration_est')
        workout.duration_est = int(duration_str) if duration_str else None
    except ValueError:
        workout.duration_est = None # Or keep original, or handle error differently
        flash('Invalid value for Estimated Duration. Please enter a number.', 'warning')

    workout.equipment = request.form.get('equipment', workout.equipment)
    workout.instructions = request.form.get('instructions', workout.instructions)
    workout.reps_sets = request.form.get('reps_sets', workout.reps_sets)
    workout.form_tips = request.form.get('form_tips', workout.form_tips)
    new_video_url = request.form.get('video_url', '').strip() # Get and strip whitespace

    # --- Validation ---
    errors = {}
    if not workout.name:
        errors['name'] = 'Workout name is required.'
    if not workout.category:
        errors['category'] = 'Category is required.'

    # Validate Standard YouTube URL format if provided
    is_valid_youtube_url = False
    if new_video_url:
        if new_video_url.startswith("https://www.youtube.com/watch?v=") or new_video_url.startswith("https://youtu.be/"):
             # Basic check, could be enhanced with regex to ensure video ID exists
             is_valid_youtube_url = True

    if new_video_url and not is_valid_youtube_url:
        errors['video_url'] = 'Invalid YouTube URL format. Use "https://www.youtube.com/watch?v=..." or "https://youtu.be/...".'
        # Keep the invalid URL in the field for correction
        workout.video_url = new_video_url
    elif not new_video_url:
        workout.video_url = None # Set to None if field is empty
    else:
        # Store the valid standard URL
        workout.video_url = new_video_url

    # If there are any validation errors, re-render the form
    if errors:
        for field, msg in errors.items():
            flash(msg, 'danger') # Still flash for general visibility
        current_year = datetime.utcnow().year
        available_categories = sorted([cat[0] for cat in db.session.query(Workout.category).distinct().all()])
        # Pass the workout object with the potentially invalid data back to the form
        return render_template('admin_edit_workout.html', title=f'Edit Workout: {workout.name}', workout=workout, current_year=current_year, available_categories=available_categories, errors=errors)

    # --- End Validation ---

    # If validation passes, commit changes
    try:
        db.session.commit()
        flash(f'Workout "{workout.name}" updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        # Revert video URL in the object if commit failed, before potentially re-rendering
        workout.video_url = original_video_url
        flash(f'Error updating workout: {e}', 'danger')
        # Optionally re-render form on commit error too
        current_year = datetime.utcnow().year
        available_categories = sorted([cat[0] for cat in db.session.query(Workout.category).distinct().all()])
        return render_template('admin_edit_workout.html', title=f'Edit Workout: {workout.name}', workout=workout, current_year=current_year, available_categories=available_categories, errors={'general': f'Database error: {e}'})


    return redirect(url_for('admin_workouts'))


@app.route('/admin/meals')
@login_required
@admin_required
def admin_meals():
    """List all predefined meals for management."""
    all_meals = Meal.query.order_by(Meal.meal_type, Meal.name).all()
    current_year = datetime.utcnow().year
    return render_template('admin_meals.html', title='Manage Meals', meals=all_meals, current_year=current_year)

@app.route('/admin/meal/<int:meal_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_meal(meal_id):
    """Deletes a predefined meal."""
    meal_to_delete = Meal.query.get_or_404(meal_id)
    meal_name = meal_to_delete.name

    # Similar consideration for MealLogs referencing this meal by name.
    # Deletion is simpler for now as there's no direct foreign key.

    db.session.delete(meal_to_delete)
    db.session.commit()
    flash(f'Successfully deleted meal "{meal_name}".', 'success')
    return redirect(url_for('admin_meals'))


# --- CLI Command for DB Initialization (Commented out for now) ---

# @click.command('init-db')
# @with_appcontext
# def init_db_command():
#     """Clear the existing data and create new tables."""
#     db.create_all()
#     click.echo('Initialized the database.')
#
# app.cli.add_command(init_db_command)


# --- Utility Comments ---
# The app will now attempt to create the DB automatically on first run if 'smartfit.db' is missing.

if __name__ == '__main__':
    # Check if the database file exists, create tables if it doesn't
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}. Creating tables and sample data...")
        with app.app_context():
            db.create_all() # This will now create the WeightLog table too

            # --- Add Sample Admin User ---
            admin_user = User(username='admin', email='admin@example.com', role='admin')
            admin_user.set_password('adminpass') # Use a strong password in production!
            db.session.add(admin_user)
            # Create a profile for the admin user
            admin_profile = Profile(user=admin_user, goal='Maintain System')
            db.session.add(admin_profile)


            # --- Add Sample Data (Restructured Categories & Videos) ---
            # Push Workouts
            w_push1 = Workout(
                name="Classic Push Day", category="Push",
                description="Focuses on chest, shoulders, and triceps.", intensity="Medium", duration_est=50, equipment="Barbell, Dumbbells, Bench",
                instructions="1. Barbell Bench Press (3x8-12)\n2. Overhead Press (3x8-12)\n3. Incline Dumbbell Press (3x10-15)\n4. Lateral Raises (3x12-15)\n5. Triceps Pushdowns (3x12-15)\n6. Overhead Triceps Extension (3x12-15)",
                reps_sets="See instructions", form_tips="Focus on controlled movements and full range of motion.",
                video_url="https://www.youtube.com/watch?v=Au1tQmWt9Qc" # Standard URL
            )
            w_push2 = Workout(
                name="Bodyweight Push Circuit", category="Push",
                description="Chest, shoulders, and triceps using bodyweight.", intensity="Medium", duration_est=30, equipment="None (Optional: Dip Station)",
                instructions="Circuit: 45s work / 15s rest. Repeat 3-4 rounds.\n1. Push-ups (various types)\n2. Pike Push-ups\n3. Triceps Dips (using chair or station)\n4. Plank Shoulder Taps\n5. Diamond Push-ups",
                reps_sets="Circuit based", form_tips="Maintain core stability. Modify exercises as needed.",
                video_url="https://www.youtube.com/watch?v=IODxDxX7oi4" # Standard URL
            )

            # Pull Workouts
            w_pull1 = Workout(
                name="Classic Pull Day", category="Pull",
                description="Focuses on back and biceps.", intensity="Medium", duration_est=50, equipment="Pull-up Bar, Barbell, Dumbbells",
                instructions="1. Pull-ups / Lat Pulldowns (3xAMRAP or 8-12)\n2. Barbell Rows (3x8-12)\n3. Seated Cable Rows (3x10-15)\n4. Face Pulls (3x15-20)\n5. Dumbbell Bicep Curls (3x10-15)\n6. Hammer Curls (3x10-15)",
                reps_sets="See instructions", form_tips="Initiate pulls with your back muscles, not just arms. Control the negative.",
                video_url="https://www.youtube.com/watch?v=JEbWPNCksQs" # Standard URL
            )
            w_pull2 = Workout(
                name="Bodyweight Pull Focus", category="Pull",
                description="Back and biceps using bodyweight and minimal equipment.", intensity="Medium", duration_est=30, equipment="Pull-up Bar (or resistance bands)",
                instructions="1. Pull-ups / Banded Pull-downs (4xAMRAP or 8-15)\n2. Inverted Rows / Bodyweight Rows (4x10-15)\n3. Supermans (3x15-20)\n4. Bicep Curls with Bands / Towel Curls (3x12-15)",
                reps_sets="See instructions", form_tips="Focus on squeezing the back muscles. Use full range of motion.",
                video_url="https://www.youtube.com/watch?v=IMxhZHkH7k4" # Standard URL
            )

            # Leg Workouts
            w_leg1 = Workout(
                name="Classic Leg Day", category="Legs",
                description="Comprehensive lower body workout.", intensity="High", duration_est=60, equipment="Squat Rack, Leg Press, Dumbbells",
                instructions="1. Barbell Squats (3x8-12)\n2. Romanian Deadlifts (3x10-12)\n3. Leg Press (3x10-15)\n4. Leg Extensions (3x12-15)\n5. Hamstring Curls (3x12-15)\n6. Calf Raises (4x15-20)",
                reps_sets="See instructions", form_tips="Prioritize form, especially on squats and deadlifts. Control the weight.",
                video_url="https://www.youtube.com/watch?v=Jpi-uQw84pA" # Standard URL
            )
            w_leg2 = Workout(
                name="Bodyweight Leg Burner", category="Legs",
                description="Lower body workout using only bodyweight.", intensity="Medium", duration_est=30, equipment="None",
                instructions="Circuit: 45s work / 15s rest. Repeat 3-4 rounds.\n1. Squats\n2. Lunges (alternating)\n3. Glute Bridges\n4. Squat Jumps\n5. Calf Raises",
                reps_sets="Circuit based", form_tips="Focus on depth in squats/lunges. Explode on jumps.",
                video_url="https://www.youtube.com/watch?v=bOLzfEmk02k" # Standard URL
            )

            # Full Body Workouts
            w_full1 = Workout(
                name="Full Body Strength (3x Week)", category="Full Body",
                description="Balanced workout targeting major muscle groups.", intensity="Medium", duration_est=45, equipment="Dumbbells, Barbell, Bench",
                instructions="Perform 2-3 times per week with rest days.\n1. Squats (3x8-12)\n2. Bench Press (3x8-12)\n3. Barbell Rows (3x8-12)\n4. Overhead Press (3x10-15)\n5. Romanian Deadlifts (3x10-12)",
                reps_sets="See instructions", form_tips="Focus on compound movements. Ensure adequate recovery.",
                video_url="https://www.youtube.com/watch?v=U0bhE67HuDY" # Standard URL
            )
            w_full2 = Workout(
                name="Bodyweight Full Body Circuit", category="Full Body",
                description="Workout using only bodyweight exercises.", intensity="Medium", duration_est=30, equipment="None",
                instructions="Circuit: 40s work / 20s rest. Repeat 3 rounds.\n1. Squats\n2. Push-ups\n3. Lunges\n4. Plank\n5. Glute Bridges\n6. Jumping Jacks",
                reps_sets="Circuit based", form_tips="Maintain good form throughout. Modify exercises if needed.",
                video_url="https://www.youtube.com/watch?v=gC_L9qAHVJ8" # Standard URL
            )

            # Cardio Workouts
            w_cardio1 = Workout(
                name="HIIT Cardio Blast", 
                category="Cardio",
                description="High-Intensity Interval Training.", 
                intensity="High", 
                duration_est=20, 
                equipment="None",
                instructions="Warm-up (3 min). Perform each exercise for 45 sec, rest 15 sec: Jumping Jacks, High Knees, Burpees, Mountain Climbers, Squat Jumps. Repeat circuit 3 times. Cool-down (3 min).",
                reps_sets="3 rounds (45s work / 15s rest)", 
                form_tips="Maintain high intensity during work periods. Modify as needed.",
                video_url="https://www.youtube.com/watch?v=cZnsLVArIt8" # Standard URL
            )
            
            w_cardio2 = Workout(
                name="Steady State Cardio (Run/Cycle)", 
                category="Cardio",
                description="A moderate-intensity running workout that builds endurance and cardiovascular fitness over time.", 
                intensity="Medium", 
                duration_est=45, 
                equipment="Running shoes, Optional: Treadmill or outdoor path",
                instructions="1. Warm-up (5 min): Start with light jogging and dynamic stretches\n2. Main Session (30-35 min): Run at a steady, conversational pace (you should be able to talk but not sing)\n3. Cool down (5 min): Gradually slow to a walk\n4. Post-run stretches: Focus on calves, quads, hamstrings, and hip flexors\n\nBeginner Tip: Start with a run/walk pattern - 3 minutes running, 2 minutes walking.",
                reps_sets="Continuous effort", 
                form_tips="Keep your head up, shoulders relaxed. Land midfoot rather than heel-striking. Maintain a slight forward lean. Take shorter strides rather than overstriding. Swing arms at 90° angles without crossing the midline of your body.",
                video_url="https://www.youtube.com/watch?v=5umbf4ps0GQ" # Running form video
            )

            # Yoga/Flexibility Workouts
            w_yoga1 = Workout(
                name="Morning Yoga Flow", 
                category="Yoga/Flexibility",
                description="Start your day with a gentle flow.", 
                intensity="Low", 
                duration_est=20, 
                equipment="None (Yoga Mat optional)",
                instructions="Follow the video for a guided flow including Child's Pose, Cat-Cow, Downward Dog, Sun Salutations, etc.",
                reps_sets="Flow based", 
                form_tips="Focus on breath. Move with intention.",
                video_url="https://www.youtube.com/watch?v=v7AYKMP6rOE" # Standard URL
            )

            w_yoga2 = Workout(
                name="Active Recovery / Stretching",
                category="Yoga/Flexibility",
                description="Low-intensity movement and targeted stretching to improve recovery, reduce soreness, and increase range of motion.",
                intensity="Low",
                duration_est=25,
                equipment="Yoga mat, Optional: Foam roller",
                instructions="1. Start with 5 minutes of gentle movement (walking, arm circles, etc.)\n2. Dynamic stretches (30 seconds each):\n   - Leg swings (forward/backward & side-to-side)\n   - Arm circles and shoulder rolls\n   - Torso rotations\n3. Static stretches (hold 30-60 seconds each):\n   - Standing hamstring stretch\n   - Quad stretch\n   - Chest opener\n   - Figure-4 hip stretch\n   - Child's pose\n   - Cat-cow stretch\n   - Downward dog\n4. Optional foam rolling for tight areas (1-2 minutes per muscle group)",
                reps_sets="Hold each stretch for 30-60 seconds, breathing deeply",
                form_tips="Never stretch to the point of pain. Focus on relaxed breathing. Stretches should feel like tension, not pain. For foam rolling, avoid rolling directly on joints or bones.",
                video_url="https://www.youtube.com/watch?v=Ef6LwAaB3_E" # Standard URL
            )

            # Additional specialized workouts (Ensure these are defined correctly)
            w_core = Workout(
                name="Core Crusher",
                category="Home", # Changed category to Home as per previous definition
                description="A focused core workout targeting all areas of the abdominal muscles, obliques, and lower back for strength and stability.",
                intensity="Medium",
                duration_est=15,
                equipment="Exercise mat, Optional: Light dumbbells",
                instructions="Circuit format - perform each exercise for 45 seconds, rest 15 seconds between exercises, and complete 3 rounds:\n\n1. Plank (standard or on forearms)\n2. Russian Twists\n3. Bicycle Crunches\n4. Mountain Climbers\n5. Slow V-Ups\n6. Side Plank (30s each side)\n7. Dead Bugs\n8. Heel Taps\n\nRest 60 seconds between rounds. Focus on controlled movements rather than speed.",
                reps_sets="45 seconds work / 15 seconds rest, 3 rounds",
                form_tips="Engage your core before each movement. Breathe consistently throughout - exhale during exertion. Keep lower back pressed into the mat during floor exercises. Quality over quantity - proper form prevents injury.",
                video_url="https://www.youtube.com/watch?v=7qA3WmqGAoo" # Standard URL
            )

            w_pilates = Workout( # Renamed from w12 to w_pilates for consistency
                name="Pilates Mat",
                category="Home", # Changed category to Home as per previous definition
                description="A flowing sequence of precise movements focusing on core strength, spinal alignment, and whole-body coordination.",
                intensity="Low",
                duration_est=45,
                equipment="Exercise mat",
                instructions="1. Breathing Exercise (2 min): Focus on lateral thoracic breathing\n2. Warm-up (5 min): Gentle spinal articulation, shoulder rolls\n3. Main Sequence (30-35 min):\n   - The Hundred\n   - Roll Up\n   - Single Leg Circles\n   - Rolling Like a Ball\n   - Single Leg Stretch\n   - Double Leg Stretch\n   - Single Straight Leg Stretch\n   - Double Straight Leg Stretch\n   - Criss Cross\n   - Spine Stretch Forward\n   - Open Leg Rocker\n   - Corkscrew\n   - Saw\n4. Cool down (3 min): Child's pose, gentle twists",
                reps_sets="8-10 repetitions of each exercise",
                form_tips="Focus on precision rather than repetitions. Maintain the Pilates stance: navel drawn to spine, ribs connected, shoulders relaxed. Coordinate breathing with movement - typically inhale to prepare, exhale during exertion. Keep neck and shoulders relaxed.",
                video_url="https://www.youtube.com/watch?v=9ATQ-5-1XrE" # Standard URL
            )

            # Add all workouts to the session
            db.session.add_all([
                w_push1, w_push2, w_pull1, w_pull2, w_leg1, w_leg2,
                w_full1, w_full2, w_cardio1, w_cardio2, w_yoga1, w_yoga2,
                w_core, w_pilates # Ensure w_core and w_pilates are included
            ])

            # Sample Meals (Remains the same)
            m1 = Meal(name="Grilled Chicken Salad", description="A healthy and satisfying salad perfect for lunch.",
                      meal_type="Lunch", diet_type="High-Protein, Low-Carb", calories_est=450,
                      protein_est=40.0, carbs_est=15.0, fat_est=25.0, fiber_est=8.0, sugar_est=5.0)
            m2 = Meal(name="Berry Oatmeal", description="A warm and filling start to the day.",
                      meal_type="Breakfast", diet_type="Vegan Option", calories_est=350,
                      protein_est=10.0, carbs_est=60.0, fat_est=8.0, fiber_est=10.0, sugar_est=15.0)
            m3 = Meal(name="Salmon with Roasted Veggies", description="Nutrient-dense dinner.",
                      meal_type="Dinner", diet_type="High-Protein", calories_est=550,
                      protein_est=35.0, carbs_est=40.0, fat_est=28.0, fiber_est=12.0, sugar_est=8.0)
            db.session.add_all([m1, m2, m3])

            # Add an initial weight log for the admin user if weight is set
            if admin_profile.weight:
                 initial_weight_log = WeightLog(weight=admin_profile.weight, user_id=admin_user.id)
                 db.session.add(initial_weight_log)

            # Commit sample data
            db.session.commit()
            print("Database tables and sample data created.")
    else:
        print(f"Database file found at {db_path}.")

    # Ensure you have run the 'flask init-db' command first. # Comment no longer accurate
    print("Starting Flask app...")
    app.run(debug=True)
