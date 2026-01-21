# Bengali Audio-Visual Dataset Manager

A web-based system for creating VoxCeleb-style Bengali audio-visual speech datasets with human-in-the-loop quality control.

## Overview

This system provides a streamlined web interface for processing YouTube videos into high-quality audio-visual speech datasets with:
- **Web-Based Workflow**: React frontend with real-time processing feedback
- **Docker Integration**: Self-contained processing with no external dependencies
- **Human Quality Control**: Review processed chunks before approval
- **Domain Classification**: 7 content categories (food, academic, economic, financial, motivational, comedy, sports/gaming)
- **Speaker Tracking**: Links videos to verified speaker identities
- **Automated Processing**: SyncNet filtering, face detection, transcription

## Features

- ✅ Web-based video queue and processing interface
- ✅ Real-time Docker log streaming and progress tracking
- ✅ Chunk review grid with video playback
- ✅ Processing history tracking (database + pipeline cache)
- ✅ PostgreSQL database with domain classification
- ✅ REST API for job management
- ✅ YouTube video fetching with metadata
- ✅ Speaker management tools
- ✅ Short video picker for testing
- ✅ Multiple transcription models (Google/Whisper/Both)

## Quick Start

### Prerequisites

- **OS**: macOS 12+ (Monterey) or Ubuntu 22.04+
- **Docker Desktop**: Running with at least 8GB RAM allocated
- **Docker Image**: `moon1570/bengali-speech-pipeline:latest` (18.2GB)
- **Python**: 3.8+ with venv
- **PostgreSQL**: 12+ (cloud-hosted supported)
- **Disk Space**: 50GB+ recommended

### 1. Clone Repository

```bash
git clone <this-repo>
cd bengali-av-dataset-manager
```

### 2. Verify Docker Setup

```bash
# Pull Docker image (one-time, ~18GB download)
docker pull moon1570/bengali-speech-pipeline:latest

# Verify setup
chmod +x test_docker.sh
./test_docker.sh
```

Expected output:
```
✓ Docker running
✓ Docker image found
✓ Directories created
✓ Volume mounts working
✓ Configuration correct
✅ All tests passed!
```

### 3. Set Up Database

Your database can be cloud-hosted (Render, AWS RDS) or local.

**Option A: Use Existing Cloud Database** (Recommended)
```bash
# Just add DATABASE_URL to .env (already configured if using Render)
# No local setup needed!
```

**Option B: Local PostgreSQL Setup**

**Linux:**
```bash
cd database
chmod +x init_db.sh
./init_db.sh
```

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
cd database
chmod +x init_db.sh
./init_db.sh
```

### 4. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required configuration:**
```bash
# Database (already configured for Render)
DATABASE_URL=postgresql://user:pass@host/database

# YouTube API (get from console.cloud.google.com)
YOUTUBE_API_KEY=your_api_key_here

# Docker image (already set)
DOCKER_IMAGE=moon1570/bengali-speech-pipeline:latest

# Paths (already set, relative to project)
DOWNLOADS_DIR=./data/downloads
OUTPUTS_DIR=./data/outputs
STORAGE_BASE=./data/storage
```

**Note:** No `PIPELINE_DIR` needed! The system is self-contained.

### 5. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install API dependencies
cd api
pip install -r requirements.txt
cd ..

# Install admin tools
cd admin
pip install -r requirements.txt
cd ..

# Install worker dependencies
cd worker
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 6. Add Speakers (Admin)

```bash
cd admin
source ../.venv/bin/activate

# Add speakers interactively
python populate_speakers.py add

# Or import from CSV
python populate_speakers.py import speakers.csv

# Fetch videos (20 per speaker)
python fetch_channel_videos.py all 20
```

### 7. Start the System

```bash
# Quick start (runs both API and frontend)
./start_dev.sh

# Or start individually:
# Terminal 1 - API Server
.venv/bin/python api/app.py

