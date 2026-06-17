import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import Database & Models
from models import db, User, UploadLog, SystemSetting, Transaction
from compressor.core.engine import CompressionEngine

# Initialize Flask App
app = Flask(__name__)

# CRITICAL: SECRET_KEY must be set in environment variables (with random fallback for zero-config deployments)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("⚠️  Warning: SECRET_KEY environment variable is not set. Generated a random ephemeral key.")
app.config['SECRET_KEY'] = SECRET_KEY

# Session Cookie Configuration for iframe compatibility (Hugging Face Spaces)
is_production = os.environ.get('FLASK_ENV', 'production') == 'production' or 'SPACE_ID' in os.environ
if is_production:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True
else:
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False

# Database Setup - Use Environment Variables (SECURITY FIX)
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'pdf_compressor')

# Upload/Download Directories
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'

# Database connection choice (MySQL or SQLite)
USE_SQLITE = os.environ.get('USE_SQLITE', 'true').lower() == 'true'

# Warn if using default credentials in production
if not USE_SQLITE and DB_USER == 'root' and DB_PASSWORD == '' and os.environ.get('FLASK_ENV', 'production') == 'production':
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("⚠️  SECURITY WARNING: Using default MySQL root credentials in production!")

def create_mysql_database_if_not_exists():
    """Create the MySQL database automatically if it doesn't exist."""
    if USE_SQLITE:
        return
    import pymysql
    try:
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            print(f"Database Initializer: MySQL Database '{DB_NAME}' checked/created.")
    except Exception as e:
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            print(f"Database Initializer Warning: Failed to pre-create MySQL database: {e}")

# Pre-create database
create_mysql_database_if_not_exists()

if USE_SQLITE:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(BASE_DIR / 'database.db')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# File upload size limits
MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', 50 * 1024 * 1024))            # Free users: 50MB
MAX_PREMIUM_UPLOAD_SIZE = int(os.environ.get('MAX_PREMIUM_UPLOAD_SIZE', 500 * 1024 * 1024))  # Premium users: 500MB
app.config['MAX_CONTENT_LENGTH'] = MAX_PREMIUM_UPLOAD_SIZE  # Set to premium limit; enforce free limit in route handler

# Ensure directories exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Initialize extensions
db.init_app(app)

# CSRF Protection (SECURITY FIX)
csrf = CSRFProtect(app)

# Rate Limiting (SECURITY FIX)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[os.environ.get('RATELIMIT_DEFAULT', '200 per day, 50 per hour')],
    storage_uri=os.environ.get('REDIS_URL', 'memory://')
)

# Proxy Fix (for correct IP detection and HTTPS detection behind reverse proxy, enabled in production/HF)
if os.environ.get('USE_PROXYFIX', 'false').lower() == 'true' or is_production:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan masuk terlebih dahulu untuk mengakses halaman ini.'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ── Security Headers (SECURITY FIX) ────────────────────────────────────
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Hugging Face Spaces embeds the app in an iframe on huggingface.co, so we must allow framing from Hugging Face domains via CSP frame-ancestors instead of blocking with SAMEORIGIN.
    # response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HSTS only in production with HTTPS
    if os.environ.get('FORCE_HTTPS', 'false').lower() == 'true':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Basic CSP (adjust based on your needs)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net app.sandbox.midtrans.com *.midtrans.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: fonts.gstatic.com; "
        "connect-src 'self' cdn.jsdelivr.net app.sandbox.midtrans.com api.sandbox.midtrans.com *.midtrans.com; "
        "frame-src 'self' app.sandbox.midtrans.com *.midtrans.com; "
        "frame-ancestors 'self' https://huggingface.co https://*.hf.space https://*.huggingface.co;"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response

# ── JSON Error Handlers (return JSON instead of HTML for API errors) ────
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors with JSON response."""
    if request.path.startswith('/api/'):
        max_mb = MAX_PREMIUM_UPLOAD_SIZE // (1024 * 1024)
        return jsonify({
            'success': False,
            'error': f'File terlalu besar. Maksimum {max_mb}MB.'
        }), 413
    return 'File too large', 413

@app.errorhandler(429)
def ratelimit_handler(error):
    """Handle rate limit exceeded with JSON response."""
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Terlalu banyak permintaan. Silakan coba lagi nanti.'
        }), 429
    return 'Too Many Requests', 429

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors with JSON response."""
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Terjadi kesalahan internal server. Silakan coba lagi.'
        }), 500
    return 'Internal Server Error', 500

# ── Custom Jinja Template Filters ───────────────────────────────────────
@app.template_filter('format_size')
def format_size(size_bytes):
    """Format bytes into readable strings (KB/MB)."""
    if size_bytes is None or size_bytes < 0:
        return '-'
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

# ── Anonymous Session Middleware ────────────────────────────────────────
@app.before_request
def ensure_anonymous_cookie():
    """Assigns a unique session cookie to tracking anonymous users."""
    if 'pdf_anon_session' not in request.cookies:
        # We will set a cookie in the response after this request
        # Store a temp session token on request object so it can be accessed
        request.new_anon_session = str(uuid.uuid4())
    else:
        request.new_anon_session = None

