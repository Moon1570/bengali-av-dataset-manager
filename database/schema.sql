-- Bengali Audio-Visual Dataset Database Schema
-- Hybrid Version - Job Queue + Manual Review
-- Version 2.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Domain types
CREATE TYPE domain_type AS ENUM (
    'food_blogger',
    'academician',
    'economic',
    'financial',
    'motivational_speaker',
    'comedian',
    'sports_and_gaming',
    'general',
    'other'
);

-- Processing status types
CREATE TYPE job_status AS ENUM (
    'pending',
    'claimed',
    'processing',
    'reviewing',
    'completed',
    'rejected',
    'failed',
    'cancelled'
);

-- Processing presets
CREATE TYPE processing_preset AS ENUM (
    'strict',      -- High quality: sync>8.0, face>95%
    'balanced',    -- Default: sync>6.5, face>90%
    'lenient'      -- Lower bar: sync>5.0, face>80%
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Speakers table
CREATE TABLE speakers (
    speaker_id VARCHAR(50) PRIMARY KEY,
    youtube_channel_id VARCHAR(100) UNIQUE NOT NULL,
    channel_name VARCHAR(200),
    speaker_name VARCHAR(200),
    domain domain_type DEFAULT 'general',
    gender VARCHAR(20),
    estimated_age VARCHAR(20),
    nationality VARCHAR(50) DEFAULT 'BD',
    language VARCHAR(10) DEFAULT 'bn',
    verified BOOLEAN DEFAULT false,
    total_videos_processed INT DEFAULT 0,
    total_hours_contributed FLOAT DEFAULT 0,
    avg_quality_score FLOAT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Videos table
CREATE TABLE videos (
    video_id VARCHAR(50) PRIMARY KEY,
    youtube_url TEXT NOT NULL,
    speaker_id VARCHAR(50) REFERENCES speakers(speaker_id) ON DELETE CASCADE,
    title TEXT,
    description TEXT,
    duration_seconds INT,
    upload_date DATE,
    thumbnail_url TEXT,
    domain domain_type,
    quality_preference VARCHAR(20) DEFAULT '720p',
    validation_candidate BOOLEAN DEFAULT false,
    times_processed INT DEFAULT 0,
    times_rejected INT DEFAULT 0,
    added_at TIMESTAMP DEFAULT NOW()
);

-- Processing jobs table (UPDATED)
CREATE TABLE processing_jobs (
    job_id SERIAL PRIMARY KEY,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    status job_status DEFAULT 'pending',
    preset processing_preset DEFAULT 'balanced',
    assigned_to VARCHAR(50),
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    processing_time_seconds INT,
    error_message TEXT,
    processing_params JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_times CHECK (
        (assigned_at IS NULL OR started_at IS NULL OR assigned_at <= started_at) AND
        (started_at IS NULL OR completed_at IS NULL OR started_at <= completed_at)
    )
);

-- Processing results table (UPDATED)
CREATE TABLE processing_results (
    result_id SERIAL PRIMARY KEY,
    job_id INT REFERENCES processing_jobs(job_id) ON DELETE CASCADE,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    
    -- Chunk statistics
    chunks_created INT NOT NULL,
    chunks_passed_sync INT NOT NULL,
    chunks_manually_approved INT DEFAULT 0,
    chunks_manually_rejected INT DEFAULT 0,
    
    -- Quality metrics
    avg_sync_score FLOAT,
    min_sync_score FLOAT,
    max_sync_score FLOAT,
    avg_face_presence FLOAT,
    min_face_presence FLOAT,
    max_face_presence FLOAT,
    
    -- Duration
    total_duration_seconds FLOAT,
    usable_duration_seconds FLOAT,
    
    -- Storage
    storage_path TEXT,
    file_size_mb FLOAT,
    
    -- Metadata
    metadata_json JSONB,
    
    -- Quality flags
    has_quality_issues BOOLEAN DEFAULT false,
    quality_issues TEXT[],
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workers/Students table (UPDATED)
CREATE TABLE workers (
    worker_id VARCHAR(50) PRIMARY KEY,
    student_name VARCHAR(100),
    email VARCHAR(100),
    active BOOLEAN DEFAULT true,
    
    -- Statistics
    jobs_completed INT DEFAULT 0,
    jobs_rejected INT DEFAULT 0,
    jobs_failed INT DEFAULT 0,
    total_hours_processed FLOAT DEFAULT 0,
    avg_processing_time_minutes FLOAT,
    avg_quality_score FLOAT,
    
    -- Activity tracking
    last_active TIMESTAMP,
    current_video_id VARCHAR(50),
    
    -- Performance metrics
    quality_warnings INT DEFAULT 0,
    fast_approvals_count INT DEFAULT 0, -- Suspiciously fast reviews
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Quality validations table (UPDATED)
CREATE TABLE quality_validations (
    validation_id SERIAL PRIMARY KEY,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    chunk_id VARCHAR(100),
    validator_id VARCHAR(50),
    validation_type VARCHAR(50), -- 'student_flag', 'admin_review', 'random_sample', 'batch_validation'
    
    -- Rating
    quality_score INT CHECK (quality_score BETWEEN 1 AND 5),
    
    -- Issues
    issues TEXT[],
    issue_description TEXT,
    
    -- Recommendations
    action_taken VARCHAR(50), -- 'approved', 'rejected', 'reprocess', 'flagged'
    
    validated_at TIMESTAMP DEFAULT NOW()
);

-- Student reviews table (NEW - for hybrid workflow)
CREATE TABLE student_reviews (
    review_id SERIAL PRIMARY KEY,
    job_id INT REFERENCES processing_jobs(job_id) ON DELETE CASCADE,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    student_id VARCHAR(50) REFERENCES workers(worker_id),
    
    -- Review decision
    decision VARCHAR(20) CHECK (decision IN ('approved', 'rejected', 'flagged')),
    
    -- Timing
    review_started_at TIMESTAMP,
    review_completed_at TIMESTAMP,
    review_duration_seconds INT,
    
    -- Quality assessment
    audio_quality INT CHECK (audio_quality BETWEEN 1 AND 5),
    video_quality INT CHECK (video_quality BETWEEN 1 AND 5),
    transcription_quality INT CHECK (transcription_quality BETWEEN 1 AND 5),
    overall_quality INT CHECK (overall_quality BETWEEN 1 AND 5),
    
    -- Issues
    has_issues BOOLEAN DEFAULT false,
    issue_categories TEXT[],
    issue_notes TEXT,
    
    -- Specific problems
    wrong_language BOOLEAN DEFAULT false,
    poor_audio BOOLEAN DEFAULT false,
    no_face BOOLEAN DEFAULT false,
    bad_sync BOOLEAN DEFAULT false,
    wrong_content BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Dataset statistics table
CREATE TABLE dataset_statistics (
    stat_id SERIAL PRIMARY KEY,
    domain domain_type,
    speaker_count INT,
    video_count INT,
    chunk_count INT,
    total_duration_hours FLOAT,
    avg_quality_score FLOAT,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Admin actions log (NEW - for tracking manual interventions)
CREATE TABLE admin_actions (
    action_id SERIAL PRIMARY KEY,
    admin_id VARCHAR(50),
    action_type VARCHAR(50), -- 'approve', 'reject', 'reassign', 'delete', 'modify_quality'
    target_type VARCHAR(50), -- 'video', 'job', 'worker', 'speaker'
    target_id VARCHAR(100),
    reason TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_video ON processing_jobs(video_id);
CREATE INDEX idx_jobs_assigned ON processing_jobs(assigned_to);
CREATE INDEX idx_jobs_preset ON processing_jobs(preset);
CREATE INDEX idx_jobs_created ON processing_jobs(created_at DESC);

CREATE INDEX idx_results_video ON processing_results(video_id);
CREATE INDEX idx_results_job ON processing_results(job_id);
CREATE INDEX idx_results_quality ON processing_results(avg_sync_score, avg_face_presence);

CREATE INDEX idx_videos_speaker ON videos(speaker_id);
CREATE INDEX idx_videos_processed ON videos(times_processed);

CREATE INDEX idx_speakers_domain ON speakers(domain);
CREATE INDEX idx_speakers_verified ON speakers(verified);

CREATE INDEX idx_validations_video ON quality_validations(video_id);
CREATE INDEX idx_validations_type ON quality_validations(validation_type);

CREATE INDEX idx_reviews_student ON student_reviews(student_id);
CREATE INDEX idx_reviews_decision ON student_reviews(decision);
CREATE INDEX idx_reviews_quality ON student_reviews(overall_quality);

CREATE INDEX idx_workers_active ON workers(active, last_active);

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- Dataset overview by domain
CREATE VIEW dataset_overview AS
SELECT 
    s.domain,
    COUNT(DISTINCT s.speaker_id) as speaker_count,
    COUNT(DISTINCT v.video_id) as video_count,
    COUNT(DISTINCT pj.job_id) FILTER (WHERE pj.status = 'completed') as completed_jobs,
    COALESCE(SUM(pr.chunks_passed_sync), 0) as total_chunks,
    COALESCE(SUM(pr.usable_duration_seconds) / 3600, 0) as total_hours,
    COALESCE(AVG(pr.avg_sync_score), 0) as avg_sync_score,
    COALESCE(AVG(pr.avg_face_presence), 0) as avg_face_presence,
    COALESCE(AVG(sr.overall_quality), 0) as avg_student_rating
FROM speakers s
LEFT JOIN videos v ON s.speaker_id = v.speaker_id
LEFT JOIN processing_jobs pj ON v.video_id = pj.video_id
LEFT JOIN processing_results pr ON pj.job_id = pr.job_id
LEFT JOIN student_reviews sr ON pj.job_id = sr.job_id AND sr.decision = 'approved'
GROUP BY s.domain;

-- Worker performance view
CREATE VIEW worker_performance AS
SELECT 
    w.worker_id,
    w.student_name,
    w.jobs_completed,
    w.jobs_rejected,
    w.jobs_failed,
    ROUND((w.jobs_completed::FLOAT / NULLIF(w.jobs_completed + w.jobs_rejected + w.jobs_failed, 0) * 100)::NUMERIC, 1) as success_rate,
    w.total_hours_processed,
    w.avg_processing_time_minutes,
    COALESCE(AVG(sr.overall_quality), 0) as avg_review_quality,
    w.quality_warnings,
    w.last_active,
    CASE 
        WHEN w.last_active > NOW() - INTERVAL '1 hour' THEN 'active'
        WHEN w.last_active > NOW() - INTERVAL '24 hours' THEN 'recent'
        ELSE 'inactive'
    END as activity_status
FROM workers w
LEFT JOIN student_reviews sr ON w.worker_id = sr.student_id
GROUP BY w.worker_id, w.student_name, w.jobs_completed, w.jobs_rejected, 
         w.jobs_failed, w.total_hours_processed, w.avg_processing_time_minutes,
         w.quality_warnings, w.last_active;

-- Pending videos with priority
CREATE VIEW pending_videos_queue AS
SELECT 
    v.video_id,
    v.youtube_url,
    v.title,
    v.duration_seconds,
    s.speaker_id,
    s.speaker_name,
    s.domain as speaker_domain,
    v.domain as video_domain,
    v.times_rejected,
    v.times_processed,
    pj.retry_count,
    -- Priority score (lower = higher priority)
    (v.times_rejected * 10 + v.times_processed * 5 + pj.retry_count) as priority_penalty,
    pj.created_at as queued_at
FROM videos v
JOIN speakers s ON v.speaker_id = s.speaker_id
JOIN processing_jobs pj ON v.video_id = pj.video_id
WHERE pj.status = 'pending'
ORDER BY priority_penalty ASC, pj.created_at ASC;

-- Quality issues summary
CREATE VIEW quality_issues_summary AS
SELECT 
    v.video_id,
    v.title,
    s.speaker_name,
    s.domain,
    sr.decision,
    sr.overall_quality,
    sr.issue_categories,
    sr.issue_notes,
    w.worker_id as reviewed_by,
    sr.created_at as reviewed_at
FROM student_reviews sr
JOIN videos v ON sr.video_id = v.video_id
JOIN speakers s ON v.speaker_id = s.speaker_id
JOIN workers w ON sr.student_id = w.worker_id
WHERE sr.has_issues = true OR sr.decision = 'rejected' OR sr.overall_quality <= 2
ORDER BY sr.created_at DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Update dataset statistics
CREATE OR REPLACE FUNCTION update_dataset_statistics()
RETURNS void AS $$
BEGIN
    DELETE FROM dataset_statistics;
    
    INSERT INTO dataset_statistics (
        domain, speaker_count, video_count, chunk_count, 
        total_duration_hours, avg_quality_score, last_updated
    )
    SELECT 
        domain,
        speaker_count,
        video_count,
        total_chunks,
        total_hours,
        (avg_sync_score + avg_face_presence) / 2 as avg_quality_score,
        NOW()
    FROM dataset_overview;
END;
$$ LANGUAGE plpgsql;

-- Calculate processing time
CREATE OR REPLACE FUNCTION calculate_processing_time()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status = 'processing' THEN
        NEW.processing_time_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_processing_time
BEFORE UPDATE ON processing_jobs
FOR EACH ROW
EXECUTE FUNCTION calculate_processing_time();

-- Update worker stats on job completion
CREATE OR REPLACE FUNCTION update_worker_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE workers
        SET jobs_completed = jobs_completed + 1,
            last_active = NOW()
        WHERE worker_id = NEW.assigned_to;
        
    ELSIF NEW.status = 'rejected' AND OLD.status != 'rejected' THEN
        UPDATE workers
        SET jobs_rejected = jobs_rejected + 1,
            last_active = NOW()
        WHERE worker_id = NEW.assigned_to;
        
    ELSIF NEW.status = 'failed' AND OLD.status != 'failed' THEN
        UPDATE workers
        SET jobs_failed = jobs_failed + 1,
            last_active = NOW()
        WHERE worker_id = NEW.assigned_to;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_worker_stats
AFTER UPDATE ON processing_jobs
FOR EACH ROW
EXECUTE FUNCTION update_worker_stats();

-- Update speaker stats when video completed
CREATE OR REPLACE FUNCTION update_speaker_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE speakers s
    SET total_videos_processed = (
            SELECT COUNT(*) FROM videos v
            JOIN processing_jobs pj ON v.video_id = pj.video_id
            WHERE v.speaker_id = s.speaker_id AND pj.status = 'completed'
        ),
        total_hours_contributed = (
            SELECT COALESCE(SUM(pr.usable_duration_seconds) / 3600, 0)
            FROM videos v
            JOIN processing_results pr ON v.video_id = pr.video_id
            WHERE v.speaker_id = s.speaker_id
        ),
        updated_at = NOW()
    WHERE s.speaker_id = (
        SELECT speaker_id FROM videos WHERE video_id = NEW.video_id
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_speaker_stats
AFTER INSERT ON processing_results
FOR EACH ROW
EXECUTE FUNCTION update_speaker_stats();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert admin worker
INSERT INTO workers (worker_id, student_name, active) 
VALUES ('admin', 'Administrator', true)
ON CONFLICT (worker_id) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE speakers IS 'YouTube channels and speaker metadata';
COMMENT ON TABLE videos IS 'Individual videos to be processed';
COMMENT ON TABLE processing_jobs IS 'Job queue with manual review workflow';
COMMENT ON TABLE processing_results IS 'Automated processing results';
COMMENT ON TABLE student_reviews IS 'Manual student reviews and decisions';
COMMENT ON TABLE workers IS 'Student workers with performance tracking';
COMMENT ON TABLE quality_validations IS 'Quality checks and validations';
COMMENT ON TABLE admin_actions IS 'Admin intervention audit log';

COMMENT ON COLUMN processing_jobs.preset IS 'Quality preset: strict, balanced, or lenient';
COMMENT ON COLUMN student_reviews.decision IS 'Student decision: approved, rejected, or flagged';
COMMENT ON COLUMN student_reviews.review_duration_seconds IS 'How long student spent reviewing';