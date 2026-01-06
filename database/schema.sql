-- Bengali Audio-Visual Dataset Database Schema
-- Version 1.0

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
    'processing',
    'completed',
    'failed',
    'cancelled'
);

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
    duration_seconds INT,
    upload_date DATE,
    quality_preference VARCHAR(20) DEFAULT '720p',
    validation_candidate BOOLEAN DEFAULT false,
    added_at TIMESTAMP DEFAULT NOW()
);

-- Processing jobs table
CREATE TABLE processing_jobs (
    job_id SERIAL PRIMARY KEY,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    status job_status DEFAULT 'pending',
    assigned_to VARCHAR(50),
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    processing_params JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Processing results table
CREATE TABLE processing_results (
    result_id SERIAL PRIMARY KEY,
    job_id INT REFERENCES processing_jobs(job_id) ON DELETE CASCADE,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    chunks_created INT,
    chunks_passed_sync INT,
    avg_sync_score FLOAT,
    avg_face_presence FLOAT,
    total_duration_seconds FLOAT,
    storage_path TEXT,
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workers table
CREATE TABLE workers (
    worker_id VARCHAR(50) PRIMARY KEY,
    student_name VARCHAR(100),
    email VARCHAR(100),
    active BOOLEAN DEFAULT true,
    jobs_completed INT DEFAULT 0,
    jobs_failed INT DEFAULT 0,
    avg_processing_time_minutes FLOAT,
    last_active TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Quality validations table
CREATE TABLE quality_validations (
    validation_id SERIAL PRIMARY KEY,
    video_id VARCHAR(50) REFERENCES videos(video_id) ON DELETE CASCADE,
    chunk_id VARCHAR(100),
    validator_id VARCHAR(50),
    validation_type VARCHAR(50),
    quality_score INT CHECK (quality_score BETWEEN 1 AND 5),
    issues TEXT,
    validated_at TIMESTAMP DEFAULT NOW()
);

-- Dataset statistics table (for caching aggregated stats)
CREATE TABLE dataset_statistics (
    stat_id SERIAL PRIMARY KEY,
    domain domain_type,
    speaker_count INT,
    video_count INT,
    chunk_count INT,
    total_duration_hours FLOAT,
    avg_quality_score FLOAT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_video ON processing_jobs(video_id);
CREATE INDEX idx_jobs_assigned ON processing_jobs(assigned_to);
CREATE INDEX idx_results_video ON processing_results(video_id);
CREATE INDEX idx_videos_speaker ON videos(speaker_id);
CREATE INDEX idx_speakers_domain ON speakers(domain);
CREATE INDEX idx_validations_video ON quality_validations(video_id);

-- Create view for easy querying
CREATE VIEW dataset_overview AS
SELECT 
    s.speaker_id,
    s.speaker_name,
    s.channel_name,
    s.domain,
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
GROUP BY s.speaker_id, s.speaker_name, s.channel_name, s.domain;

-- Function to update dataset statistics
CREATE OR REPLACE FUNCTION update_dataset_statistics()
RETURNS void AS $$
BEGIN
    DELETE FROM dataset_statistics;
    
    INSERT INTO dataset_statistics (domain, speaker_count, video_count, chunk_count, total_duration_hours, avg_quality_score)
    SELECT 
        s.domain,
        COUNT(DISTINCT s.speaker_id) as speaker_count,
        COUNT(DISTINCT v.video_id) as video_count,
        COALESCE(SUM(pr.chunks_passed_sync), 0) as chunk_count,
        COALESCE(SUM(pr.total_duration_seconds) / 3600, 0) as total_duration_hours,
        COALESCE(AVG(pr.avg_sync_score), 0) as avg_quality_score
    FROM speakers s
    LEFT JOIN videos v ON s.speaker_id = v.speaker_id
    LEFT JOIN processing_results pr ON v.video_id = pr.video_id
    GROUP BY s.domain;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update worker stats
CREATE OR REPLACE FUNCTION update_worker_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status = 'processing' THEN
        UPDATE workers
        SET jobs_completed = jobs_completed + 1,
            avg_processing_time_minutes = (
                COALESCE(avg_processing_time_minutes * jobs_completed, 0) + 
                EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at)) / 60
            ) / (jobs_completed + 1),
            last_active = NOW()
        WHERE worker_id = NEW.assigned_to;
    ELSIF NEW.status = 'failed' AND OLD.status = 'processing' THEN
        UPDATE workers
        SET jobs_failed = jobs_failed + 1,
            last_active = NOW()
        WHERE worker_id = NEW.assigned_to;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER worker_stats_trigger
AFTER UPDATE ON processing_jobs
FOR EACH ROW
EXECUTE FUNCTION update_worker_stats();

-- Insert initial data
INSERT INTO workers (worker_id, student_name, active) VALUES ('admin', 'Administrator', true);

-- Comments
COMMENT ON TABLE speakers IS 'YouTube channels and speaker metadata';
COMMENT ON TABLE videos IS 'Individual videos to be processed';
COMMENT ON TABLE processing_jobs IS 'Job queue for video processing';
COMMENT ON TABLE processing_results IS 'Results from processed videos';
COMMENT ON TABLE workers IS 'Student workers processing videos';
COMMENT ON TABLE quality_validations IS 'Manual quality checks on processed chunks';
COMMENT ON COLUMN speakers.domain IS 'Content domain: food_blogger, academician, economic, financial, motivational_speaker, comedian, sports_and_gaming, general, other';