# Terminal 2 - Frontend
cd frontend && npm start
```

Access the web interface at: **http://localhost:3000**

## Web Interface Guide

### Login
1. Navigate to http://localhost:3000
2. Enter your student ID (any ID for testing, e.g., `student_001`)
3. Click "Start Processing"

### Processing Workflow

1. **Preview Stage**
   - View video details, thumbnail, duration
   - Check if video was processed before (shows database + cache status)
   - Select processing preset (strict/balanced/lenient)
   - Choose transcription model (Google/Whisper/Both)
   - Options: Process, Skip, or Search Short Videos

2. **Processing Stage**
   - Real-time Docker logs streaming
   - Progress bar with step indicators
   - Color-coded log messages
   - Processing takes 15-20 minutes per video

3. **Chunk Review Stage** ⭐ NEW
   - Grid view of all processed chunks
   - Video player for each chunk
   - Transcription text display
   - Quality indicators (audio, cropped, bbox, transcription)
   - Statistics: total chunks, passed SyncNet, duration, file size
   - Options: Approve chunks or reject and reprocess

4. **Final Review Stage**
   - Quality assessment sliders (1-5 stars)
   - Issue checkboxes (wrong language, poor audio, etc.)
   - Notes field for detailed feedback
   - Approve or reject entire video

5. **Complete**
   - Video marked as reviewed
   - Automatically loads next video
   - Data saved to database and storage

### Features

**Short Video Picker:**
- Button to find videos under 2 minutes
- Grid view with thumbnails and duration
- Perfect for testing and quick results

**Skip Functionality:**
- Queue system with local caching (5 videos)
- Instant skip without API calls
- Background fetching of more videos

**Processing History:**
- Shows if video already processed
- Displays database status and pipeline cache
- Options to skip or process again anyway

## Architecture

```
┌─────────────────────────────────────────────┐
│         Web Browser (localhost:3000)        │
│  - Video Queue UI                           │
│  - Real-time Progress                       │
│  - Chunk Review Grid                        │
│  - Quality Control                          │
└────────────────┬────────────────────────────┘
                 │ HTTP/WebSocket
                 ▼
┌─────────────────────────────────────────────┐
│      Flask API Server (localhost:5000)      │
│  - Job Queue Management                     │
│  - Processing Orchestration                 │
│  - Video Metadata                           │
│  - Chunk Information                        │
└────────┬────────────────────────────────────┘
         │
         ├──────► PostgreSQL (Cloud/Local)
         │        - Videos, Jobs, Results
         │
         ▼
┌─────────────────────────────────────────────┐
│         Docker Container (Isolated)         │
│  moon1570/bengali-speech-pipeline:latest    │
│  - Volume Mounts:                           │
│    • downloads/ → /app/bengali-pipeline/downloads
│    • outputs/   → /app/bengali-pipeline/outputs
│  - Processing Pipeline:                     │
│    1. Audio segmentation                    │
│    2. Face detection & tracking             │
│    3. SyncNet filtering                     │
│    4. Transcription (Google/Whisper)        │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│          Local File System                  │
│  data/                                      │
│  ├── downloads/  ← Source videos            │
│  ├── outputs/    ← Docker results           │
│  └── storage/    ← Approved chunks          │
└─────────────────────────────────────────────┘
```

**Key Design:**
- ✅ Self-contained: No external pipeline directory needed
- ✅ Portable: Docker handles all processing dependencies
- ✅ Simple: Volume mounts connect local dirs to container
- ✅ Scalable: Can run on any machine with Docker

## Docker Details

### Image Information
- **Name**: `moon1570/bengali-speech-pipeline:latest`
- **Size**: 18.2GB
- **Platform**: linux/amd64 (works on macOS ARM via emulation)
- **Contents**: Complete processing pipeline with all dependencies

### How It Works

The worker script runs Docker with volume mounts:

```bash
docker run --rm \
  -v $(pwd)/data/downloads:/app/bengali-pipeline/downloads \
  -v $(pwd)/data/outputs:/app/bengali-pipeline/outputs \
  -e SYNCNET_REPO=/app/syncnet_python \
  -e CURRENT_REPO=/app/bengali-pipeline \
  moon1570/bengali-speech-pipeline:latest \
  /app/bengali-pipeline/complete_pipeline.sh VIDEO_ID \
  --preset medium --transcription-model google
```

### Troubleshooting Docker

```bash
# Verify image exists
docker images | grep bengali

# Test image manually
docker run --rm moon1570/bengali-speech-pipeline:latest ls /app

# Check Docker resources (needs 8GB+ RAM)
# Docker Desktop → Settings → Resources

