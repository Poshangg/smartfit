# SmartFitness - Fitness & Nutrition Tracker

A web application built with Flask to help users track their workouts, meals, and fitness progress.

## Features

*   **User Authentication:** Secure registration and login.
*   **Profile Management:** Users can set and update their weight, height, goals (including goal weight), fitness level, and dietary preferences.
*   **Workout Tracking:**
    *   Browse a predefined list of workouts categorized by type (Push, Pull, Legs, Full Body, Cardio, Yoga/Flexibility).
    *   View workout details including instructions, equipment, duration, intensity, form tips, and embedded video tutorials (YouTube).
    *   Save favorite workouts to a personal list ("My Workouts").
    *   Log completed workouts with details like intensity, repetitions, and notes.
    *   View historical logs for specific workouts.
*   **Meal Tracking:**
    *   Log meals with details like name, type, calories, macronutrients (protein, carbs, fat), fiber, sugar, and notes.
    *   Search a food database (currently placeholder data) to quickly populate meal details.
    *   View daily meal history grouped by meal type (Breakfast, Lunch, Dinner, Snack).
    *   View daily nutrition summary (calories, macros) with a pie chart visualization.
*   **Progress Visualization:**
    *   **Dashboard:** Quick overview of recent activity, today's nutrition summary, and a 30-day weight trend chart.
    *   **Profile Page:**
        *   Comprehensive weight history chart.
        *   Workout activity chart (workouts logged per day over the last 30 days).
        *   Calorie intake vs. goal chart (last 30 days).
    *   **Meals Page:** 7-day nutrition intake chart (calories and macros).
*   **Nutrition Goal Estimation:** Automatically estimates daily calorie and macronutrient goals based on profile information (weight, height, goal, fitness level, goal weight). Users can also manually override these goals.
*   **Admin Panel:**
    *   Manage users (view list, change roles, delete users).
    *   Manage predefined workout content (view, edit, delete).
    *   Manage predefined meal content (view, delete).

## Technology Stack

*   **Backend:** Python, Flask
*   **Database:** SQLite (via Flask-SQLAlchemy)
*   **Frontend:** HTML, CSS (Bootstrap 5), JavaScript
*   **Charting:** Chart.js (with date-fns adapter and annotation plugin)
*   **Authentication:** Flask-Login
*   **Password Hashing:** Werkzeug

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Smartfitness
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file should be created containing Flask, Flask-SQLAlchemy, Flask-Login, Werkzeug etc.)*
4.  **Run the application:**
    ```bash
    python app.py
    ```
5.  **Access the application:** Open your web browser and go to `http://127.0.0.1:5000` (or the address provided by Flask).

## Database Initialization

The application is configured to automatically create the `smartfit.db` SQLite database file and populate it with initial admin user credentials and sample workout/meal data if the file does not exist when `app.py` is run for the first time.

## Default Admin Credentials

*   **Username:** `admin`
*   **Password:** `adminpass`

*(It is strongly recommended to change the admin password immediately after the first login, especially in a production environment.)*

## Usage

1.  **Register:** Create a new user account, providing basic profile information.
2.  **Login:** Access your dashboard.
3.  **Profile:** Update your personal details, fitness goals, and nutrition targets. View your weight, workout, and calorie progress charts.
4.  **Workouts:** Browse available workouts, view details, add them to "My Workouts", or log them directly.
5.  **My Workouts:** View your saved workouts and log progress for specific exercises.
6.  **Meals:** Log your daily meals using the modal form. Search the food database for quick entry. View your daily and weekly nutrition summaries and history.
7.  **Admin:** (If logged in as admin) Access the `/admin` route to manage users and content.

## Future Enhancements

*   Implement a proper external food database API (e.g., Open Food Facts, USDA FoodData Central).
*   Add calorie burn estimation to workouts.
*   More detailed progress tracking (e.g., exercise-specific strength progression).
*   Workout plan generation based on goals.
*   Social features (sharing progress, challenges).
*   More robust AI/NLP for food search.
*   Unit and integration testing.
*   Deployment configuration (e.g., using Gunicorn/Nginx).
