# Video Domain Feature

## Overview

This feature adds domain support at the **video level**, allowing videos to have their own domain that can differ from the speaker's default domain. This is useful when a speaker creates content across multiple topics/domains.

## What Changed

### Database Schema
- Added `domain` column to `videos` table (type: `domain_type`)
- Updated `pending_videos_queue` view to expose both `speaker_domain` and `video_domain`

### Backend (API)
- Updated `/api/videos/next` endpoint to return `speaker_domain` and `video_domain`
- Updated `/api/videos/short` endpoint to return both domains
- Added new endpoint: `POST /api/videos/<video_id>/update-domain` to change video domain

### Admin Scripts
- Updated `fetch_channel_videos.py` to set video domain (defaults to speaker's domain)
- Videos imported from YouTube now inherit speaker's domain by default

### Frontend (Web UI)
- Added domain dropdown in video preview stage
- Shows speaker's default domain as reference
- Allows changing video domain before processing
- Domain badge updates in real-time when changed

## Migration

For existing databases, run the migration:

```bash
# Make sure DATABASE_URL is set in your .env file
cd database
./run_migration.sh
```

Or manually with psql:

```bash
psql "$DATABASE_URL" < database/migrate_add_video_domain.sql
```

The migration will:
1. Add the `domain` column to existing `videos` table
2. Initialize domain from speaker's domain for all existing videos
3. Update the `pending_videos_queue` view

## Usage

### Web UI

When previewing a video before processing:

1. **Default Domain**: Video inherits speaker's domain automatically
2. **Change Domain**: Use the dropdown to select a different domain:
   - 🍳 Food Blogger
   - 🎓 Academician
   - 💹 Economic
   - 💰 Financial
   - 💪 Motivational Speaker
   - 😄 Comedian
   - 🎮 Sports & Gaming
   - 📋 General
   - 🔖 Other

3. **Domain Updates**: Changes are saved immediately to the database

### API

Update video domain programmatically:

```bash
curl -X POST http://localhost:5000/api/videos/<video_id>/update-domain \
  -H "Content-Type: application/json" \
  -d '{"domain": "comedian"}'
```

### Admin Scripts

When fetching videos from YouTube:

```python
# Videos automatically get speaker's domain
python admin/fetch_channel_videos.py speaker SPK001 10

# You can override domain per video (advanced)
videos = get_channel_videos(channel_id, 10)
for video in videos:
    video['domain'] = 'comedian'  # Override speaker's domain
add_videos_to_db(speaker_id, videos, speaker_domain)
```

## Examples

### Example 1: Food Blogger Does Interview

- **Speaker**: Cooking Channel (domain: `food_blogger`)
- **Normal Videos**: Cooking tutorials → domain: `food_blogger`
- **Special Video**: Interview with economist → domain: `economic`

### Example 2: Academician Does Motivational Talk

- **Speaker**: Professor (domain: `academician`)
- **Normal Videos**: Lectures → domain: `academician`
- **Special Video**: Motivational speech → domain: `motivational_speaker`

### Example 3: Comedian on Sports Podcast

- **Speaker**: Comedy Channel (domain: `comedian`)
- **Normal Videos**: Comedy sketches → domain: `comedian`
- **Special Video**: Sports commentary → domain: `sports_and_gaming`

## Benefits

1. **Accurate Categorization**: Videos are categorized by their actual content, not just speaker
2. **Better Dataset Organization**: More precise domain filtering and statistics
3. **Flexible Content**: Speakers can explore multiple topics without miscategorization
4. **Improved Search**: Find videos by topic regardless of speaker's primary domain
5. **Quality Control**: Domain-specific quality thresholds can be applied per video

## Database Views

### Pending Videos Queue

```sql
SELECT speaker_domain, video_domain, COUNT(*)
FROM pending_videos_queue
GROUP BY speaker_domain, video_domain;
```

Shows distribution of video domains across different speakers.

### Domain Statistics

```sql
SELECT 
    v.domain as video_domain,
    s.domain as speaker_domain,
    COUNT(*) as video_count
FROM videos v
JOIN speakers s ON v.speaker_id = s.speaker_id
GROUP BY v.domain, s.domain
ORDER BY video_count DESC;
```

Shows how often videos differ from their speaker's domain.

## Notes

- Video domain defaults to speaker's domain when videos are imported
- Domain can be changed at any time via UI or API
- Processing uses the video domain, not speaker domain
- Statistics and reports now use video domain for accurate categorization