# Re-pull image if corrupted
docker pull moon1570/bengali-speech-pipeline:latest --platform linux/amd64
```

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker documentation.
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
bengali-av-dataset-manager/
├── api/                  # Flask REST API server
│   ├── app.py           # Main API with job queue, video endpoints
│   └── config.py        # Configuration management
├── frontend/            # React web interface
│   ├── src/
│   │   ├── components/  # VideoQueue, Dashboard, Login
│   │   └── api.js       # API client
│   └── package.json
├── worker/              # Background video processing
│   └── process_video.py # Docker orchestration
├── admin/               # Management tools
│   ├── populate_speakers.py      # Speaker management
│   └── fetch_channel_videos.py   # YouTube video fetching
├── database/            # PostgreSQL schema
│   ├── schema.sql       # Database structure
│   └── init_db.sh       # Setup script
├── data/                # Local storage (created automatically)
│   ├── downloads/       # Downloaded videos
│   ├── outputs/         # Docker processing results
│   └── storage/         # Final approved chunks
├── test_docker.sh       # Docker setup verification
├── start_dev.sh         # Quick start script
└── .env                 # Configuration (copy from .env.example)
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with student ID
- `POST /api/auth/logout` - Logout current session

### Video Management
- `GET /api/videos/next` - Get next video to process (with queue)
- `GET /api/videos/short` - Get short videos (for testing)
- `GET /api/videos/{id}/check-processed` - Check processing history
- `GET /api/videos/{id}/chunks` - Get processed chunks for review
- `POST /api/videos/{id}/process-local` - Start processing

### Processing
- `GET /api/videos/{id}/processing-status` - Real-time status/logs
- `POST /api/videos/{id}/submit-results` - Submit processing results
- `POST /api/videos/{id}/review` - Submit quality review

### Statistics
- `GET /api/stats` - Overall dataset statistics
- `GET /api/stats/domains` - Domain breakdown
- `GET /api/health` - System health check

### Static Files
- `GET /storage/{video_id}/{filename}` - Serve processed video chunks

## Configuration

### Environment Variables (.env)

```bash
# ============================================================================
# DATABASE (Cloud or Local PostgreSQL)
# ============================================================================
DATABASE_URL=postgresql://user:password@host:5432/database

# ============================================================================
# API SERVER
# ============================================================================
API_HOST=0.0.0.0
API_PORT=5000
DEBUG=True
SECRET_KEY=your_secret_key_here

# ============================================================================
# YOUTUBE API
# ============================================================================
# Get from: https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=your_youtube_api_key

# ============================================================================
# DOCKER & PATHS (Self-Contained - No External Dependencies!)
# ============================================================================
DOCKER_IMAGE=moon1570/bengali-speech-pipeline:latest
DOWNLOADS_DIR=./data/downloads
OUTPUTS_DIR=./data/outputs
STORAGE_BASE=./data/storage

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================
DEFAULT_PRESET=balanced

# Preset thresholds
STRICT_SYNC_THRESHOLD=8.0
BALANCED_SYNC_THRESHOLD=6.5
LENIENT_SYNC_THRESHOLD=5.0

# ============================================================================
# FRONTEND
# ============================================================================
REACT_APP_API_URL=http://localhost:5000
```

**Important Notes:**
- ✅ No `PIPELINE_DIR` needed - system is self-contained!
- ✅ All paths are relative to project root
- ✅ Works on any machine with Docker installed
- ✅ Database can be cloud-hosted (Render, AWS, etc.)

### Processing Presets

| Preset | SyncNet Threshold | Face Threshold | Use Case |
|--------|------------------|----------------|----------|
| **strict** | 8.0 | 0.95 | Highest quality, lower retention |
| **balanced** | 6.5 | 0.90 | Good quality, ~50-70% retention |
| **lenient** | 5.0 | 0.80 | Maximum retention, lower quality |

## Speaker CSV Format

```csv
speaker_id,channel_id,channel_name,speaker_name,domain,gender,nationality
SPK001,UCxxxxx,Channel Name,Speaker Name,food_blogger,M,BD
SPK002,UCyyyyy,Another Channel,Another Speaker,academician,F,BD
```

## Processing Pipeline

The complete pipeline runs inside Docker:

```
1. Download Video
   ↓ yt-dlp downloads from YouTube
   ↓ Saved to: data/downloads/VIDEO_ID.mp4