@app.after_request
def set_anonymous_cookie(response):
    """Set the generated anonymous cookie in the response if necessary."""
    if hasattr(request, 'new_anon_session') and request.new_anon_session:
        # SECURITY FIX: Add secure and samesite flags
        is_prod = os.environ.get('FLASK_ENV', 'production') == 'production' or 'SPACE_ID' in os.environ
        response.set_cookie(
            'pdf_anon_session', 
            request.new_anon_session, 
            max_age=365 * 24 * 60 * 60,
            httponly=True,
            secure=is_prod,  # Must be True if samesite='None'
            samesite='None' if is_prod else 'Lax'
        )
    return response

# ── Helper: Get current quotas and limits ──────────────────────────────
def get_user_quota_info():
    """Retrieve limits and remaining quotas for the current client."""
    anon_limit = int(SystemSetting.get_val('anonymous_limit', '1'))
    free_limit = int(SystemSetting.get_val('logged_in_free_limit', '2'))
    price = int(SystemSetting.get_val('premium_monthly_price', '20000'))
    
    # 1. Premium users: no limit
    if current_user.is_authenticated and current_user.is_premium:
        return {
            'tier': 'Premium',
            'limit': 999999,
            'used': 0,
            'remaining': 999999,
            'anon_limit': anon_limit,
            'free_limit': free_limit,
            'premium_monthly_price': price
        }
    
    # 2. Registered Free users: check DB logs
    if current_user.is_authenticated:
        used = UploadLog.query.filter_by(user_id=current_user.id).count()
        return {
            'tier': 'Registered (Free)',
            'limit': free_limit,
            'used': used,
            'remaining': max(0, free_limit - used),
            'anon_limit': anon_limit,
            'free_limit': free_limit,
            'premium_monthly_price': price
        }
    
    # 3. Anonymous users: check IP and Cookie logs
    ip_addr = request.remote_addr
    session_token = request.cookies.get('pdf_anon_session')
    
    # Filter logs from anonymous users matching IP OR session cookie
    filters = []
    if ip_addr:
        filters.append(UploadLog.ip_address == ip_addr)
    if session_token:
        filters.append(UploadLog.session_token == session_token)
        
    if filters:
        # Check logs created within last 24 hours
        time_limit = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        used = UploadLog.query.filter(
            UploadLog.user_id.is_(None),
            db.or_(*filters),
            UploadLog.created_at >= time_limit
        ).count()
    else:
        used = 0
        
    return {
        'tier': 'Anonymous',
        'limit': anon_limit,
        'used': used,
        'remaining': max(0, anon_limit - used),
        'anon_limit': anon_limit,
        'free_limit': free_limit,
        'premium_monthly_price': price
    }

@app.context_processor
def inject_global_quota_vars():
    """Inject quota limits and pricing variables into all Jinja templates automatically."""
    quota = get_user_quota_info()
    return {
        'anon_limit': quota['anon_limit'],
        'anon_remaining': quota['remaining'] if quota['tier'] == 'Anonymous' else quota['anon_limit'],
        'free_limit': quota['free_limit'],
        'premium_monthly_price': quota['premium_monthly_price'],
        'midtrans_client_key': SystemSetting.get_val('midtrans_client_key', 'SB-Mid-client-YOUR_SANDBOX_CLIENT_KEY'),
        'now': datetime.now(timezone.utc)
    }

# ── Primary Navigation Routes ───────────────────────────────────────────
@app.route('/')
def index():
    quota = get_user_quota_info()
    return render_template(
        'index.html',
        anon_limit=quota['anon_limit'],
        anon_remaining=quota['remaining'] if quota['tier'] == 'Anonymous' else quota['anon_limit'],
        free_limit=quota['free_limit'],
        premium_monthly_price=quota['premium_monthly_price']
    )

@app.route('/subscription')
def subscription():
    quota = get_user_quota_info()
    price = quota['premium_monthly_price']
    # Format monthly price as dot-separated string (e.g. 20.000)
    price_formatted = f"{price:,}".replace(",", ".")
    
    # Check if returning from a successful Midtrans transaction via redirect
    order_id = request.args.get('order_id')
    status_code = request.args.get('status_code')
    
    if order_id and status_code in ['200', '201'] and current_user.is_authenticated:
        # Check if the transaction was indeed successful/settled
        import midtransclient
        try:
            server_key = SystemSetting.get_val('midtrans_server_key')
            client_key = SystemSetting.get_val('midtrans_client_key')
            
            # Verify the order belongs to current user
            parts = order_id.split('-')
            if len(parts) >= 2 and parts[0] == 'SUB' and int(parts[1]) == current_user.id:
                snap = midtransclient.Snap(
                    is_production=False,
                    server_key=server_key,
                    client_key=client_key
                )
                status_response = snap.transactions.status(order_id)
                db_transaction_status = status_response.get('transaction_status')
                db_fraud_status = status_response.get('fraud_status', 'accept')
                
                is_settled = False
                if db_transaction_status == 'capture' and db_fraud_status == 'accept':
                    is_settled = True
                elif db_transaction_status == 'settlement':
                    is_settled = True
                
                if is_settled:
                    user = User.query.get(current_user.id)
                    user.is_premium = True
                    user.premium_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
                    db.session.commit()
                    flash('Pembayaran berhasil diverifikasi!', 'success')
                    # Refresh quota info
                    quota = get_user_quota_info()
                else:
                    flash(f'Transaksi belum terverifikasi (status: {db_transaction_status}). Silakan coba beberapa saat lagi.', 'warning')
        except Exception as e:
            # Silence error but flash a message
            import logging
            logging.error(f"Callback verification failed: {e}")
            flash('Gagal memverifikasi status pembayaran dengan Midtrans. Mohon segarkan halaman ini.', 'error')
            
    return render_template(
        'subscription.html',
        premium_monthly_price=price,
        price_formatted=price_formatted,
        free_limit=quota['free_limit']
    )

