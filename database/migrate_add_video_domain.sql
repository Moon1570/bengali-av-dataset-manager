-- Migration: Add domain column to videos table
-- This allows videos to have their own domain, independent of speaker domain
-- Run this migration on existing databases

-- Add domain column to videos table (allows NULL initially)
ALTER TABLE videos ADD COLUMN IF NOT EXISTS domain domain_type;

-- Set default domain from speaker's domain for existing videos
UPDATE videos v
SET domain = s.domain
FROM speakers s
WHERE v.speaker_id = s.speaker_id
AND v.domain IS NULL;

-- Update the pending_videos_queue view to include both domains
DROP VIEW IF EXISTS pending_videos_queue;
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

-- Add comment
COMMENT ON COLUMN videos.domain IS 'Video domain - can differ from speaker domain';

-- Show migration results
SELECT 
    COUNT(*) as total_videos,
    COUNT(domain) as videos_with_domain,
    COUNT(*) - COUNT(domain) as videos_without_domain
FROM videos;

-- Show domain distribution
SELECT 
    COALESCE(v.domain::text, 'NULL') as video_domain,
    COUNT(*) as count
FROM videos v
GROUP BY v.domain
ORDER BY count DESC;