2. Docker Processing (15-20 minutes)
   ↓ Volume mount: downloads/ → /app/bengali-pipeline/downloads
   ↓ Volume mount: outputs/ → /app/bengali-pipeline/outputs
   ↓
   ├─► Audio Segmentation
   │   - Detects speech vs silence
   │   - Creates initial chunks
   │
   ├─► Face Detection & Tracking
   │   - Detects faces in video
   │   - Tracks face across frames
   │   - Filters chunks without faces
   │
   ├─► SyncNet Filtering
   │   - Checks audio-visual synchronization
   │   - Filters chunks with poor sync (<6.5)
   │   - Keeps only well-synchronized chunks
   │
   └─► Transcription
       - Google Speech-to-Text (default)
       - OpenAI Whisper (optional)
       - Bengali language support

3. Results Collection
   ↓ Outputs to: data/outputs/VIDEO_ID/
   ↓
   ├─► video_normal/     # Passed chunks
   ├─► video_cropped/    # Face-cropped 224x224
   ├─► video_bbox/       # With face bounding boxes
   ├─► audio/            # Extracted audio WAV
   └─► google_transcription/  # Text transcripts

4. Human Review (Web UI)
   ↓ User reviews chunk grid
   ↓ Quality assessment
   ↓ Approve or reject

5. Final Storage
   ↓ Approved chunks → data/storage/VIDEO_ID/
   ↓ Metadata → PostgreSQL database
   ✓ Complete!
```

## Quality Metrics

Target metrics for dataset quality:

| Metric | Target | Description |
|--------|--------|-------------|
| **Sync Score** | >6.5 (balanced) | Audio-visual synchronization quality |
| **Face Confidence** | >0.90 | Face detection confidence |
| **Retention Rate** | 50-70% | % of chunks passing all filters |
| **Transcription Coverage** | >85% | % of chunks with valid transcription |
| **Chunk Duration** | 2-10 seconds | Optimal chunk length range |

### Processing Statistics

After processing, you'll see:
- Total chunks created
- Chunks passed SyncNet
- Usable duration (seconds)
- Total file size (MB)
- Files per chunk: video, audio, cropped, bbox, transcription

## Monitoring

### Web Interface
Visit http://localhost:3000 to see:
- Current video being processed
- Real-time logs and progress
- Queue status
- Processing history

### Check Database Status
```bash
# Overall statistics
curl http://localhost:5000/api/stats | jq

# Domain breakdown
curl http://localhost:5000/api/stats/domains | jq
```

### PostgreSQL Queries

```bash
# Connect to database
psql $DATABASE_URL

# Check video statuses
SELECT status, COUNT(*) 
FROM processing_jobs 
GROUP BY status;

# Top speakers by videos processed
SELECT s.speaker_name, COUNT(v.video_id) as video_count
FROM speakers s
JOIN videos v ON s.speaker_id = v.speaker_id
GROUP BY s.speaker_name
ORDER BY video_count DESC
LIMIT 10;

# Recent processing results
SELECT 
    v.title,
    pr.chunks_created,
    pr.chunks_passed_sync,
    pr.usable_duration_seconds,
    pj.completed_at
FROM processing_results pr
JOIN processing_jobs pj ON pr.job_id = pj.job_id
JOIN videos v ON pj.video_id = v.video_id
ORDER BY pj.completed_at DESC
LIMIT 10;
```

## Troubleshooting

### Docker Issues

**Image not found:**
```bash
docker pull moon1570/bengali-speech-pipeline:latest
docker images | grep bengali  # Verify it's there
```

**Platform warning (Mac ARM):**
```
WARNING: The requested image's platform (linux/amd64) does not match...
```
This is normal on Apple Silicon Macs. Docker handles emulation automatically.

**Container exits immediately:**
```bash
# Check Docker logs
docker ps -a  # Find container ID
docker logs <container_id>

# Test image manually
docker run --rm moon1570/bengali-speech-pipeline:latest ls /app
```

**Volume mount permission denied:**
```bash
# On Mac: Docker Desktop → Settings → Resources → File Sharing
# Add: /Users/your-username/path/to/project

# On Linux: Check file permissions
ls -la data/
chmod -R 755 data/
```

### API/Frontend Issues

**API won't start:**
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill existing process
kill -9 <PID>

# Check .env file exists
ls -la .env

# Verify database connection
.venv/bin/python -c "
from api.app import get_db
conn = get_db()
print('✓ Database connected')
"
```