# ── Authentication Routes ───────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit(os.environ.get('RATELIMIT_LOGIN', '5 per minute'))
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Selamat datang kembali!', 'success')
            
            # Support post-login redirect
            redirect_to = request.args.get('redirect')
            if redirect_to == 'subscription':
                return redirect(url_for('subscription'))
            return redirect(url_for('index'))
        else:
            flash('Username atau password salah.', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit(os.environ.get('RATELIMIT_REGISTER', '3 per hour'))
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation checks
        if password != confirm_password:
            flash('Konfirmasi password tidak cocok.', 'error')
            return render_template('register.html')
        
        # SECURITY FIX: Password strength validation
        import re
        if len(password) < 8:
            flash('Password minimal 8 karakter.', 'error')
            return render_template('register.html')
        if not re.search(r'[A-Z]', password):
            flash('Password harus mengandung minimal 1 huruf besar.', 'error')
            return render_template('register.html')
        if not re.search(r'[a-z]', password):
            flash('Password harus mengandung minimal 1 huruf kecil.', 'error')
            return render_template('register.html')
        if not re.search(r'[0-9]', password):
            flash('Password harus mengandung minimal 1 angka.', 'error')
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'error')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar.', 'error')
            return render_template('register.html')
            
        # Create user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # Check if first user, make admin
        if User.query.count() == 0:
            new_user.is_admin = True
            
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Akun berhasil dibuat! Anda mendapatkan kuota gratis 2x.', 'success')
        
        redirect_to = request.args.get('redirect')
        if redirect_to == 'subscription':
            return redirect(url_for('subscription'))
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda berhasil keluar.', 'success')
    return redirect(url_for('index'))

