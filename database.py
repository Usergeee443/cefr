import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'cefr_platform'),
    'pool_name': 'cefr_pool',
    'pool_size': 5
}

# Create connection pool
connection_pool = None

def init_db():
    """Initialize database and create tables"""
    global connection_pool

    # First connect without database to create it if needed
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

    # Create connection pool
    try:
        connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
    except Exception as e:
        print(f"Error creating connection pool: {e}")
        return

    # Create tables
    create_tables()

def get_connection():
    """Get connection from pool"""
    global connection_pool
    if connection_pool is None:
        init_db()
    return connection_pool.get_connection()

def create_tables():
    """Create all necessary tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # Admin users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Reading questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            passage TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a VARCHAR(500) NOT NULL,
            option_b VARCHAR(500) NOT NULL,
            option_c VARCHAR(500) NOT NULL,
            option_d VARCHAR(500) NOT NULL,
            correct_answer CHAR(1) NOT NULL,
            difficulty VARCHAR(10) NOT NULL DEFAULT 'B1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Listening questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listening_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            audio_url VARCHAR(500) NOT NULL,
            transcript TEXT,
            question TEXT NOT NULL,
            option_a VARCHAR(500) NOT NULL,
            option_b VARCHAR(500) NOT NULL,
            option_c VARCHAR(500) NOT NULL,
            option_d VARCHAR(500) NOT NULL,
            correct_answer CHAR(1) NOT NULL,
            difficulty VARCHAR(10) NOT NULL DEFAULT 'B1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Writing prompts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS writing_prompts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            prompt_text TEXT NOT NULL,
            min_words INT DEFAULT 150,
            max_words INT DEFAULT 300,
            difficulty VARCHAR(10) NOT NULL DEFAULT 'B1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Test sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100) UNIQUE NOT NULL,
            reading_score INT DEFAULT 0,
            reading_total INT DEFAULT 0,
            listening_score INT DEFAULT 0,
            listening_total INT DEFAULT 0,
            writing_score FLOAT DEFAULT 0,
            writing_feedback TEXT,
            overall_level VARCHAR(10),
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL
        )
    ''')

    # Test answers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_answers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100) NOT NULL,
            question_type VARCHAR(20) NOT NULL,
            question_id INT NOT NULL,
            user_answer TEXT NOT NULL,
            is_correct BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Survey responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_responses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100) NOT NULL,
            overall_experience INT,
            difficulty_rating INT,
            would_recommend BOOLEAN,
            feedback TEXT,
            improvement_suggestions TEXT,
            age_group VARCHAR(50),
            english_purpose VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

def create_default_admin():
    """Create default admin if not exists"""
    from passlib.hash import bcrypt

    conn = get_connection()
    cursor = conn.cursor()

    # Check if admin exists
    cursor.execute("SELECT id FROM admins WHERE username = 'admin'")
    if cursor.fetchone() is None:
        password_hash = bcrypt.hash('admin123')
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
            ('admin', password_hash)
        )
        conn.commit()

    cursor.close()
    conn.close()

# Reading questions operations
def get_reading_questions(limit=10):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reading_questions ORDER BY RAND() LIMIT %s", (limit,))
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions

def add_reading_question(passage, question, options, correct, difficulty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reading_questions
        (passage, question, option_a, option_b, option_c, option_d, correct_answer, difficulty)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (passage, question, options[0], options[1], options[2], options[3], correct, difficulty))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_reading_questions():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reading_questions ORDER BY created_at DESC")
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions

def delete_reading_question(question_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reading_questions WHERE id = %s", (question_id,))
    conn.commit()
    cursor.close()
    conn.close()

# Listening questions operations
def get_listening_questions(limit=10):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listening_questions ORDER BY RAND() LIMIT %s", (limit,))
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions

def add_listening_question(audio_url, transcript, question, options, correct, difficulty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO listening_questions
        (audio_url, transcript, question, option_a, option_b, option_c, option_d, correct_answer, difficulty)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (audio_url, transcript, question, options[0], options[1], options[2], options[3], correct, difficulty))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_listening_questions():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM listening_questions ORDER BY created_at DESC")
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions

def delete_listening_question(question_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM listening_questions WHERE id = %s", (question_id,))
    conn.commit()
    cursor.close()
    conn.close()

# Writing prompts operations
def get_writing_prompts(limit=1):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM writing_prompts ORDER BY RAND() LIMIT %s", (limit,))
    prompts = cursor.fetchall()
    cursor.close()
    conn.close()
    return prompts

def add_writing_prompt(prompt_text, min_words, max_words, difficulty):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO writing_prompts (prompt_text, min_words, max_words, difficulty)
        VALUES (%s, %s, %s, %s)
    ''', (prompt_text, min_words, max_words, difficulty))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_writing_prompts():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM writing_prompts ORDER BY created_at DESC")
    prompts = cursor.fetchall()
    cursor.close()
    conn.close()
    return prompts

def delete_writing_prompt(prompt_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM writing_prompts WHERE id = %s", (prompt_id,))
    conn.commit()
    cursor.close()
    conn.close()

# Test session operations
def create_test_session(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO test_sessions (session_id) VALUES (%s)", (session_id,))
    conn.commit()
    cursor.close()
    conn.close()

def update_test_session(session_id, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []
    for key, value in kwargs.items():
        updates.append(f"{key} = %s")
        values.append(value)
    values.append(session_id)

    query = f"UPDATE test_sessions SET {', '.join(updates)} WHERE session_id = %s"
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def get_test_session(session_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM test_sessions WHERE session_id = %s", (session_id,))
    session = cursor.fetchone()
    cursor.close()
    conn.close()
    return session

def save_answer(session_id, question_type, question_id, user_answer, is_correct):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO test_answers (session_id, question_type, question_id, user_answer, is_correct)
        VALUES (%s, %s, %s, %s, %s)
    ''', (session_id, question_type, question_id, user_answer, is_correct))
    conn.commit()
    cursor.close()
    conn.close()

# Survey operations
def save_survey(session_id, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO survey_responses
        (session_id, overall_experience, difficulty_rating, would_recommend,
         feedback, improvement_suggestions, age_group, english_purpose)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        session_id,
        data.get('overall_experience'),
        data.get('difficulty_rating'),
        data.get('would_recommend'),
        data.get('feedback'),
        data.get('improvement_suggestions'),
        data.get('age_group'),
        data.get('english_purpose')
    ))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_surveys():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT sr.*, ts.overall_level, ts.reading_score, ts.listening_score, ts.writing_score
        FROM survey_responses sr
        LEFT JOIN test_sessions ts ON sr.session_id = ts.session_id
        ORDER BY sr.created_at DESC
    ''')
    surveys = cursor.fetchall()
    cursor.close()
    conn.close()
    return surveys

# Admin operations
def verify_admin(username, password):
    from passlib.hash import bcrypt

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if admin and bcrypt.verify(password, admin['password_hash']):
        return admin
    return None

# Statistics
def get_statistics():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    stats = {}

    # Total tests
    cursor.execute("SELECT COUNT(*) as count FROM test_sessions WHERE completed_at IS NOT NULL")
    stats['total_tests'] = cursor.fetchone()['count']

    # Average scores
    cursor.execute('''
        SELECT
            AVG(reading_score * 100.0 / NULLIF(reading_total, 0)) as avg_reading,
            AVG(listening_score * 100.0 / NULLIF(listening_total, 0)) as avg_listening,
            AVG(writing_score) as avg_writing
        FROM test_sessions WHERE completed_at IS NOT NULL
    ''')
    avgs = cursor.fetchone()
    stats['avg_reading'] = round(avgs['avg_reading'] or 0, 1)
    stats['avg_listening'] = round(avgs['avg_listening'] or 0, 1)
    stats['avg_writing'] = round(avgs['avg_writing'] or 0, 1)

    # Level distribution
    cursor.execute('''
        SELECT overall_level, COUNT(*) as count
        FROM test_sessions
        WHERE overall_level IS NOT NULL
        GROUP BY overall_level
    ''')
    stats['level_distribution'] = {row['overall_level']: row['count'] for row in cursor.fetchall()}

    # Survey stats
    cursor.execute("SELECT COUNT(*) as count FROM survey_responses")
    stats['total_surveys'] = cursor.fetchone()['count']

    cursor.execute("SELECT AVG(overall_experience) as avg FROM survey_responses")
    stats['avg_experience'] = round(cursor.fetchone()['avg'] or 0, 1)

    cursor.close()
    conn.close()

    return stats