**Frontend won't start:**
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

**CORS errors:**
- Verify API is running on port 5000
- Check `REACT_APP_API_URL` in frontend/.env
- API should allow `http://localhost:3000` (already configured)

### Processing Issues

**Video download fails:**
```bash
# Update yt-dlp
.venv/bin/pip install --upgrade yt-dlp

# Test download manually
.venv/bin/yt-dlp "https://youtube.com/watch?v=VIDEO_ID" -o "test.mp4"
```

**Processing timeout:**
- Increase Docker memory: Docker Desktop → Settings → Resources → Memory (8GB+)
- Check video length: Start with short videos (<2 minutes) for testing
- Monitor `docker stats` during processing

**No chunks created:**
- Check video has clear speech and faces
- Try lenient preset for testing
- View Docker logs for specific errors

**Database Connection Failed:**

**Cloud Database:**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check if DATABASE_URL is correct in .env
echo $DATABASE_URL
```

**Local Database:**

Linux:
```bash
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

macOS:
```bash
brew services list | grep postgresql
brew services restart postgresql@14
```

### Common Error Messages

**"Processing failed: 2026-01-15 14:19:49,015 - INFO - [Docker] ✅ already processed. Skipping."**
- Video was previously processed and cached
- UI now shows warning with option to skip or process again
- Or manually remove from: `data/outputs/processed.json`

**"Cannot read properties of undefined (reading 'toFixed')"**
- Fixed: Results object was missing fields
- Update to latest version for safety checks

**"No JSON results found in output"**
- Fixed: Multi-line JSON parsing issue resolved
- Worker output now properly parsed

## Development

### Running in Development Mode

```bash
# Terminal 1: API with auto-reload
.venv/bin/python api/app.py

# Terminal 2: Frontend with hot reload
cd frontend && npm start

# Terminal 3: Watch logs
tail -f worker/worker.log
```

### Testing with Short Videos

1. Click "🔍 Search Short Videos" in UI
2. Select video under 2 minutes
3. Process with balanced preset
4. Review chunks quickly

### Code Structure

**Backend (Flask):**
- `api/app.py` - Main API server
  - `/api/videos/next` - Video queue logic
  - `/api/videos/{id}/process-local` - Triggers worker
  - `/api/videos/{id}/processing-status` - Real-time polling
  - `/api/videos/{id}/chunks` - Chunk information for review

**Frontend (React):**
- `frontend/src/components/VideoQueue.js` - Main workflow component
  - STAGES: LOADING → PREVIEW → PROCESSING → CHUNK_REVIEW → REVIEWING → COMPLETE
  - Real-time log streaming and progress updates
  - Chunk review grid with video players

**Worker (Python):**
- `worker/process_video.py` - Docker orchestration
  - Downloads video with yt-dlp
  - Runs Docker container with volume mounts
  - Streams logs in real-time
  - Collects and reports results

### Adding New Features

**New API endpoint:**
1. Add route in `api/app.py`
2. Add function in `frontend/src/api.js`
3. Call from React component

**New processing option:**
1. Add parameter in `worker/process_video.py`
2. Add UI control in `VideoQueue.js` PREVIEW stage
3. Pass to `/api/videos/{id}/process-local`

## Migration from Old Setup

If you had the old system with `PIPELINE_DIR`:

1. **Pull latest code:**
   ```bash
   git pull origin main
   ```

2. **Update .env:**
   ```bash
   # Remove this line:
   # PIPELINE_DIR="/path/to/..."
   
   # Add these lines:
   OUTPUTS_DIR=./data/outputs
   DOCKER_IMAGE=moon1570/bengali-speech-pipeline:latest
   ```

3. **Verify Docker:**
   ```bash
   ./test_docker.sh
   ```

4. **Done!** The pipeline directory is no longer needed.

**Changes:**
- ✅ No more file copying between repos
- ✅ No more external path configuration
- ✅ Docker runs with volume mounts
- ✅ Results go directly to `data/outputs/`

## Contributing

### For Students Processing Videos:
1. Get login credentials from project lead
2. Visit http://localhost:3000
3. Login with your student ID
4. Follow the web interface workflow
5. Report any issues via GitHub Issues