# ── API: PDF Compression Handler ────────────────────────────────────────
@app.route('/api/compress', methods=['POST'])
@limiter.limit(os.environ.get('RATELIMIT_COMPRESS', '10 per minute'))
@csrf.exempt  # API endpoint - CSRF handled via other means if needed
def api_compress():
    """Handles upload validation, quota checking, and PDF compression."""
    # 1. Validate file presence
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'error': 'Tidak ada file PDF yang dikirim.'}), 400
        
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nama file tidak boleh kosong.'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Format berkas tidak didukung. Harus file PDF.'}), 400
    
    # SECURITY FIX: Validate file size (premium users get higher limit)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    is_premium = current_user.is_authenticated and current_user.is_premium
    effective_max = MAX_PREMIUM_UPLOAD_SIZE if is_premium else MAX_UPLOAD_SIZE
    
    if file_size > effective_max:
        max_mb = effective_max // (1024 * 1024)
        if not is_premium:
            return jsonify({
                'success': False, 
                'error': f'File terlalu besar. Maksimal {max_mb} MB untuk akun gratis. Upgrade ke Premium untuk upload hingga {MAX_PREMIUM_UPLOAD_SIZE // (1024 * 1024)} MB.'
            }), 400
        else:
            return jsonify({
                'success': False, 
                'error': f'File terlalu besar. Maksimal {max_mb} MB.'
            }), 400
    
    if file_size == 0:
        return jsonify({'success': False, 'error': 'File kosong atau corrupt.'}), 400

    # 2. Check Quotas/Limits before starting engine
    quota = get_user_quota_info()
    if quota['remaining'] <= 0:
        if quota['tier'] == 'Anonymous':
            return jsonify({
                'success': False, 
                'error': f"Batas kuota anonim terlampaui ({quota['limit']}/{quota['limit']} upload terpakai). Silakan mendaftar secara GRATIS untuk kuota tambahan!"
            }), 403
        else:
            return jsonify({
                'success': False, 
                'error': f"Batas kuota gratis akun Anda terlampaui ({quota['limit']}/{quota['limit']} upload terpakai)"
            }), 403

    # 3. Read settings and inputs
    preset = request.form.get('preset', 'medium')
    custom_dpi = request.form.get('dpi')
    custom_quality = request.form.get('quality')
    
    # Parse overrides
    try:
        custom_dpi = int(custom_dpi) if custom_dpi else None
        custom_quality = int(custom_quality) if custom_quality else None
    except ValueError:
        return jsonify({'success': False, 'error': 'DPI atau kualitas harus berupa angka valid.'}), 400

    # Generate unique filename for temporary uploads and outputs
    file_id = str(uuid.uuid4())
    temp_in_path = UPLOAD_FOLDER / f"upload_{file_id}.pdf"
    
    # Save input file
    file.save(str(temp_in_path))
    original_size = temp_in_path.stat().st_size
    
    # Instantiate compression engine
    engine = CompressionEngine(output_dir=OUTPUT_FOLDER, overwrite=True, verbose=True)
    
    # SECURITY FIX: Sanitize original filename before storing
    import re as re_module
    safe_filename = os.path.basename(file.filename)
    safe_filename = re_module.sub(r'[^\w\s.\-]', '_', safe_filename)[:255]
    
    # Track details for DB logging
    ip_addr = request.remote_addr
    session_token = request.cookies.get('pdf_anon_session')
    user_id = current_user.id if current_user.is_authenticated else None
    
    start_time = datetime.now(timezone.utc).replace(tzinfo=None)
    
    try:
        # Run compressor
        result = engine.compress(
            input_path=temp_in_path,
            preset_name=preset,
            custom_dpi=custom_dpi,
            custom_quality=custom_quality,
            output_name=f"compressed_{file_id}"
        )
        
        end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_seconds = (end_time - start_time).total_seconds()
        
        # Remove temporary uploaded file
        if temp_in_path.exists():
            temp_in_path.unlink()
            
        if result.success and result.output_path and result.output_path.exists():
            compressed_size = result.output_path.stat().st_size
            
            # Record log inside database
            stages_str = ",".join(result.stages_used) if result.stages_used else ""
            log = UploadLog(
                user_id=user_id,
                ip_address=ip_addr,
                session_token=session_token,
                original_name=safe_filename,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_time=elapsed_seconds,
                preset=preset,
                status='success',
                stages_used=stages_str
            )
            db.session.add(log)
            db.session.commit()
            
            # Recalculate remaining quota after success
            updated_quota = get_user_quota_info()
            
            return jsonify({
                'success': True,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'reduction_percent': result.reduction_percent,
                'elapsed_seconds': elapsed_seconds,
                'download_url': url_for('download_file', filename=result.output_path.name),
                'quota_used': updated_quota['used'],
                'quota_limit': updated_quota['limit'],
                'quota_tier': updated_quota['tier']
            })
        else:
            # Compression completed but failure
            err_msg = result.error_message or "Unknown core compression engine failure."
            log = UploadLog(
                user_id=user_id,
                ip_address=ip_addr,
                session_token=session_token,
                original_name=safe_filename,
                original_size=original_size,
                status='failed',
                error_message=err_msg
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({'success': False, 'error': err_msg}), 500
            
    except Exception as e:
        if temp_in_path.exists():
            temp_in_path.unlink()
            
        # SECURITY FIX: Log detailed error but send generic message to client
        err_msg = str(e)
        import logging
        logging.error(f"Compression failed for user {user_id}: {err_msg}", exc_info=True)
        
        log = UploadLog(
            user_id=user_id,
            ip_address=ip_addr,
            session_token=session_token,
            original_name=safe_filename,
            original_size=original_size,
            status='failed',
            error_message=err_msg[:500]  # Truncate for DB
        )
        db.session.add(log)
        db.session.commit()
        
        # Send generic error to client (don't expose internal details)
        return jsonify({
            'success': False, 
            'error': 'Terjadi kesalahan saat memproses file. Silakan coba lagi atau hubungi support jika masalah berlanjut.'
        }), 500

# ── API: PDF Downloader Router ──────────────────────────────────────────
@app.route('/download/<path:filename>')
def download_file(filename):
    """Serves the compressed PDF files to the client safely."""
    # SECURITY FIX: Enhanced path traversal protection
    from flask import abort
    
    # Remove any path components (prevent ../../../etc/passwd)
    filename = os.path.basename(filename)
    
    # Validate filename (only allow alphanumeric, dash, underscore, dot)
    import re
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
        abort(400, 'Invalid filename')
    
    # Construct full path
    file_path = app.config['OUTPUT_FOLDER'] / filename
    
    # Verify file exists and is a file (not directory)
    if not file_path.exists() or not file_path.is_file():
        abort(404, 'File not found')
    
    # Verify file is within output folder (prevent symlink attacks)
    try:
        file_path.resolve().relative_to(app.config['OUTPUT_FOLDER'].resolve())
    except ValueError:
        abort(403, 'Access denied')
    
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# ── API: Premium Mock subscription payment ──────────────────────────────
@app.route('/api/subscribe/mock', methods=['POST'])
@login_required
@csrf.exempt  # API endpoint with user authentication
def api_subscribe_mock():
    """Asynchronously upgrades the logged-in user to Premium."""
    try:
        user = User.query.get(current_user.id)
        user.is_premium = True
        # Subscription valid for 30 days
        user.premium_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        
        # Record Transaction
        price = int(SystemSetting.get_val('premium_monthly_price', '20000'))
        order_id = f"MOCK-{user.id}-{int(datetime.now(timezone.utc).timestamp())}"
        txn = Transaction(
            user_id=user.id,
            order_id=order_id,
            amount=price,
            status='settlement',
            payment_type='mock',
            created_at=datetime.utcnow()
        )
        db.session.add(txn)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Akun Anda berhasil ditingkatkan ke Premium'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ── API: Midtrans Sandbox Payment Gateway ────────────────────────────────
@app.route('/api/subscribe/midtrans/token', methods=['POST'])
@login_required
def api_subscribe_midtrans_token():
    """Contact Midtrans Snap API and return checkout token for Sandbox payment."""
    import midtransclient
    try:
        server_key = SystemSetting.get_val('midtrans_server_key')
        client_key = SystemSetting.get_val('midtrans_client_key')
        
        # Guard clause for default keys
        if 'YOUR_SANDBOX' in server_key:
            return jsonify({
                'success': False, 
                'error': 'Kunci Midtrans Server Key belum diatur di Admin Panel > Pengaturan Limit.'
            }), 400

        # Initialize Snap API client
        snap = midtransclient.Snap(
            is_production=False,
            server_key=server_key,
            client_key=client_key
        )
        
        # Set Order parameters
        order_id = f"SUB-{current_user.id}-{int(datetime.now(timezone.utc).timestamp())}"
        price = int(SystemSetting.get_val('premium_monthly_price', '20000'))
        
        # Build dynamic callback URLs matching the current host/port of this application
        finish_url = request.host_url.rstrip('/') + url_for('subscription')
        
        param = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": price
            },
            "item_details": [{
                "id": "PREMIUM-PRO-1M",
                "price": price,
                "quantity": 1,
                "name": "Premium — 1 Bulan"
            }],
            "customer_details": {
                "first_name": current_user.username,
                "email": current_user.email
            },
            "callbacks": {
                "finish": finish_url,
                "unfinish": finish_url,
                "error": finish_url
            }
        }
        
        # Create Snap payment transaction
        transaction = snap.create_transaction(param)
        snap_token = transaction['token']
        redirect_url = transaction['redirect_url']
        
        return jsonify({
            'success': True, 
            'token': snap_token, 
            'redirect_url': redirect_url,
            'order_id': order_id,
            'client_key': client_key
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f"Gagal membuat token Midtrans: {str(e)}"}), 500

