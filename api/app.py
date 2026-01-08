"""
Hybrid API - Job Queue + Manual Student Review
Combines automated processing with human quality control
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from dotenv import load_dotenv
import secrets

load_dotenv()


import subprocess
import threading
import json
from pathlib import Path
import logging

# Add logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# ============================================================================
# REAL PROCESSING - Background Worker Management
# ============================================================================

# In-memory status tracking (for production, use Redis)
processing_status = {}

def run_worker_background(video_id, youtube_url, preset, student_id):
    """Run worker script in background thread"""
    try:
        processing_status[video_id] = {
            'status': 'processing',
            'progress': 0,
            'logs': ['🚀 Starting processing...'],
            'results': None,
            'error': None
        }
        
        # Path to worker script
        worker_script = Path(__file__).parent.parent / 'worker' / 'process_video.py'
        
        cmd = [
            'python3',
            str(worker_script),
            video_id,
            youtube_url,
            preset
        ]
        
        logger.info(f"🎬 Running worker for {video_id}: {' '.join(cmd)}")
        
        # Update status
        processing_status[video_id]['logs'].append(f'📥 Downloading from YouTube...')
        
        # Run worker script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            cwd=Path(__file__).parent.parent / 'worker'
        )
        
        if result.returncode == 0:
            # Parse results from stdout
            try:
                results = json.loads(result.stdout)
                processing_status[video_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'logs': processing_status[video_id]['logs'] + ['✅ Processing complete!'],
                    'results': results,
                    'error': None
                }
                logger.info(f"✅ Processing completed: {video_id}")
                
                # Submit results to database
                submit_processing_results(video_id, results)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse worker output: {result.stdout}")
                processing_status[video_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'logs': processing_status[video_id]['logs'],
                    'results': None,
                    'error': f'Invalid output from worker: {str(e)}'
                }
        else:
            error_msg = result.stderr or result.stdout or 'Unknown error'
            processing_status[video_id] = {
                'status': 'failed',
                'progress': 0,
                'logs': processing_status[video_id]['logs'],
                'results': None,
                'error': error_msg
            }
            logger.error(f"❌ Processing failed: {error_msg}")
            
    except subprocess.TimeoutExpired:
        processing_status[video_id] = {
            'status': 'failed',
            'progress': 0,
            'logs': processing_status[video_id]['logs'],
            'results': None,
            'error': 'Processing timeout after 1 hour'
        }
        logger.error(f"⏱️ Timeout: {video_id}")
        
    except Exception as e:
        processing_status[video_id] = {
            'status': 'failed',
            'progress': 0,
            'logs': processing_status[video_id]['logs'],
            'results': None,
            'error': str(e)
        }
        logger.error(f"❌ Error processing {video_id}: {e}", exc_info=True)

def submit_processing_results(video_id, results):
    """Submit results to database after processing"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Find job
        cur.execute("""
            SELECT job_id FROM processing_jobs
            WHERE video_id = %s
            AND status = 'processing'
        """, (video_id,))
        
        job = cur.fetchone()
        if not job:
            logger.warning(f"Job not found for {video_id}")
            return
        
        job_id = job['job_id']
        
        # Update job to reviewing
        cur.execute("""
            UPDATE processing_jobs
            SET status = 'reviewing',
                completed_at = NOW()
            WHERE job_id = %s
        """, (job_id,))
        
        # Insert results
        cur.execute("""
            INSERT INTO processing_results
            (job_id, video_id, chunks_created, chunks_passed_sync,
             avg_sync_score, min_sync_score, max_sync_score,
             avg_face_presence, min_face_presence, max_face_presence,
             total_duration_seconds, usable_duration_seconds,
             storage_path, file_size_mb, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            job_id, video_id,
            results.get('chunks_created', 0),
            results.get('chunks_passed_sync', 0),
            results.get('avg_sync_score', 0.0),
            results.get('min_sync_score', 0.0),
            results.get('max_sync_score', 0.0),
            results.get('avg_face_presence', 0.0),
            results.get('min_face_presence', 0.0),
            results.get('max_face_presence', 0.0),
            results.get('total_duration_seconds', 0.0),
            results.get('usable_duration_seconds', 0.0),
            results.get('storage_path', ''),
            results.get('file_size_mb', 0.0),
            results.get('metadata', {})
        ))
        
        conn.commit()
        logger.info(f"✅ Results saved to database: {video_id}")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
    finally:
        cur.close()
        conn.close()

def get_db():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ============================================================================
# AUTHENTICATION
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new student"""
    data = request.json
    student_id = data.get('student_id')
    name = data.get('name')
    email = data.get('email')
    
    if not all([student_id, name]):
        return jsonify({'error': 'student_id and name required'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO workers (worker_id, student_name, email, active)
            VALUES (%s, %s, %s, true)
            RETURNING worker_id, student_name
        """, (student_id, name, email))
        
        result = cur.fetchone()
        conn.commit()
        
        if result:
            session['student_id'] = student_id
            session['student_name'] = name
            return jsonify({
                'message': 'Registered successfully',
                'student': {'id': result['worker_id'], 'name': result['student_name']}
            })
            
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Student ID already exists'}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Student login"""
    data = request.json
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({'error': 'student_id required'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT worker_id, student_name, email, jobs_completed, jobs_rejected
        FROM workers
        WHERE worker_id = %s
    """, (student_id,))
    
    student = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if student:
        session['student_id'] = student['worker_id']
        session['student_name'] = student['student_name']
        return jsonify({
            'message': 'Logged in',
            'student': student
        })
    else:
        return jsonify({'error': 'Student not found. Please register first.'}), 404

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout"""
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current logged in user"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    return jsonify({
        'student_id': session['student_id'],
        'student_name': session.get('student_name')
    })

# ============================================================================
# VIDEO QUEUE & CLAIMING
# ============================================================================

@app.route('/api/videos/next', methods=['GET'])
def get_next_video():
    """Get next available video with preview"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Get next video from priority queue
        cur.execute("""
            SELECT 
                video_id,
                youtube_url,
                title,
                duration_seconds,
                speaker_id,
                speaker_name,
                domain,
                times_rejected,
                times_processed,
                queued_at
            FROM pending_videos_queue
            LIMIT 1
        """)
        
        video = cur.fetchone()
        
        if not video:
            return jsonify({'message': 'No videos available in queue'}), 404
        
        return jsonify({
            'video': video,
            'estimated_time_minutes': 15 + (video['duration_seconds'] or 0) // 60,
            'presets': [
                {'value': 'strict', 'label': 'Strict', 'description': 'Highest quality (sync>8.0, face>95%)'},
                {'value': 'balanced', 'label': 'Balanced', 'description': 'Good quality (sync>6.5, face>90%) - Default'},
                {'value': 'lenient', 'label': 'Lenient', 'description': 'Lower threshold (sync>5.0, face>80%)'}
            ]
        })
        
    finally:
        cur.close()
        conn.close()

@app.route('/api/videos/<video_id>/claim', methods=['POST'])
def claim_video(video_id):
    """Claim video for processing"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = session['student_id']
    preset = request.json.get('preset', 'balanced')
    
    if preset not in ['strict', 'balanced', 'lenient']:
        return jsonify({'error': 'Invalid preset'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Claim job atomically
        cur.execute("""
            UPDATE processing_jobs
            SET status = 'claimed',
                preset = %s::processing_preset,
                assigned_to = %s,
                assigned_at = NOW()
            WHERE video_id = %s
            AND status = 'pending'
            RETURNING job_id, video_id
        """, (preset, student_id, video_id))
        
        result = cur.fetchone()
        
        if not result:
            conn.rollback()
            return jsonify({'error': 'Video already claimed or not available'}), 409
        
        # Update worker's current video
        cur.execute("""
            UPDATE workers
            SET current_video_id = %s,
                last_active = NOW()
            WHERE worker_id = %s
        """, (video_id, student_id))
        
        conn.commit()
        
        return jsonify({
            'message': 'Video claimed successfully',
            'job_id': result['job_id'],
            'video_id': result['video_id'],
            'preset': preset
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/videos/<video_id>/processing', methods=['POST'])
def start_processing(video_id):
    """Mark video as processing started"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = session['student_id']
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE processing_jobs
            SET status = 'processing',
                started_at = NOW()
            WHERE video_id = %s
            AND assigned_to = %s
            AND status = 'claimed'
            RETURNING job_id
        """, (video_id, student_id))
        
        result = cur.fetchone()
        conn.commit()
        
        if result:
            return jsonify({'message': 'Processing started'})
        else:
            return jsonify({'error': 'Job not found or already processing'}), 404
            
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============================================================================
# SUBMIT RESULTS
# ============================================================================

@app.route('/api/videos/<video_id>/results', methods=['POST'])
def submit_results(video_id):
    """Submit processing results (before review)"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = session['student_id']
    data = request.json
    
    required = ['chunks_created', 'chunks_passed_sync', 'avg_sync_score', 
                'avg_face_presence', 'total_duration_seconds', 'storage_path']
    
    if not all(field in data for field in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Find job
        cur.execute("""
            SELECT job_id FROM processing_jobs
            WHERE video_id = %s
            AND assigned_to = %s
            AND status = 'processing'
        """, (video_id, student_id))
        
        job = cur.fetchone()
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        job_id = job['job_id']
        
        # Update job to reviewing
        cur.execute("""
            UPDATE processing_jobs
            SET status = 'reviewing',
                completed_at = NOW()
            WHERE job_id = %s
        """, (job_id,))
        
        # Insert processing results
        cur.execute("""
            INSERT INTO processing_results
            (job_id, video_id, chunks_created, chunks_passed_sync,
             avg_sync_score, min_sync_score, max_sync_score,
             avg_face_presence, min_face_presence, max_face_presence,
             total_duration_seconds, usable_duration_seconds,
             storage_path, file_size_mb, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING result_id
        """, (
            job_id, video_id,
            data['chunks_created'], data['chunks_passed_sync'],
            data['avg_sync_score'], data.get('min_sync_score'), data.get('max_sync_score'),
            data['avg_face_presence'], data.get('min_face_presence'), data.get('max_face_presence'),
            data['total_duration_seconds'], 
            data.get('usable_duration_seconds', data['total_duration_seconds']),
            data['storage_path'], data.get('file_size_mb', 0),
            data.get('metadata', {})
        ))
        
        conn.commit()
        
        return jsonify({
            'message': 'Results submitted. Please review.',
            'job_id': job_id
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============================================================================
# STUDENT REVIEW
# ============================================================================

@app.route('/api/videos/<video_id>/review', methods=['POST'])
def submit_review(video_id):
    """Submit student review and decision"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = session['student_id']
    data = request.json
    
    decision = data.get('decision')  # 'approved', 'rejected', 'flagged'
    
    if decision not in ['approved', 'rejected', 'flagged']:
        return jsonify({'error': 'Invalid decision'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Find job
        cur.execute("""
            SELECT job_id FROM processing_jobs
            WHERE video_id = %s
            AND assigned_to = %s
            AND status = 'reviewing'
        """, (video_id, student_id))
        
        job = cur.fetchone()
        if not job:
            return jsonify({'error': 'Job not found or not in review'}), 404
        
        job_id = job['job_id']
        
        # Update job status based on decision
        new_status = {
            'approved': 'completed',
            'rejected': 'rejected',
            'flagged': 'completed'  # Flagged but still completed
        }[decision]
        
        cur.execute("""
            UPDATE processing_jobs
            SET status = %s::job_status,
                reviewed_at = NOW()
            WHERE job_id = %s
        """, (new_status, job_id))
        
        # Insert student review
        cur.execute("""
            INSERT INTO student_reviews
            (job_id, video_id, student_id, decision,
             review_started_at, review_completed_at,
             audio_quality, video_quality, transcription_quality, overall_quality,
             has_issues, issue_categories, issue_notes,
             wrong_language, poor_audio, no_face, bad_sync, wrong_content)
            VALUES (%s, %s, %s, %s, NOW() - INTERVAL '2 minutes', NOW(),
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            job_id, video_id, student_id, decision,
            data.get('audio_quality', 3),
            data.get('video_quality', 3),
            data.get('transcription_quality', 3),
            data.get('overall_quality', 3),
            data.get('has_issues', False),
            data.get('issue_categories', []),
            data.get('issue_notes', ''),
            data.get('wrong_language', False),
            data.get('poor_audio', False),
            data.get('no_face', False),
            data.get('bad_sync', False),
            data.get('wrong_content', False)
        ))
        
        # Update video stats
        if decision == 'rejected':
            cur.execute("""
                UPDATE videos
                SET times_rejected = times_rejected + 1
                WHERE video_id = %s
            """, (video_id,))
        else:
            cur.execute("""
                UPDATE videos
                SET times_processed = times_processed + 1
                WHERE video_id = %s
            """, (video_id,))
        
        # Clear worker's current video
        cur.execute("""
            UPDATE workers
            SET current_video_id = NULL,
                last_active = NOW()
            WHERE worker_id = %s
        """, (student_id,))
        
        conn.commit()
        
        return jsonify({
            'message': f'Review submitted: {decision}',
            'decision': decision
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============================================================================
# STATISTICS
# ============================================================================

@app.route('/api/stats/student', methods=['GET'])
def student_stats():
    """Get current student's stats"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = session['student_id']
    
    conn = get_db()
    cur = conn.cursor()
    
    # Overall stats
    cur.execute("""
        SELECT 
            jobs_completed,
            jobs_rejected,
            jobs_failed,
            total_hours_processed,
            avg_processing_time_minutes,
            avg_quality_score
        FROM workers
        WHERE worker_id = %s
    """, (student_id,))
    
    stats = cur.fetchone()
    
    # Today's stats
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE pj.status = 'completed') as completed_today,
            COUNT(*) FILTER (WHERE pj.status = 'rejected') as rejected_today,
            COALESCE(SUM(pr.usable_duration_seconds) / 3600, 0) as hours_today
        FROM processing_jobs pj
        LEFT JOIN processing_results pr ON pj.job_id = pr.job_id
        WHERE pj.assigned_to = %s
        AND pj.completed_at >= CURRENT_DATE
    """, (student_id,))
    
    today = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'total': stats or {},
        'today': today or {}
    })

@app.route('/api/stats/overall', methods=['GET'])
def overall_stats():
    """Get overall dataset statistics"""
    conn = get_db()
    cur = conn.cursor()
    
    # Job statistics
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE status='pending') as pending,
            COUNT(*) FILTER (WHERE status='claimed') as claimed,
            COUNT(*) FILTER (WHERE status='processing') as processing,
            COUNT(*) FILTER (WHERE status='reviewing') as reviewing,
            COUNT(*) FILTER (WHERE status='completed') as completed,
            COUNT(*) FILTER (WHERE status='rejected') as rejected,
            COUNT(*) FILTER (WHERE status='failed') as failed
        FROM processing_jobs
    """)
    jobs = cur.fetchone()
    
    # Dataset statistics
    cur.execute("""
        SELECT 
            COUNT(DISTINCT v.video_id) as total_videos,
            COUNT(DISTINCT s.speaker_id) as total_speakers,
            COALESCE(SUM(pr.chunks_passed_sync), 0) as total_chunks,
            COALESCE(SUM(pr.usable_duration_seconds) / 3600, 0) as total_hours,
            COALESCE(AVG(pr.avg_sync_score), 0) as avg_sync_score,
            COALESCE(AVG(pr.avg_face_presence), 0) as avg_face_presence
        FROM videos v
        JOIN speakers s ON v.speaker_id = s.speaker_id
        LEFT JOIN processing_results pr ON v.video_id = pr.video_id
    """)
    dataset = cur.fetchone()
    
    # Active workers
    cur.execute("""
        SELECT COUNT(*) as active_workers
        FROM workers
        WHERE active = true
        AND last_active > NOW() - INTERVAL '1 hour'
    """)
    workers = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return jsonify({
        'jobs': jobs,
        'dataset': dataset,
        'workers': workers
    })

@app.route('/api/stats/domains', methods=['GET'])
def domain_stats():
    """Get statistics by domain"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM dataset_overview ORDER BY total_hours DESC")
    domains = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({'domains': domains})

# ============================================================================
# LOCAL PROCESSING TRIGGER
# ============================================================================
@app.route('/api/videos/<video_id>/process-local', methods=['POST'])
def process_local(video_id):
    """Trigger local processing via worker script"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    preset = data.get('preset', 'balanced')
    youtube_url = data.get('youtube_url')
    
    print(f"🎬 Starting processing for video {video_id} with preset {preset}")
    
    # Call worker script
    import subprocess
    import os
    
    # Get the base directory and worker directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    worker_dir = os.path.join(base_dir, 'worker')
    venv_python = os.path.join(base_dir, '.venv', 'bin', 'python')
    
    cmd = [
        venv_python,
        'process_video.py',
        video_id,
        youtube_url,
        preset
    ]
    
    # Run in background with correct working directory
    process = subprocess.Popen(
        cmd,
        cwd=worker_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print(f"✅ Processing started for video {video_id}")
    
    return jsonify({
        'message': 'Processing started',
        'video_id': video_id
    })


@app.route('/api/videos/<video_id>/status', methods=['GET'])
def get_video_status(video_id):
    """Get processing status for a video"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    print(f"📊 Checking status for video {video_id}")
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Get job status
        cur.execute("""
            SELECT 
                pj.status,
                pj.progress,
                pj.error_message,
                pr.chunks_created,
                pr.chunks_passed_sync,
                pr.avg_sync_score,
                pr.avg_face_presence,
                pr.min_sync_score,
                pr.max_sync_score,
                pr.min_face_presence,
                pr.max_face_presence,
                pr.total_duration_seconds,
                pr.usable_duration_seconds,
                pr.storage_path
            FROM processing_jobs pj
            LEFT JOIN processing_results pr ON pj.video_id = pr.video_id
            WHERE pj.video_id = %s
            ORDER BY pj.created_at DESC
            LIMIT 1
        """, (video_id,))
        
        job = cur.fetchone()
        
        if not job:
            print(f"❌ No job found for video {video_id}")
            return jsonify({
                'status': 'not_found',
                'logs': ['No processing job found']
            }), 404
        
        print(f"✅ Job status: {job['status']}, Progress: {job.get('progress', 0)}%")
        
        # Build response
        response = {
            'status': job['status'],
            'progress': job.get('progress', 0),
            'logs': []
        }
        
        # Add progress-based logs
        progress = job.get('progress', 0)
        if progress >= 10:
            response['logs'].append('🎬 Downloaded video from YouTube')
        if progress >= 25:
            response['logs'].append('🔊 Extracted and processed audio')
        if progress >= 40:
            response['logs'].append('✂️ Segmented by silence detection')
        if progress >= 55:
            response['logs'].append('👤 Completed face detection')
        if progress >= 70:
            response['logs'].append('🔄 Completed SyncNet analysis')
        if progress >= 85:
            response['logs'].append('🎯 Filtered chunks by quality')
        if progress >= 95:
            response['logs'].append('📝 Completed transcription')
        if progress >= 100:
            response['logs'].append('✅ Processing complete!')
        
        # If completed, add results
        if job['status'] == 'completed' and job['chunks_created']:
            response['results'] = {
                'chunks_created': job['chunks_created'],
                'chunks_passed_sync': job['chunks_passed_sync'],
                'avg_sync_score': float(job['avg_sync_score']) if job['avg_sync_score'] else 0,
                'min_sync_score': float(job['min_sync_score']) if job['min_sync_score'] else 0,
                'max_sync_score': float(job['max_sync_score']) if job['max_sync_score'] else 0,
                'avg_face_presence': float(job['avg_face_presence']) if job['avg_face_presence'] else 0,
                'min_face_presence': float(job['min_face_presence']) if job['min_face_presence'] else 0,
                'max_face_presence': float(job['max_face_presence']) if job['max_face_presence'] else 0,
                'total_duration_seconds': job['total_duration_seconds'] or 0,
                'usable_duration_seconds': job['usable_duration_seconds'] or 0,
                'storage_path': job['storage_path'] or ''
            }
        
        # If failed, add error
        if job['status'] == 'failed':
            response['error'] = job.get('error_message', 'Unknown error')
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# ============================================================================
# REAL PROCESSING - Background Worker Management
# ============================================================================
@app.route('/api/videos/<video_id>/process-real', methods=['POST'])
def process_real(video_id):
    """Trigger real processing via worker script"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    student_id = session['student_id']
    data = request.json
    preset = data.get('preset', 'balanced')
    youtube_url = data.get('youtube_url')
    
    logger.info(f"🎬 Processing request: {video_id} by {student_id}")
    
    # Check if already processing
    if video_id in processing_status and processing_status[video_id]['status'] == 'processing':
        return jsonify({'error': 'Already processing this video'}), 409
    
    # Start background thread
    thread = threading.Thread(
        target=run_worker_background,
        args=(video_id, youtube_url, preset, student_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Processing started',
        'video_id': video_id
    })

# ============================================================================
# REAL PROCESSING - Get Processing Status
# ============================================================================
@app.route('/api/videos/<video_id>/processing-status', methods=['GET'])
def get_processing_status(video_id):
    """Get current processing status"""
    if 'student_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    status = processing_status.get(video_id, {
        'status': 'not_found',
        'progress': 0,
        'logs': [],
        'results': None,
        'error': 'No processing found for this video'
    })
    
    logger.debug(f"📊 Status check for {video_id}: {status['status']}")
    
    return jsonify(status)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """API health check"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    print("="*60)
    print("🚀 Hybrid API Server Starting")
    print("="*60)
    print(f"Database: {DATABASE_URL[:30]}...")
    print(f"Port: 5000")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=True)