### For Developers:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (especially Docker integration)
5. Submit a pull request

## Dataset Output

Final approved dataset structure:

```
data/storage/
├── VIDEO_ID_1/
│   ├── video_normal/          # Original quality chunks
│   │   ├── chunk_000.mp4
│   │   ├── chunk_001.mp4
│   │   └── ...
│   ├── video_cropped/         # Face-cropped 224x224
│   │   ├── chunk_000.mp4
│   │   └── ...
│   ├── video_bbox/            # With face bounding boxes
│   │   ├── chunk_000_with_bboxes.mp4
│   │   └── ...
│   ├── audio/                 # Extracted audio WAV
│   │   ├── chunk_000.wav
│   │   └── ...
│   └── google_transcription/  # Bengali text
│       ├── chunk_000.txt
│       └── ...
├── VIDEO_ID_2/
│   └── ...
└── processed.json             # Processing cache
```

### Metadata Structure

**PostgreSQL Database:**
- `speakers` - Speaker information and channel links
- `videos` - Video metadata (title, duration, URL, domain)
- `processing_jobs` - Processing status tracking
- `processing_results` - Quality metrics and statistics
- `quality_reviews` - Human quality assessments

## System Requirements

### Minimum
- **CPU**: 4 cores (8 recommended)
- **RAM**: 8GB (16GB recommended)
- **Storage**: 50GB free space
- **Docker**: 8GB memory allocation
- **Network**: 10 Mbps for video downloads

### Recommended
- **CPU**: 8+ cores (for faster processing)
- **RAM**: 16-32GB
- **Storage**: 100-500GB SSD
- **Docker**: 12-16GB memory allocation
- **Network**: 50+ Mbps
- **GPU**: Optional (CUDA for faster SyncNet - requires image rebuild)

### Processing Time Estimates
- **Short video (30-60s)**: 5-10 minutes
- **Medium video (2-5 min)**: 15-25 minutes
- **Long video (10+ min)**: 30-60 minutes

*Times vary based on CPU speed, video complexity, and preset strictness.*

## Known Limitations

- Platform warning on Mac ARM (cosmetic, works fine)
- Large Docker image size (18.2GB - includes all models)
- Processing is CPU-bound (GPU support requires image rebuild)
- YouTube rate limiting (use API key for higher limits)

## Roadmap

- [ ] Batch processing mode
- [ ] Export to VoxCeleb format
- [ ] Advanced quality metrics dashboard
- [ ] Speaker verification integration
- [ ] Multi-language support (Hindi, Tamil, etc.)
- [ ] GPU acceleration support
- [ ] Cloud storage integration (S3, GCS)

## License

[Specify your license]

## Citation

If you use this dataset in your research, please cite:

```bibtex
@dataset{bengali_av_dataset_2026,
  title={Bengali Audio-Visual Speech Dataset},
  author={[Your Name/Institution]},
  year={2026},
  note={Created using Bengali AV Dataset Manager},
  url={[Your URL]}
}
```

## Acknowledgments

- Bengali Speech Audio-Visual Dataset Pipeline
- SyncNet Python implementation
- VoxCeleb dataset format inspiration
- React and Flask communities

## Contact

- **Project Lead**: [Your Name]
- **Email**: [Your Email]
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: See [DOCKER_SETUP.md](DOCKER_SETUP.md) and [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)

## Quick Links

- 🐳 [Docker Setup Guide](DOCKER_SETUP.md)
- 📝 [Refactoring Summary](REFACTORING_SUMMARY.md) - Details on PIPELINE_DIR removal
- 💾 [Database Schema](database/schema.sql)
- 🔧 [API Documentation](#api-endpoints)
- 🎨 [Web Interface Guide](#web-interface-guide)

---

**Status**: Production Ready ✅  
**Version**: 2.0 (Self-Contained Docker Edition)  
**Last Updated**: January 15, 2026

**What's New in 2.0:**
- ✨ Complete web-based workflow with React UI
- 🔄 Real-time processing with live log streaming
- 🎬 Chunk review grid with video playback
- 🐳 Self-contained Docker architecture (no PIPELINE_DIR!)
- 📊 Processing history tracking
- ⚡ Short video picker for testing
- 🎯 Human-in-the-loop quality control
- 🚀 Simplified setup - works anywhere with Docker