@app.route('/api/subscribe/midtrans/success', methods=['POST'])
@login_required
@csrf.exempt
def api_subscribe_midtrans_success():
    """Client-side success callback — verify with Midtrans before upgrading (SECURITY FIX)."""
    import midtransclient
    import hashlib
    try:
        data = request.get_json(silent=True) or {}
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'success': False, 'error': 'Order ID tidak ditemukan.'}), 400
        
        # SECURITY FIX: Verify transaction with Midtrans API server-side
        server_key = SystemSetting.get_val('midtrans_server_key')
        client_key = SystemSetting.get_val('midtrans_client_key')
        
        if not server_key or 'YOUR_SANDBOX' in server_key:
            return jsonify({'success': False, 'error': 'Midtrans belum dikonfigurasi.'}), 400
        
        # Verify the order belongs to current user
        parts = order_id.split('-')
        if len(parts) < 2 or parts[0] != 'SUB' or int(parts[1]) != current_user.id:
            return jsonify({'success': False, 'error': 'Order ID tidak valid untuk akun ini.'}), 403
        
        # Double-check transaction status with Midtrans API
        snap = midtransclient.Snap(
            is_production=False,
            server_key=server_key,
            client_key=client_key
        )
        status_response = snap.transactions.status(order_id)
        transaction_status = status_response.get('transaction_status')
        fraud_status = status_response.get('fraud_status', 'accept')
        
        is_settled = False
        if transaction_status == 'capture' and fraud_status == 'accept':
            is_settled = True
        elif transaction_status == 'settlement':
            is_settled = True
        
        if not is_settled:
            return jsonify({
                'success': False, 
                'error': f'Transaksi belum terverifikasi (status: {transaction_status}). Silakan tunggu notifikasi dari Midtrans.'
            }), 400
        
        # Verified! Upgrade user
        user = User.query.get(current_user.id)
        user.is_premium = True
        user.premium_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        
        # Record/Update Transaction
        txn = Transaction.query.filter_by(order_id=order_id).first()
        gross_amount = int(float(status_response.get('gross_amount', 20000)))
        payment_type = status_response.get('payment_type', 'midtrans')
        
        if not txn:
            txn = Transaction(
                user_id=user.id,
                order_id=order_id,
                amount=gross_amount,
                status='settlement',
                payment_type=payment_type,
                created_at=datetime.utcnow()
            )
            db.session.add(txn)
        else:
            txn.status = 'settlement'
            txn.payment_type = payment_type
            
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Pembayaran terverifikasi'})
    except Exception as e:
        import logging
        logging.error(f"Midtrans success verification failed: {e}")
        return jsonify({'success': False, 'error': 'Gagal memverifikasi pembayaran. Hubungi support.'}), 500

