"""
Job Management API Server
Handles job queue, worker coordination, and result tracking
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
from config import Config

# Setup
app = Flask(__name__)
CORS(app)
config = Config()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
def get_db():
    """Get database connection"""
    return psycopg2.connect(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT,
        cursor_factory=RealDictCursor
    )

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Claim job
@app.route('/api/jobs/claim', methods=['POST'])
def claim_job():
    """Worker claims next available job"""
    worker_id = request.json.get('worker_id')
    
    if not worker_id:
        return jsonify({'error': 'worker_id required'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Register worker if not exists
        cur.execute("""
            INSERT INTO workers (worker_id, last_active)
            VALUES (%s, NOW())
            ON CONFLICT (worker_id) DO UPDATE
            SET last_active = NOW(), active = true
        """, (worker_id,))
        
        # Atomic job claiming with SKIP LOCKED
        cur.execute("""
            UPDATE processing_jobs 
            SET status='processing', 
                assigned_to=%s, 
                assigned_at=NOW(),
                started_at=NOW()
            WHERE job_id = (
                SELECT job_id FROM processing_jobs 
                WHERE status='pending' 
                AND retry_count < %s
                ORDER BY job_id
                LIMIT 1 
                FOR UPDATE SKIP LOCKED
            )
            RETURNING job_id, video_id
        """, (worker_id, config.MAX_RETRY_COUNT))
        
        job = cur.fetchone()
        
        if not job:
            conn.commit()
            return jsonify({'message': 'No jobs available'}), 404
        
        # Get video details
        cur.execute("""
            SELECT 
                v.video_id,
                v.youtube_url,
                v.title,
                v.duration_seconds,
                s.speaker_id,
                s.speaker_name,
                s.channel_name,
                s.domain
            FROM videos v
            JOIN speakers s ON v.speaker_id = s.speaker_id
            WHERE v.video_id = %s
        """, (job['video_id'],))
        
        video = cur.fetchone()
        
        conn.commit()
        
        logger.info(f"Job {job['job_id']} claimed by worker {worker_id}")
        
        return jsonify({
            'job_id': job['job_id'],
            'video_id': video['video_id'],
            'youtube_url': video['youtube_url'],
            'title': video['title'],
            'speaker_id': video['speaker_id'],
            'speaker_name': video['speaker_name'],
            'channel_name': video['channel_name'],
            'domain': video['domain'],
            'duration_seconds': video['duration_seconds']
        })
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error claiming job: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Complete job
@app.route('/api/jobs/<int:job_id>/complete', methods=['POST'])
def complete_job(job_id):
    """Worker reports job completion"""
    data = request.json
    
    required_fields = ['chunks_created', 'chunks_passed_sync', 'storage_path']
    if not all(field in data for field in required_fields):
        return jsonify({'error': f'Missing required fields: {required_fields}'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Update job status
        cur.execute("""
            UPDATE processing_jobs
            SET status='completed',
                completed_at=NOW()
            WHERE job_id=%s
            RETURNING video_id, assigned_to
        """, (job_id,))
        
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Job not found'}), 404
        
        # Insert processing results
        cur.execute("""
            INSERT INTO processing_results 
            (job_id, video_id, chunks_created, chunks_passed_sync, 
             avg_sync_score, avg_face_presence, total_duration_seconds,
             storage_path, metadata_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            job_id,
            result['video_id'],
            data['chunks_created'],
            data['chunks_passed_sync'],
            data.get('avg_sync_score', 0.0),
            data.get('avg_face_presence', 0.0),
            data.get('total_duration_seconds', 0.0),
            data['storage_path'],
            data.get('metadata_json', {})
        ))
        
        conn.commit()
        
        logger.info(f"Job {job_id} completed by worker {result['assigned_to']}")
        
        return jsonify({
            'message': 'Job completed successfully',
            'job_id': job_id,
            'video_id': result['video_id']
        })
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error completing job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Fail job
@app.route('/api/jobs/<int:job_id>/fail', methods=['POST'])
def fail_job(job_id):
    """Worker reports job failure"""
    error_message = request.json.get('error_message', 'Unknown error')
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE processing_jobs
            SET status = CASE 
                    WHEN retry_count < %s THEN 'pending'
                    ELSE 'failed'
                END,
                retry_count = retry_count + 1,
                error_message = %s,
                assigned_to = NULL,
                assigned_at = NULL
            WHERE job_id = %s
            RETURNING retry_count, assigned_to
        """, (config.MAX_RETRY_COUNT - 1, error_message, job_id))
        
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Job not found'}), 404
        
        conn.commit()
        
        logger.warning(f"Job {job_id} failed (retry {result['retry_count']}): {error_message}")
        
        return jsonify({
            'message': 'Job marked as failed',
            'retry_count': result['retry_count'],
            'will_retry': result['retry_count'] < config.MAX_RETRY_COUNT
        })
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error failing job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Job statistics
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall job statistics"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Job stats
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE status='pending') as pending,
                COUNT(*) FILTER (WHERE status='processing') as processing,
                COUNT(*) FILTER (WHERE status='completed') as completed,
                COUNT(*) FILTER (WHERE status='failed') as failed,
                COUNT(*) as total
            FROM processing_jobs
        """)
        job_stats = cur.fetchone()
        
        # Domain distribution
        cur.execute("""
            SELECT domain, COUNT(DISTINCT speaker_id) as speaker_count
            FROM speakers
            GROUP BY domain
            ORDER BY speaker_count DESC
        """)
        domain_stats = cur.fetchall()
        
        # Worker stats
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE active=true) as active_workers,
                SUM(jobs_completed) as total_completed,
                SUM(jobs_failed) as total_failed
            FROM workers
        """)
        worker_stats = cur.fetchone()
        
        # Dataset size
        cur.execute("""
            SELECT 
                COUNT(DISTINCT video_id) as total_videos,
                COALESCE(SUM(chunks_passed_sync), 0) as total_chunks,
                COALESCE(SUM(total_duration_seconds) / 3600, 0) as total_hours
            FROM processing_results
        """)
        dataset_stats = cur.fetchone()
        
        return jsonify({
            'jobs': job_stats,
            'domains': domain_stats,
            'workers': worker_stats,
            'dataset': dataset_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Cleanup stuck jobs
@app.route('/api/jobs/cleanup', methods=['POST'])
def cleanup_stuck_jobs():
    """Reset jobs stuck in processing for too long"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        timeout = timedelta(hours=config.JOB_TIMEOUT_HOURS)
        
        cur.execute("""
            UPDATE processing_jobs
            SET status = 'pending',
                assigned_to = NULL,
                assigned_at = NULL,
                retry_count = retry_count + 1,
                error_message = 'Job timeout - worker unresponsive'
            WHERE status = 'processing'
            AND started_at < NOW() - INTERVAL '%s hours'
            AND retry_count < %s
            RETURNING job_id, video_id, assigned_to
        """, (config.JOB_TIMEOUT_HOURS, config.MAX_RETRY_COUNT))
        
        stuck_jobs = cur.fetchall()
        
        conn.commit()
        
        logger.info(f"Cleaned up {len(stuck_jobs)} stuck jobs")
        
        return jsonify({
            'message': f'Reset {len(stuck_jobs)} stuck jobs',
            'jobs': stuck_jobs
        })
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning up jobs: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Get domain statistics
@app.route('/api/stats/domains', methods=['GET'])
def get_domain_stats():
    """Get detailed statistics by domain"""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                s.domain,
                COUNT(DISTINCT s.speaker_id) as speaker_count,
                COUNT(DISTINCT v.video_id) as video_count,
                COUNT(DISTINCT pj.job_id) FILTER (WHERE pj.status = 'completed') as completed_jobs,
                COALESCE(SUM(pr.chunks_passed_sync), 0) as total_chunks,
                COALESCE(SUM(pr.total_duration_seconds) / 3600, 0) as total_hours,
                COALESCE(AVG(pr.avg_sync_score), 0) as avg_sync_score,
                COALESCE(AVG(pr.avg_face_presence), 0) as avg_face_presence
            FROM speakers s
            LEFT JOIN videos v ON s.speaker_id = v.speaker_id
            LEFT JOIN processing_jobs pj ON v.video_id = pj.video_id
            LEFT JOIN processing_results pr ON pj.job_id = pr.job_id
            GROUP BY s.domain
            ORDER BY total_hours DESC
        """)
        
        stats = cur.fetchall()
        
        return jsonify({
            'domains': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting domain stats: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Main
if __name__ == '__main__':
    logger.info(f"Starting API server on {config.API_HOST}:{config.API_PORT}")
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.DEBUG
    )