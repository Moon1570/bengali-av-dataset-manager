# Bengali Audio-Visual Dataset Manager

A distributed system for creating VoxCeleb-style Bengali audio-visual speech datasets with domain classification and quality control.

## Overview

This system enables coordinated video processing across multiple workers with:
- **Domain Classification**: 7 content categories (food, academic, economic, financial, motivational, comedy, sports/gaming)
- **Distributed Processing**: Multiple students can process videos concurrently
- **Quality Control**: Automated and manual validation
- **Job Queue Management**: Prevents duplicate work
- **Speaker Tracking**: Links videos to speaker identities

## Features

- ✅ PostgreSQL database with domain classification
- ✅ REST API for job queue management
- ✅ Worker scripts for distributed processing
- ✅ YouTube video fetching
- ✅ Speaker management tools
- ⏳ Quality dashboard (in development)
- ⏳ Dataset browser UI (in development)

## Quick Start

### Prerequisites

- **OS**: Ubuntu 22.04+ or macOS 12+ (Monterey or later)
- Python 3.8+
- PostgreSQL 12+
- Docker (for video processing)
- 50GB+ free disk space
- **macOS only**: Homebrew package manager

### 1. Clone Your Pipeline

Ensure you have your existing Bengali pipeline ready:
```bash
git clone <your-bengali-pipeline-repo>
cd bengali-pipeline
```

### 2. Set Up Database

**Linux:**
```bash
cd database
chmod +x init_db.sh
./init_db.sh
```

**macOS:**
```bash
# Install PostgreSQL if not already installed
brew install postgresql@14
brew services start postgresql@14

# Run database setup
cd database
chmod +x init_db.sh
./init_db.sh
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

### 4. Start API Server

```bash
cd api
pip install -r requirements.txt
python app.py
```

Server runs at: `http://localhost:5000`

### 5. Add Speakers

```bash
cd admin
pip install -r requirements.txt

# Get YouTube API key from: https://console.cloud.google.com/apis/credentials
export YOUTUBE_API_KEY='your-key-here'

# Add speakers interactively
python populate_speakers.py add

# Or import from CSV
python populate_speakers.py import speakers.csv
```

### 6. Fetch Videos

```bash
# Fetch 20 videos per speaker
python fetch_channel_videos.py all 20

# Or fetch for specific domain
python fetch_channel_videos.py domain food_blogger 30
```

### 7. Set Up Worker

```bash
cd worker
chmod +x setup_worker.sh
./setup_worker.sh

# Process videos
python process_video.py
```

## Architecture

```
┌─────────────────┐
│  PostgreSQL DB  │
│  - Speakers     │
│  - Videos       │
│  - Jobs         │
│  - Results      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   REST API      │
│  - Job Queue    │
│  - Stats        │
│  - Coordination │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Worker 1       │◄────►│   Storage    │
│  - Download     │      │  (Shared)    │
│  - Process      │      └──────────────┘
│  - Upload       │
└─────────────────┘
         ▲
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│Worker│  │Worker│
│  2   │  │  3   │
└──────┘  └──────┘
```

## Domain Classification

Videos are categorized into 7 domains:

| Domain | Description | Example Channels |
|--------|-------------|------------------|
| `food_blogger` | Cooking, recipes, food reviews | Cooking channels |
| `academician` | Education, lectures, tutorials | University professors |
| `economic` | Economics, market analysis | Economic analysts |
| `financial` | Finance, investment, banking | Financial advisors |
| `motivational_speaker` | Motivation, self-help | Motivational speakers |
| `comedian` | Comedy, entertainment | Stand-up comedians |
| `sports_and_gaming` | Sports, gaming commentary | Sports channels |

## Project Structure

```
bengali-dataset-manager/
├── database/           # Database schema and setup
├── api/               # REST API server
├── worker/            # Video processing workers
├── admin/             # Management tools
├── frontend/          # UI dashboard (coming soon)
└── docs/              # Documentation
```

## API Endpoints

### Job Management
- `POST /api/jobs/claim` - Claim next job
- `POST /api/jobs/{id}/complete` - Report completion
- `POST /api/jobs/{id}/fail` - Report failure
- `POST /api/jobs/cleanup` - Reset stuck jobs

### Statistics
- `GET /api/stats` - Overall statistics
- `GET /api/stats/domains` - Domain breakdown
- `GET /api/health` - Health check

## Configuration

### Environment Variables

```bash
# Database
DB_HOST=localhost
DB_NAME=voxceleb_dataset
DB_USER=dataset_admin
DB_PASSWORD=your_password
DB_PORT=5432

# API
API_HOST=0.0.0.0
API_PORT=5000
DEBUG=False

# Worker
WORKER_ID=student_001
API_URL=http://server-ip:5000
PIPELINE_DIR=/path/to/bengali-pipeline
STORAGE_BASE=/mnt/dataset_storage

# YouTube
YOUTUBE_API_KEY=your_api_key
```

## Speaker CSV Format

```csv
speaker_id,channel_id,channel_name,speaker_name,domain,gender,nationality
SPK001,UCxxxxx,Channel Name,Speaker Name,food_blogger,M,BD
SPK002,UCyyyyy,Another Channel,Another Speaker,academician,F,BD
```

## Processing Pipeline

1. **Download**: Worker downloads video from YouTube
2. **Process**: Runs through your existing Docker pipeline
   - Audio segmentation
   - Face detection
   - SyncNet filtering
   - Transcription
3. **Upload**: Results uploaded to shared storage
4. **Report**: Metadata saved to database

## Quality Metrics

Target metrics for dataset quality:

- **Sync Score**: >7.0 average
- **Face Presence**: >90% average
- **Retention Rate**: 50-70% chunks pass filters
- **Transcription Coverage**: >85% of chunks

## Monitoring

### Check System Status
```bash
curl http://localhost:5000/api/stats | jq
```

### Check Database
```bash
psql -U dataset_admin -d voxceleb_dataset -c "
SELECT 
    status, 
    COUNT(*) as count 
FROM processing_jobs 
GROUP BY status;
"
```

### View Worker Performance
```bash
psql -U dataset_admin -d voxceleb_dataset -c "
SELECT * FROM workers ORDER BY jobs_completed DESC;
"
```

## Troubleshooting

### Database Connection Failed

**Linux:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Restart if needed
sudo systemctl restart postgresql
```

**macOS:**
```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Restart if needed
brew services restart postgresql@14
```

### Worker Can't Claim Jobs
- Verify API URL in worker .env
- Check API server is running
- Ensure database has pending jobs

### Video Download Fails
```bash
# Update yt-dlp
pip install --upgrade yt-dlp
```

### Processing Times Out
- Increase timeout in worker config
- Check Docker container resources
- Verify GPU is accessible (if using GPU mode)

## Contributing

For students processing videos:
1. Set up your worker using `setup_worker.sh`
2. Run `python process_video.py` to process jobs
3. Report any issues to project lead

## Dataset Output

Final dataset structure:
```
storage/
├── VIDEO_ID_1/
│   ├── video_normal/     # Original chunks
│   ├── video_cropped/    # Face-cropped 224x224
│   ├── audio/            # Extracted audio
│   └── metadata.json     # Processing metadata
├── VIDEO_ID_2/
│   └── ...
└── transcriptions/
    ├── google/           # Google API transcripts
    └── whisper/          # Whisper transcripts
```

## License

[Specify your license]

## Citation

[Add citation format when dataset is published]

## Contact

[Your contact information]

---

**Status**: Testing Phase  
**Version**: 1.0  
**Last Updated**: January 2026