from flask import Flask, jsonify, request, session, render_template_string, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import secrets
import json
import logging
import traceback
import os
from dotenv import load_dotenv
from functools import wraps
# Import additional modules at the top
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart



# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.route("/")
def index():
    return send_from_directory('frontend', 'index.html')

@app.route("/admin_dashboard.html")
def admin_dashboard():
    return send_from_directory('frontend', 'admin_dashboard.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('frontend/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('frontend/js', filename)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('frontend/assets', filename)





# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Auth decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        if session.get('user_role') != 'platform_admin':
            return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Database connection
def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            dbname=os.getenv('DB_NAME')
        )
    except psycopg2.Error as err:
        logger.error(f"Database connection error: {err}")
        raise


# Initialize database
def init_db():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            name VARCHAR(255),
            role TEXT CHECK (role IN ('platform_admin', 'company_admin', 'guest')) DEFAULT 'guest',
            is_suspended BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        )
        ''')
        
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE email = 'admin@netdash.com'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            # Create admin user with hashed password
            hashed_password = generate_password_hash('admin123')
            cursor.execute('''
                INSERT INTO users 
                (email, password_hash, first_name, last_name, name, role) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                'admin@netdash.com', 
                hashed_password, 
                'NetDash', 
                'Admin', 
                'NetDash Admin', 
                'platform_admin'
            ))
            db.commit()
            logger.info("Admin user created successfully")
        
        # Create other tables (plans, reviews, contacts)
        tables = {
            'plans': '''
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    features JSON,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'reviews': '''
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    user_id INT,
                    name VARCHAR(255) NOT NULL,
                    rating INT NOT NULL,
                    comment TEXT,
                    is_approved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''',
            'contacts': '''
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT CHECK (status IN ('new', 'responded', 'closed')) DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        }
        
        for table_name, create_table_query in tables.items():
            try:
                cursor.execute(create_table_query)
                db.commit()
                logger.info(f"{table_name} table created or already exists")
            except Exception as e:
                logger.error(f"Error creating {table_name} table: {e}")
        
        db.close()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def update_database_schema():
    """Update the database schema to add missing columns"""
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if user_id column exists in reviews table
        cursor.execute('''
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE table_name = 'reviews' 
            AND TABLE_NAME = 'reviews' 
            AND column_name = 'user_id'
        ''', (os.getenv('DB_NAME', 'product_website'),))
        
        result = cursor.fetchone()
        
        if not result:
            # Add user_id column if it doesn't exist
            logger.info("Adding user_id column to reviews table")
            try:
                # First, add the column without foreign key
                cursor.execute('ALTER TABLE reviews ADD COLUMN user_id INT')
                db.commit()
                
                # Then add the foreign key constraint
                cursor.execute('ALTER TABLE reviews ADD FOREIGN KEY (user_id) REFERENCES users(id)')
                db.commit()
                
                logger.info("user_id column and foreign key added successfully")
            except psycopg2.Error as e:
                logger.error(f"Error adding user_id column: {e}")
                # If there's an error, try to rollback
                db.rollback()
        else:
            logger.info("user_id column already exists in reviews table")
        
        cursor.close()
        db.close()
        
    except Exception as e:
        logger.error(f"Database schema update error: {e}")
        if 'db' in locals():
            db.close()