@app.route('/api/subscribe/midtrans/notification', methods=['POST'])
@csrf.exempt  # Webhook from Midtrans server
def api_subscribe_midtrans_notification():
    """Server-to-server webhook callback for Midtrans payment status notifications."""
    import midtransclient
    import hashlib
    import logging
    try:
        server_key = SystemSetting.get_val('midtrans_server_key')
        client_key = SystemSetting.get_val('midtrans_client_key')
        
        notification = request.get_json()
        if not notification:
            return jsonify({'success': False, 'error': 'Payload not found'}), 400
        
        order_id = notification.get('order_id', '')
        status_code = notification.get('status_code', '')
        gross_amount = notification.get('gross_amount', '')
        received_signature = notification.get('signature_key', '')
        
        # SECURITY FIX: Validate Midtrans signature
        expected_signature = hashlib.sha512(
            f"{order_id}{status_code}{gross_amount}{server_key}".encode()
        ).hexdigest()
        
        if received_signature != expected_signature:
            logging.warning(f"Midtrans Webhook: Invalid signature for order {order_id}")
            return jsonify({'success': False, 'error': 'Invalid signature'}), 403
        
        snap = midtransclient.Snap(
            is_production=False,
            server_key=server_key,
            client_key=client_key
        )
        
        # Double-check transaction status with Midtrans API
        status_response = snap.transactions.status(order_id)
        db_transaction_status = status_response.get('transaction_status')
        db_fraud_status = status_response.get('fraud_status', 'accept')
        
        # Validate order ID format
        parts = order_id.split('-')
        if len(parts) >= 2 and parts[0] == 'SUB':
            try:
                user_id = int(parts[1])
            except ValueError:
                logging.warning(f"Midtrans Webhook: Invalid order_id format: {order_id}")
                return jsonify({'success': False, 'error': 'Invalid order ID format'}), 400
            
            is_settled = False
            if db_transaction_status == 'capture' and db_fraud_status == 'accept':
                is_settled = True
            elif db_transaction_status == 'settlement':
                is_settled = True
                
            # Record or Update Transaction
            txn = Transaction.query.filter_by(order_id=order_id).first()
            gross_amount_val = int(float(gross_amount)) if gross_amount else 20000
            payment_type = status_response.get('payment_type', 'midtrans')
            
            if not txn:
                txn = Transaction(
                    user_id=user_id,
                    order_id=order_id,
                    amount=gross_amount_val,
                    status=db_transaction_status,
                    payment_type=payment_type,
                    created_at=datetime.utcnow()
                )
                db.session.add(txn)
            else:
                txn.status = db_transaction_status
                txn.payment_type = payment_type
                
            db.session.commit()
                
            if is_settled:
                user = User.query.get(user_id)
                if user:
                    user.is_premium = True
                    user.premium_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
                    db.session.commit()
                    logging.info(f"Midtrans Webhook: User '{user.username}' upgraded to Premium (Order: {order_id})")
                else:
                    logging.warning(f"Midtrans Webhook: User {user_id} not found for order {order_id}")
                    
        return jsonify({'success': True}), 200
    except Exception as e:
        import logging
        logging.error(f"Midtrans Webhook Error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Webhook processing error'}), 500

# ── Admin Panel Dashboard Routes ────────────────────────────────────────
def admin_required(f):
    """Decorator to enforce administrator credentials."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Akses ditolak. Halaman ini hanya untuk Administrator.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Metrics
    total_users = User.query.count()
    total_premium = User.query.filter_by(is_premium=True).count()
    total_uploads = UploadLog.query.count()
    
    # Calculate total space saved
    successful_logs = UploadLog.query.filter_by(status='success').all()
    total_saved_bytes = sum(max(0, log.original_size - log.compressed_size) for log in successful_logs if log.compressed_size)
    
    # Format total storage saved
    if total_saved_bytes < 1024 * 1024:
        total_saved_formatted = f"{total_saved_bytes / 1024:.1f} KB"
    else:
        total_saved_formatted = f"{total_saved_bytes / (1024 * 1024):.1f} MB"
        
    recent_logs = UploadLog.query.order_by(UploadLog.created_at.desc()).limit(5).all()
    
    # Analytics line chart: Daily uploads for last 7 days
    daily_labels = []
    daily_data = []
    
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc).date() - timedelta(days=i)
        day_str = day.strftime('%A') # e.g. Monday, Tuesday
        
        # Translate to Indonesian for user-friendly UI
        translations = {
            'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
            'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
        }
        day_name = translations.get(day_str, day_str)
        daily_labels.append(day_name)
        
        # Count uploads on that specific date
        start_of_day = datetime.combine(day, datetime.min.time())
        end_of_day = datetime.combine(day, datetime.max.time())
        count = UploadLog.query.filter(
            UploadLog.created_at >= start_of_day,
            UploadLog.created_at <= end_of_day
        ).count()
        daily_data.append(count)
        
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_premium=total_premium,
        total_uploads=total_uploads,
        total_saved_formatted=total_saved_formatted,
        recent_logs=recent_logs,
        daily_labels=daily_labels,
        daily_data=daily_data
    )

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    if per_page not in (10, 20, 50, 100):
        per_page = 10
    
    # Calculate global counts for stats
    total_users = User.query.count()
    premium_users = User.query.filter_by(is_premium=True).count()
    admin_users_count = User.query.filter_by(is_admin=True).count()
    
    pagination = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    quota = get_user_quota_info()
    
    return render_template(
        'admin/users.html', 
        users=users,
        pagination=pagination,
        total_users=total_users,
        premium_users=premium_users,
        admin_users_count=admin_users_count,
        free_limit=quota['free_limit']
    )

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    if per_page not in (10, 20, 50, 100):
        per_page = 10
    
    # Calculate global counts for stats
    total_count = UploadLog.query.count()
    success_count = UploadLog.query.filter_by(status='success').count()
    failed_count = UploadLog.query.filter_by(status='failed').count()
    
    pagination = UploadLog.query.order_by(UploadLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    return render_template(
        'admin/logs.html', 
        logs=logs, 
        pagination=pagination,
        total_count=total_count,
        success_count=success_count,
        failed_count=failed_count
    )

@app.route('/admin/transactions')
@login_required
@admin_required
def admin_transactions():
    # Fetch all for historical stats and daily trend calculations
    all_transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    
    # Calculate stats
    now = datetime.utcnow()
    current_year = now.year
    current_month = now.month
    
    # Successful transactions (all time)
    successful_txns = [t for t in all_transactions if t.status in ('settlement', 'success', 'capture')]
    total_subscriptions = len(successful_txns)
    
    # Revenue this month
    monthly_txns = [t for t in successful_txns if t.created_at.year == current_year and t.created_at.month == current_month]
    monthly_revenue = sum(t.amount for t in monthly_txns)
    
    # Revenue this year
    yearly_txns = [t for t in successful_txns if t.created_at.year == current_year]
    yearly_revenue = sum(t.amount for t in yearly_txns)
    
    # Monthly revenue trend analytics for last 12 months
    revenue_labels = []
    revenue_data = []
    
    month_names = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
        7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    for i in range(11, -1, -1):
        target_year = now.year
        target_month = now.month - i
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        month_label = f"{month_names[target_month]} {target_year}"
        revenue_labels.append(month_label)
        
        # Calculate total revenue for this year and month
        month_revenue = sum(t.amount for t in successful_txns if t.created_at.year == target_year and t.created_at.month == target_month)
        revenue_data.append(month_revenue)
        
    # Paginate table items
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    if per_page not in (10, 20, 50, 100):
        per_page = 10
        
    pagination = Transaction.query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    
    return render_template(
        'admin/transactions.html',
        transactions=transactions,
        pagination=pagination,
        monthly_revenue=monthly_revenue,
        total_subscriptions=total_subscriptions,
        yearly_revenue=yearly_revenue,
        revenue_labels=revenue_labels,
        revenue_data=revenue_data
    )

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    if request.method == 'POST':
        anon_limit = request.form.get('anonymous_limit')
        free_limit = request.form.get('logged_in_free_limit')
        price = request.form.get('premium_monthly_price')
        midtrans_server_key = request.form.get('midtrans_server_key')
        midtrans_client_key = request.form.get('midtrans_client_key')
        
        # SECURITY FIX: Validate input ranges
        try:
            anon_limit_int = int(anon_limit)
            free_limit_int = int(free_limit)
            price_int = int(price)
            
            # Validate ranges
            if not (0 <= anon_limit_int <= 1000):
                flash('Error: Batas anonim harus antara 0-1000.', 'error')
                return redirect(url_for('admin_settings'))
            
            if not (0 <= free_limit_int <= 1000):
                flash('Error: Batas free user harus antara 0-1000.', 'error')
                return redirect(url_for('admin_settings'))
            
            if not (0 <= price_int <= 10000000):
                flash('Error: Harga harus antara 0-10.000.000.', 'error')
                return redirect(url_for('admin_settings'))
            
            # Sanitize keys (remove dangerous characters)
            import re as re_module
            server_key = re_module.sub(r'[^a-zA-Z0-9_\-]', '', midtrans_server_key.strip())[:255]
            client_key = re_module.sub(r'[^a-zA-Z0-9_\-]', '', midtrans_client_key.strip())[:255]
            
            SystemSetting.set_val('anonymous_limit', anon_limit_int, 'Batas upload harian anonim')
            SystemSetting.set_val('logged_in_free_limit', free_limit_int, 'Batas upload total/harian user terdaftar free')
            SystemSetting.set_val('premium_monthly_price', price_int, 'Harga langganan bulanan premium')
            SystemSetting.set_val('midtrans_server_key', server_key, 'Midtrans Sandbox Server Key')
            SystemSetting.set_val('midtrans_client_key', client_key, 'Midtrans Sandbox Client Key')
            flash('Pengaturan sistem berhasil disimpan.', 'success')
        except ValueError:
            flash('Error: Batas input harus berupa bilangan bulat.', 'error')
            
        return redirect(url_for('admin_settings'))
        
    anon_limit = int(SystemSetting.get_val('anonymous_limit', '1'))
    free_limit = int(SystemSetting.get_val('logged_in_free_limit', '2'))
    price = int(SystemSetting.get_val('premium_monthly_price', '20000'))
    server_key = SystemSetting.get_val('midtrans_server_key', 'SB-Mid-server-YOUR_SANDBOX_SERVER_KEY')
    client_key = SystemSetting.get_val('midtrans_client_key', 'SB-Mid-client-YOUR_SANDBOX_CLIENT_KEY')
    
    return render_template(
        'admin/settings.html',
        anonymous_limit=anon_limit,
        logged_in_free_limit=free_limit,
        premium_monthly_price=price,
        midtrans_server_key=server_key,
        midtrans_client_key=client_key
    )

# ── Admin Panel Toggles API ─────────────────────────────────────────────
@app.route('/admin/toggle-premium/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_premium(user_id):
    user = User.query.get_or_404(user_id)
    user.is_premium = not user.is_premium
    if user.is_premium:
        user.premium_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    else:
        user.premium_expires_at = None
    db.session.commit()
    
    status_str = "berhasil diaktifkan" if user.is_premium else "berhasil dinonaktifkan"
    return jsonify({
        'success': True, 
        'is_premium': user.is_premium, 
        'message': f"Status Premium untuk pengguna {user.username} {status_str}."
    })

@app.route('/admin/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    # Prevent self demotion
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Anda tidak bisa mencabut hak administrasi Anda sendiri!'}), 400
        
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status_str = "berhasil diaktifkan" if user.is_admin else "berhasil dinonaktifkan"
    return jsonify({
        'success': True, 
        'is_admin': user.is_admin, 
        'message': f"Hak akses Administrator untuk pengguna {user.username} {status_str}."
    })

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    # Prevent self deletion
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Anda tidak bisa menghapus akun Anda sendiri saat sedang masuk!'}), 400
        
    user = User.query.get_or_404(user_id)
    
    # Capture username before deleting
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f"Akun pengguna '{username}' beserta seluruh log unggahan terkait telah berhasil dihapus dari sistem"})

# ── System Startup: Initializations ─────────────────────────────────────
def initialize_system():
    """Initializes tables, default configurations, and creates default admin."""
    with app.app_context():
        db.create_all()
        
        # Populate Default system settings
        if not SystemSetting.query.filter_by(key='anonymous_limit').first():
            SystemSetting.set_val('anonymous_limit', '1', 'Batas upload harian anonim')
        if not SystemSetting.query.filter_by(key='logged_in_free_limit').first():
            SystemSetting.set_val('logged_in_free_limit', '2', 'Batas upload total/harian user terdaftar free')
        if not SystemSetting.query.filter_by(key='premium_monthly_price').first():
            SystemSetting.set_val('premium_monthly_price', '20000', 'Harga langganan bulanan premium')
        # Populate Default system settings
        # Synchronize from environment variables if set in .env
        env_server_key = os.environ.get('MIDTRANS_SERVER_KEY')
        env_client_key = os.environ.get('MIDTRANS_CLIENT_KEY')
        
        db_server_setting = SystemSetting.query.filter_by(key='midtrans_server_key').first()
        if not db_server_setting:
            SystemSetting.set_val('midtrans_server_key', env_server_key or 'SB-Mid-server-YOUR_SANDBOX_SERVER_KEY', 'Midtrans Sandbox Server Key')
        elif env_server_key and ('YOUR_SANDBOX' in db_server_setting.value or db_server_setting.value != env_server_key):
            SystemSetting.set_val('midtrans_server_key', env_server_key, 'Midtrans Sandbox Server Key')
            
        db_client_setting = SystemSetting.query.filter_by(key='midtrans_client_key').first()
        if not db_client_setting:
            SystemSetting.set_val('midtrans_client_key', env_client_key or 'SB-Mid-client-YOUR_SANDBOX_CLIENT_KEY', 'Midtrans Sandbox Client Key')
        elif env_client_key and ('YOUR_SANDBOX' in db_client_setting.value or db_client_setting.value != env_client_key):
            SystemSetting.set_val('midtrans_client_key', env_client_key, 'Midtrans Sandbox Client Key')
            
        # Create default Admin if database is empty
        if User.query.count() == 0:
            # SECURITY FIX: Use environment variable for admin password
            admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')
            
            if not admin_password:
                # Generate random password if not set
                import secrets
                import string
                admin_password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(20))
                if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
                    print("\n" + "="*70)
                    print("⚠️  CRITICAL: ADMIN_INITIAL_PASSWORD not set in environment!")
                    print("   A random password has been generated:")
                    print(f"   Username: admin")
                    print(f"   Password: {admin_password}")
                    print("   SAVE THIS PASSWORD NOW! It will not be shown again.")
                    print("   For production, set ADMIN_INITIAL_PASSWORD in .env file")
                    print("="*70 + "\n")
            else:
                if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
                    print("System Initializer: Creating admin account with password from environment")
            
            admin_user = User(username='admin', email='admin@pdfcomp.com', is_admin=True, is_premium=True)
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
                print("System Initializer: Default admin created! (Username: admin)")

# Run Initializer
initialize_system()

# ── File Cleanup Scheduler (SECURITY FIX) ──────────────────────────────
def cleanup_old_files():
    """Delete uploaded and output files older than configured hours."""
    import time
    import logging
    
    cleanup_hours = int(os.environ.get('FILE_CLEANUP_HOURS', '24'))
    max_age_seconds = cleanup_hours * 3600
    now = time.time()
    
    cleaned_count = 0
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        try:
            for file_path in folder.glob('*'):
                if file_path.is_file():
                    age = now - file_path.stat().st_mtime
                    if age > max_age_seconds:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                            logging.info(f"Cleaned up old file: {file_path.name}")
                        except Exception as e:
                            logging.warning(f"Failed to delete {file_path.name}: {e}")
        except Exception as e:
            logging.error(f"Cleanup error in {folder}: {e}")
    
    if cleaned_count > 0:
        logging.info(f"File cleanup completed: {cleaned_count} files removed")

# Schedule cleanup to run every hour
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_old_files, 'interval', hours=1)
    scheduler.start()
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("File cleanup scheduler started (runs every hour)")
except ImportError:
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("Warning: APScheduler not installed. File cleanup disabled.")
        print("Install with: pip install apscheduler")

# ── Main Entry Point ────────────────────────────────────────────────────
if __name__ == '__main__':
    # SECURITY FIX: Only use debug mode in development
    is_development = os.environ.get('FLASK_ENV', 'production') == 'development'
    port = int(os.environ.get('PORT', 7860 if not is_development else 5000))
    
    if is_development:
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            print(f"🚀 Starting PDF Compressor in DEVELOPMENT mode (Debug: Active) on port {port}")
        app.run(host='127.0.0.1', port=port, debug=True)
    else:
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            print(f"🚀 Starting PDF Compressor in PRODUCTION mode on port {port}")
            print("⚠️  WARNING: Using Flask development server in production!")
            print("   For production, use a WSGI server like Gunicorn:")
            print(f"   gunicorn -w 4 -b 0.0.0.0:{port} --timeout 600 app:app")
        app.run(host='0.0.0.0', port=port, debug=False)