# Routes
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'success', 'message': 'Logged out successfully'}), 200

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate input
        if not all(key in data for key in ['email', 'password', 'first_name', 'last_name']):
            return jsonify({
                'status': 'error', 
                'message': 'All fields are required'
            }), 400
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Hash password
        hashed_password = generate_password_hash(data['password'])
        
        # Create name from first_name and last_name
        name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
        
        # If name is empty, use email as fallback
        if not name:
            name = data['email'].split('@')[0]
        
        # Set role - check if it's specified, otherwise default to 'guest'
        role = data.get('role', 'guest')
        
        # Make sure role is valid
        if role not in ['platform_admin', 'company_admin', 'guest']:
            role = 'guest'
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users 
            (email, password_hash, first_name, last_name, name, role) 
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data['email'], 
            hashed_password, 
            data.get('first_name', ''), 
            data.get('last_name', ''), 
            name,
            role
        ))
        
        db.commit()
        
        # Send welcome email if configured
        if name and data['email']:
            send_welcome_email(data['email'], name)
        
        return jsonify({
            'status': 'success', 
            'message': 'User registered successfully'
        }), 201
    
    except psycopg2.Error as e:
        logger.error(f"Registration integrity error: {e}")
        return jsonify({
            'status': 'error', 
            'message': 'Email already exists'
        }), 400
    
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'status': 'error', 
            'message': 'An unexpected error occurred during registration'
        }), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Profile Routes
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return jsonify(user), 200
    
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Analytics Routes
@app.route('/api/analytics', methods=['GET'])
@admin_required
def get_analytics():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get total users
        cursor.execute('SELECT COUNT(*) as count FROM users')
        total_users = cursor.fetchone()['count']
        
        # Get active subscriptions (counting completed purchases)
        cursor.execute('''
            SELECT COUNT(*) as count FROM purchases 
            WHERE status = 'completed'
        ''')
        completed_subscriptions = cursor.fetchone()['count']
        
        # Get pending subscriptions (counting pending purchases)
        cursor.execute('''
            SELECT COUNT(*) as count FROM purchases 
            WHERE status = 'pending'
        ''')
        pending_subscriptions = cursor.fetchone()['count']
        
        # Calculate active subscriptions (you can decide whether to include pending ones)
        # Option 1: Count only completed as active
        # active_subscriptions = completed_subscriptions
        
        # Option 2: Count both pending and completed as active
        active_subscriptions = completed_subscriptions + pending_subscriptions
        
        # Get total reviews
        cursor.execute('SELECT COUNT(*) as count FROM reviews')
        total_reviews = cursor.fetchone()['count']
        
        # Get pending contacts
        cursor.execute('SELECT COUNT(*) as count FROM contacts WHERE status = "new"')
        pending_contacts = cursor.fetchone()['count']
        
        return jsonify({
            'total_users': total_users,
            'active_subscriptions': active_subscriptions,
            'completed_subscriptions': completed_subscriptions,
            'pending_subscriptions': pending_subscriptions,
            'total_reviews': total_reviews,
            'pending_contacts': pending_contacts
        }), 200
    
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# User Management Routes
@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        search_term = request.args.get('search', '')
        
        if search_term:
            cursor.execute('''
                SELECT id, first_name, last_name, email, role, is_suspended, created_at 
                FROM users 
                WHERE email LIKE %s OR first_name LIKE %s OR last_name LIKE %s
            ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        else:
            cursor.execute('''
                SELECT id, first_name, last_name, email, role, is_suspended, created_at 
                FROM users
            ''')
        
        users = cursor.fetchall()
        return jsonify(users), 200
    
    except Exception as e:
        logger.error(f"Users error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT id, first_name, last_name, email, role, is_suspended, created_at 
            FROM users WHERE id = %s
        ''', (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Add name field for compatibility
        user['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        user['plan_name'] = 'Free Trial'  # Placeholder
        
        return jsonify(user), 200
    
    except Exception as e:
        logger.error(f"User details error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/users/<int:user_id>/suspend', methods=['POST'])
@admin_required
def suspend_user(user_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('UPDATE users SET is_suspended = TRUE WHERE id = %s', (user_id,))
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'User suspended successfully'}), 200
    
    except Exception as e:
        logger.error(f"Suspend user error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/users/<int:user_id>/unsuspend', methods=['POST'])
@admin_required
def unsuspend_user(user_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('UPDATE users SET is_suspended = FALSE WHERE id = %s', (user_id,))
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'User unsuspended successfully'}), 200
    
    except Exception as e:
        logger.error(f"Unsuspend user error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Plans Routes
@app.route('/api/plans', methods=['GET'])
@login_required  # Change from @admin_required to @login_required
def get_plans():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # For admin view, include all plans with is_active status
        # For company_admin/guest view, only show active plans
        if session.get('user_role') == 'platform_admin':
            cursor.execute('SELECT * FROM plans')
        else:
            cursor.execute('SELECT * FROM plans WHERE is_active = TRUE')
        
        plans = cursor.fetchall()
        
        # Parse JSON features
        for plan in plans:
            if plan['features']:
                try:
                    plan['features'] = json.loads(plan['features'])
                except:
                    plan['features'] = []
        
        return jsonify(plans), 200
    
    except Exception as e:
        logger.error(f"Plans error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/plans', methods=['POST'])
@admin_required
def create_plan():
    try:
        data = request.get_json()
        
        db = get_db_connection()
        cursor = db.cursor()
        
        features = json.dumps(data.get('features', []))
        
        cursor.execute('''
            INSERT INTO plans (name, price, features) 
            VALUES (%s, %s, %s)
        ''', (data['name'], data['price'], features))
        
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'Plan created successfully'}), 201
    
    except Exception as e:
        logger.error(f"Create plan error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Reviews Routes
@app.route('/api/reviews', methods=['GET'])
@admin_required
def get_reviews():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('SELECT * FROM reviews ORDER BY created_at DESC')
        reviews = cursor.fetchall()
        
        return jsonify(reviews), 200
    
    except Exception as e:
        logger.error(f"Reviews error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()


# Contacts Routes
@app.route('/api/contacts', methods=['GET'])
@admin_required
def get_contacts():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('SELECT * FROM contacts ORDER BY created_at DESC')
        contacts = cursor.fetchall()
        
        return jsonify(contacts), 200
    
    except Exception as e:
        logger.error(f"Contacts error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/contact', methods=['POST'])
def create_contact():
    try:
        data = request.get_json()
        
        # Validate input
        if not all(key in data for key in ['name', 'email', 'message']):
            return jsonify({
                'status': 'error', 
                'message': 'Name, email and message are required'
            }), 400
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Insert new contact message
        cursor.execute('''
            INSERT INTO contacts (name, email, message, status) 
            VALUES (%s, %s, %s, %s)
        ''', (
            data['name'], 
            data['email'], 
            data['message'],
            'new'  # Default status for new messages
        ))
        
        db.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'Contact message sent successfully'
        }), 201
    
    except Exception as e:
        logger.error(f"Create contact error: {e}")
        return jsonify({
            'status': 'error', 
            'message': 'An unexpected error occurred'
        }), 500
    
    finally:
        if 'db' in locals():
            db.close()


  # Profile Management Routes
@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        data = request.get_json()
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Update user profile
        update_fields = []
        params = []
        
        if 'first_name' in data:
            update_fields.append('first_name = %s')
            params.append(data['first_name'])
        
        if 'last_name' in data:
            update_fields.append('last_name = %s')
            params.append(data['last_name'])
        
        if 'name' in data:
            update_fields.append('name = %s')
            params.append(data['name'])
        
        if update_fields:
            params.append(session['user_id'])
            cursor.execute(f'''
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = %s
            ''', params)
            db.commit()
        
        return jsonify({'status': 'success', 'message': 'Profile updated successfully'}), 200
    
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/profile', methods=['DELETE'])
@login_required
def delete_account():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Delete user account
        cursor.execute('DELETE FROM users WHERE id = %s', (session['user_id'],))
        db.commit()
        
        # Clear session
        session.clear()
        
        return jsonify({'status': 'success', 'message': 'Account deleted successfully'}), 200
    
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Company Admin Reviews Route
@app.route('/api/reviews', methods=['POST'])
@login_required
def create_review_by_user():
    try:
        data = request.get_json()
        
        # Get user info
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('SELECT name, role FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Only company_admin and guest users can create reviews
        if user['role'] not in ['company_admin', 'guest']:
            return jsonify({'status': 'error', 'message': 'Unauthorized to create review'}), 403
        
        cursor.execute('''
            INSERT INTO reviews (user_id, name, rating, comment) 
            VALUES (%s, %s, %s, %s)
        ''', (session['user_id'], user['name'], data['rating'], data['comment']))
        
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'Review submitted successfully'}), 201
    
    except Exception as e:
        logger.error(f"Create review error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Purchase Management Routes
@app.route('/api/purchase', methods=['POST'])
@login_required
def create_purchase():
    try:
        data = request.get_json()
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create purchase record
        cursor.execute('''
            INSERT INTO purchases (user_id, plan_id, amount, status, purchase_date) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            session['user_id'], 
            data['plan_id'], 
            data['amount'], 
            'pending', 
            datetime.now()
        ))
        
        purchase_id = cursor.lastrowid
        db.commit()
        
        # Send email notification but don't let failures affect the response
        try:
            email_sent = send_purchase_notification(session.get('user_email', ''), purchase_id)
            if not email_sent:
                logger.warning(f"Failed to send purchase confirmation email to user {session['user_id']}")
        except Exception as e:
            logger.error(f"Email dispatch error: {e}")
            # Continue the process despite email failures
        
        return jsonify({
            'status': 'success', 
            'message': 'Purchase initiated successfully',
            'purchase_id': purchase_id,
            'email_status': 'pending'  # Indicate that email might be sent asynchronously
        }), 201
    
    except Exception as e:
        logger.error(f"Create purchase error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/purchases', methods=['GET'])
@admin_required
def get_purchases():
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT p.*, u.name as user_name, u.email, pl.name as plan_name 
            FROM purchases p
            JOIN users u ON p.user_id = u.id
            JOIN plans pl ON p.plan_id = pl.id
            ORDER BY p.purchase_date DESC
        ''')
        
        purchases = cursor.fetchall()
        return jsonify(purchases), 200
    
    except Exception as e:
        logger.error(f"Get purchases error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Demo System Routes
@app.route('/api/demo/start', methods=['POST'])
def start_demo():
    try:
        data = request.get_json()
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create demo session
        demo_token = secrets.token_urlsafe(32)
        expiry_time = datetime.now() + timedelta(hours=1)  # 1 hour demo
        
        cursor.execute('''
            INSERT INTO demo_sessions (token, email, expiry_time, features_accessed) 
            VALUES (%s, %s, %s, %s)
        ''', (demo_token, data.get('email', ''), expiry_time, '{}'))
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'demo_token': demo_token,
            'expiry_time': expiry_time.isoformat()
        }), 201
    
    except Exception as e:
        logger.error(f"Start demo error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/demo/access/<token>', methods=['GET'])
def access_demo(token):
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('''
            SELECT * FROM demo_sessions 
            WHERE token = %s AND expiry_time > NOW()
        ''', (token,))
        
        demo_session = cursor.fetchone()
        
        if not demo_session:
            return jsonify({'status': 'error', 'message': 'Invalid or expired demo'}), 404
        
        # Return demo data
        return jsonify({
            'status': 'success',
            'demo_active': True,
            'remaining_time': demo_session['expiry_time'].isoformat(),
            'features': ['Real-time Monitoring', 'Basic Analytics', 'Threat Detection']
        }), 200
    
    except Exception as e:
        logger.error(f"Access demo error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Email Notification Functions
def send_purchase_notification(email, purchase_id):
    try:
        # This is a basic implementation - you'd need to configure SMTP settings
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not all([smtp_username, smtp_password]):
            logger.warning("SMTP not configured - email not sent")
            return False
            
        # Log the email sending attempt
        logger.info(f"Attempting to send purchase notification to {email} for purchase ID {purchase_id}")
        
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email
        msg['Subject'] = "Purchase Confirmation - NetDash"
        
        body = f"""
        <html>
        <body>
            <h2>Thank you for your purchase!</h2>
            <p>Your purchase ID is: <strong>{purchase_id}</strong></p>
            <p>We'll process your order shortly and send you access details.</p>
            <p>Best regards,<br>The NetDash Team</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # More detailed error handling and logging
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent successfully to {email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication Error: {e}")
            # Don't let email failures affect the user's purchase experience
            return False
        except Exception as e:
            logger.error(f"Email sending error (SMTP): {e}")
            return False
            
    except Exception as e:
        logger.error(f"Email preparation error: {e}")
        return False

def send_welcome_email(email, name):
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not all([smtp_username, smtp_password]):
            logger.warning("SMTP not configured - email not sent")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email
        msg['Subject'] = "Welcome to NetDash!"
        
        body = f"""
        <html>
        <body>
            <h2>Welcome to NetDash, {name}!</h2>
            <p>Thank you for joining our cybersecurity platform.</p>
            <p>You can now access all features available in your plan.</p>
            <p>Best regards,<br>The NetDash Team</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Email sending error: {e}")
        return False

# Purchase status update route
@app.route('/api/purchases/<int:purchase_id>/status', methods=['PUT'])
@admin_required
def update_purchase_status(purchase_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'completed', 'failed', 'refunded']:
            return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # Check if purchase exists
        cursor.execute('SELECT * FROM purchases WHERE id = %s', (purchase_id,))
        if cursor.fetchone() is None:
            return jsonify({'status': 'error', 'message': 'Purchase not found'}), 404
        
        # Update purchase status
        cursor.execute('UPDATE purchases SET status = %s WHERE id = %s', (new_status, purchase_id))
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'Purchase status updated successfully'}), 200
    
    except Exception as e:
        logger.error(f"Update purchase status error: {e}")
        return jsonify({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

# Email configuration route
@app.route('/api/email-config', methods=['POST'])
@admin_required
def update_email_config():
    try:
        data = request.get_json()
        
        # In a real application, you would save these to a configuration table
        # For now, we'll update environment variables (not persistent)
        os.environ['SMTP_SERVER'] = data.get('smtp_server', 'smtp.gmail.com')
        os.environ['SMTP_PORT'] = str(data.get('smtp_port', 587))
        os.environ['SMTP_USERNAME'] = data.get('smtp_username', '')
        os.environ['SMTP_PASSWORD'] = data.get('smtp_password', '')
        
        return jsonify({'status': 'success', 'message': 'Email configuration updated successfully'}), 200
    
    except Exception as e:
        logger.error(f"Email config error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500

# Company admin route to serve the company dashboard
@app.route('/company_dashboard.html')
@login_required
def company_dashboard():
    # Check if user is company_admin
    if session.get('user_role') != 'company_admin':
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    return send_from_directory('frontend', 'company_dashboard.html')

# Route for company admins to access after login
@app.route('/api/redirect-after-login', methods=['GET'])
@login_required
def redirect_after_login():
    user_role = session.get('user_role')
    
    if user_role == 'platform_admin':
        return jsonify({'redirect': '/admin_dashboard.html'}), 200
    elif user_role == 'company_admin':
        return jsonify({'redirect': '/company_dashboard.html'}), 200
    else:
        return jsonify({'redirect': '/'}), 200

# Enhanced purchase confirmation email
def send_purchase_confirmation(email, name, plan_name):
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not all([smtp_username, smtp_password]):
            logger.warning("SMTP not configured - email not sent")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email
        msg['Subject'] = "Purchase Confirmed - NetDash"
        
        body = f"""
        <html>
        <body>
            <h2>Purchase Confirmed!</h2>
            <p>Dear {name},</p>
            <p>Your purchase of the <strong>{plan_name}</strong> plan has been confirmed and activated.</p>
            <p>You now have access to all features included in your plan.</p>
            <p>If you have any questions, please contact our support team.</p>
            <p>Best regards,<br>The NetDash Team</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Email sending error: {e}")
        return False



# Also make sure to approve some reviews in your admin dashboard
# Add a route to approve reviews
@app.route('/api/reviews/<int:review_id>/approve', methods=['PUT'])
@admin_required
def approve_review(review_id):
    """Approve a review for public display"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('UPDATE reviews SET is_approved = TRUE WHERE id = %s', (review_id,))
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'Review approved successfully'}), 200
    
    except Exception as e:
        logger.error(f"Approve review error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()

@app.route('/api/reviews/<int:review_id>/reject', methods=['PUT'])
@admin_required
def reject_review(review_id):
    """Reject a review (set is_approved to FALSE)"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        cursor.execute('UPDATE reviews SET is_approved = FALSE WHERE id = %s', (review_id,))
        db.commit()
        
        return jsonify({'status': 'success', 'message': 'Review rejected successfully'}), 200
    
    except Exception as e:
        logger.error(f"Reject review error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals():
            db.close()


def insert_approved_test_reviews():
    """Insert sample approved reviews for testing the display"""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Sample reviews that are pre-approved
        sample_reviews = [
            {
                "name": "John Smith",
                "rating": 5,
                "comment": "Excellent service! Highly recommended.",
                "is_approved": True
            },
            {
                "name": "Sarah Johnson",
                "rating": 4,
                "comment": "Great product, would use again. The dashboard is very intuitive.",
                "is_approved": True
            },
            {
                "name": "Michael Brown",
                "rating": 5,
                "comment": "The best cybersecurity tool I've used. Worth every penny!",
                "is_approved": True
            }
        ]
        
        # Insert each sample review
        for review in sample_reviews:
            cursor.execute('''
                INSERT INTO reviews (name, rating, comment, is_approved) 
                VALUES (%s, %s, %s, %s)
            ''', (
                review["name"],
                review["rating"],
                review["comment"],
                review["is_approved"]
            ))
        
        db.commit()
        print("Pre-approved test reviews inserted successfully!")
        
    except Exception as e:
        print(f"Error inserting test reviews: {e}")
    finally:
        if 'db' in locals():
            db.close()

# Add this route for quick testing - REMOVE IN PRODUCTION
@app.route('/api/debug/insert-approved-reviews', methods=['GET'])
def test_insert_approved_reviews():
    """Debug endpoint to insert pre-approved test reviews"""
    try:
        insert_approved_test_reviews()
        return jsonify({'status': 'success', 'message': 'Approved test reviews inserted'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Modify your get_public_reviews function to also include debug info in development
# Add or update this endpoint in your Flask app.py file

@app.route('/api/reviews/public', methods=['GET'])
def get_public_reviews():
    """Get all reviews for public display"""
    try:
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Simple query without WHERE clause
        cursor.execute('''
            SELECT id, name, rating, comment, created_at 
            FROM reviews
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        
        reviews = cursor.fetchall()
        
        # Format dates for JSON serialization
        for review in reviews:
            if review['created_at']:
                review['created_at'] = review['created_at'].isoformat()
        
        return jsonify(reviews), 200
    
    except Exception as e:
        logger.error(f"Public reviews error: {e}")
        return jsonify([]), 200
    
    finally:
        if 'db' in locals() and hasattr(db, 'is_connected') and db.is_connected():
            db.close()


@app.route('/api/debug/db-test', methods=['GET'])
def test_database_connection():
    """Test database connection and table structure"""
    db = None
    cursor = None
    results = {
        "database_connection": False,
        "reviews_table_exists": False,
        "can_query_reviews": False,
        "errors": []
    }
    
    try:
        # Test database connection
        db = get_db_connection()
        results["database_connection"] = True
        
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if reviews table exists
        try:
            cursor.execute("SELECT to_regclass('public.reviews')")
            if cursor.fetchone():
                results["reviews_table_exists"] = True
            else:
                results["errors"].append("Reviews table does not exist")
        except Exception as e:
            results["errors"].append(f"Error checking tables: {str(e)}")
        
        # Test querying reviews table
        if results["reviews_table_exists"]:
            try:
                cursor.execute("SELECT COUNT(*) as count FROM reviews")
                count = cursor.fetchone()["count"]
                results["can_query_reviews"] = True
                results["reviews_count"] = count
            except Exception as e:
                results["errors"].append(f"Error querying reviews: {str(e)}")
                
            # Check table structure
            try:
                cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'reviews'")
                columns = cursor.fetchall()
                results["table_structure"] = [col["Field"] for col in columns]
            except Exception as e:
                results["errors"].append(f"Error checking table structure: {str(e)}")
        
    except Exception as e:
        results["errors"].append(f"Database connection error: {str(e)}")
    
    finally:
        if cursor:
            cursor.close()
        if db and hasattr(db, 'is_connected') and db.is_connected():
            db.close()
    
    return jsonify(results), 200


    
# REMOVED OLD MYSQL FUNCTION
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'P@ssW0rd'),
        database=os.getenv('DB_NAME', 'product_website')
    )

def fix_reviews_table_manually():
    """Manually fix the reviews table by adding the is_approved column"""
    db = None
    cursor = None
    try:
        print("Connecting to database...")
        db = get_db_connection()
        cursor = db.cursor()
        
        print("Checking if is_approved column exists...")
        cursor.execute('''
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE table_name = 'reviews' 
            AND TABLE_NAME = 'reviews' 
            AND COLUMN_NAME = 'is_approved'
        ''', (os.getenv('DB_NAME', 'product_website'),))
        
        result = cursor.fetchone()
        
        if not result:
            print("Adding is_approved column to reviews table...")
            cursor.execute('ALTER TABLE reviews ADD COLUMN is_approved BOOLEAN DEFAULT TRUE')
            db.commit()
            print("is_approved column added successfully!")
        else:
            print("is_approved column already exists in reviews table.")
        
        # Update existing reviews to be approved
        print("Setting existing reviews to approved...")
        cursor.execute('UPDATE reviews SET is_approved = TRUE')
        db.commit()
        print(f"Updated {cursor.rowcount} reviews to be approved.")
        
        print("Checking reviews table structure...")
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'reviews' AND table_schema = 'public'")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[0]}, Type: {col[1]}, Null: {col[2]}, Key: {col[3]}, Default: {col[4]}")
        
        print("Checking reviews count...")
        cursor.execute('SELECT COUNT(*) FROM reviews')
        count = cursor.fetchone()[0]
        print(f"Total reviews in database: {count}")
        
        print("Fix completed successfully!")
        
    except Exception as e:
        print(f"Error fixing reviews table: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

# Run the fix
if __name__ == "__main__":
    fix_reviews_table_manually()


  # Password reset token store (in production, use a database table)
reset_tokens = {}

@app.route('/api/reset-password', methods=['POST'])
def request_password_reset():
    """Request a password reset link"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'status': 'error', 'message': 'Email is required'}), 400
        
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if user exists
        cursor.execute('SELECT id, first_name, last_name, name FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        
        if not user:
            # Don't reveal that the email doesn't exist
            return jsonify({'status': 'success', 'message': 'If your email is registered, you will receive reset instructions'}), 200
        
        # Generate reset token
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=1)  # Token valid for 1 hour
        
        # Store token (in production, store in database)
        reset_tokens[token] = {
            'user_id': user['id'],
            'email': email,
            'expiry': expiry
        }
        
        # Send reset email
        send_password_reset_email(email, token, user.get('name') or f"{user.get('first_name', '')} {user.get('last_name', '')}")
        
        return jsonify({'status': 'success', 'message': 'Password reset instructions sent'}), 200
    
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals() and hasattr(db, 'is_connected') and db.is_connected():
            db.close()

@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password using token"""
    try:
        if token not in reset_tokens:
            return jsonify({'status': 'error', 'message': 'Invalid or expired token'}), 400
        
        token_data = reset_tokens[token]
        if datetime.now() > token_data['expiry']:
            # Remove expired token
            del reset_tokens[token]
            return jsonify({'status': 'error', 'message': 'Token has expired'}), 400
        
        data = request.get_json()
        new_password = data.get('password')
        
        if not new_password or len(new_password) < 8:
            return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400
        
        # Update password in database
        db = get_db_connection()
        cursor = db.cursor()
        
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', 
                      (hashed_password, token_data['user_id']))
        db.commit()
        
        # Remove used token
        del reset_tokens[token]
        
        return jsonify({'status': 'success', 'message': 'Password has been reset successfully'}), 200
    
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500
    
    finally:
        if 'db' in locals() and hasattr(db, 'is_connected') and db.is_connected():
            db.close()

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session.get('user_id'),
                'email': session.get('user_email'),
                'name': session.get('user_name'),
                'role': session.get('user_role')
            }
        }), 200
    else:
        return jsonify({'authenticated': False}), 200

def send_password_reset_email(email, token, name):
    """Send password reset email"""
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not all([smtp_username, smtp_password]):
            logger.warning("SMTP not configured - password reset email not sent")
            return False
        
        reset_url = f"{request.host_url}reset-password.html?token={token}"
        
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = email
        msg['Subject'] = "NetDash Password Reset"
        
        body = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hello {name},</p>
            <p>We received a request to reset your password for your NetDash account.</p>
            <p>To reset your password, please click the link below:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this password reset, you can ignore this email.</p>
            <p>Best regards,<br>The NetDash Team</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Password reset email error: {e}")
        return False

# Modified login endpoint to support Remember Me
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({
                'status': 'error', 
                'message': 'Email and password are required'
            }), 400
        
        remember_me = data.get('remember', False)
        
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Find user by email
        cursor.execute('SELECT * FROM users WHERE email = %s', (data['email'],))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password_hash'], data['password']):
            return jsonify({
                'status': 'error', 
                'message': 'Invalid credentials'
            }), 401
        
        # Check if account is suspended
        if user.get('is_suspended', False):
            return jsonify({
                'status': 'error', 
                'message': 'Account is suspended'
            }), 403
        
        # Prepare user data
        user_data = {
            'id': user['id'],
            'email': user['email'],
            'role': user['role'],
            'name': user.get('name', ''),
            'first_name': user.get('first_name', ''),
            'last_name': user.get('last_name', '')
        }
        
        # Set session
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        session['user_email'] = user['email']
        session['user_name'] = user.get('name', '')
        
        # Set session to expire in 30 days if remember_me is True
        if remember_me:
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=30)
        
        return jsonify({
            'status': 'success',
            'user': user_data
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'status': 'error', 
            'message': 'An unexpected error occurred'
        }), 500
    finally:
        if 'db' in locals():
            db.close()  

# Update the init_db function to create new tables
def init_db():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            name VARCHAR(255),
            role TEXT CHECK (role IN ('platform_admin', 'company_admin', 'guest')) DEFAULT 'guest',
            is_suspended BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
        )
        ''')
        
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE email = 'admin@netdash.com'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            # Create admin user with hashed password
            hashed_password = generate_password_hash('admin123')
            cursor.execute('''
                INSERT INTO users 
                (email, password_hash, first_name, last_name, name, role) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                'admin@netdash.com', 
                hashed_password, 
                'NetDash', 
                'Admin', 
                'NetDash Admin', 
                'platform_admin'
            ))
            db.commit()
            logger.info("Admin user created successfully")
        
        # Create other tables (plans, reviews, contacts)
        tables = {
            'plans': '''
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    features JSON,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'reviews': '''
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    user_id INT,
                    name VARCHAR(255) NOT NULL,
                    rating INT NOT NULL,
                    comment TEXT,
                    is_approved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''',
            'contacts': '''
                CREATE TABLE IF NOT EXISTS contacts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT CHECK (status IN ('new', 'responded', 'closed')) DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        }
        
        for table_name, create_table_query in tables.items():
            try:
                cursor.execute(create_table_query)
                db.commit()
                logger.info(f"{table_name} table created or already exists")
            except Exception as e:
                logger.error(f"Error creating {table_name} table: {e}")
        
        # Add new tables for the missing features
        new_tables = {
            'purchases': '''
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL,
                    plan_id INT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    status TEXT CHECK (status IN ('pending', 'completed', 'failed', 'refunded')) DEFAULT 'pending',
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (plan_id) REFERENCES plans(id)
                )
            ''',
            'demo_sessions': '''
                CREATE TABLE IF NOT EXISTS demo_sessions (
                    id SERIAL PRIMARY KEY,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255),
                    expiry_time TIMESTAMP NOT NULL,
                    features_accessed JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            'email_config': '''
                CREATE TABLE IF NOT EXISTS email_config (
                    id SERIAL PRIMARY KEY,
                    smtp_server VARCHAR(255) DEFAULT 'smtp.gmail.com',
                    smtp_port INT DEFAULT 587,
                    smtp_username VARCHAR(255),
                    smtp_password VARCHAR(255),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
                )
            '''
        }
        
        for table_name, create_table_query in new_tables.items():
            try:
                cursor.execute(create_table_query)
                db.commit()
                logger.info(f"{table_name} table created or already exists")
            except Exception as e:
                logger.error(f"Error creating {table_name} table: {e}")
        
        cursor.close()
        db.close()
        
        # Update schema if needed - call this AFTER closing the first connection
        update_database_schema()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        if 'db' in locals():
            db.close()


# Initialize DB on startup (for Render/Gunicorn too)
init_db()


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

