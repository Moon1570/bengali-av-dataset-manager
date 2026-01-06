# Bengali Audio-Visual Dataset Creation Project
## Complete Implementation Plan

**Project Goal:** Create a VoxCeleb-style Bengali audio-visual speech dataset with domain classification and distributed processing.

**Target:** 1000+ hours of data across 50+ speakers in 7 domains

---

## Phase 1: Foundation Setup ✅ (Completed in Chat)

### ✅ 1.1 Database Design (DONE)
- [x] PostgreSQL schema with domain classification
- [x] Tables: speakers, videos, processing_jobs, processing_results, workers, quality_validations
- [x] Domain types: food_blogger, academician, economic, financial, motivational_speaker, comedian, sports_and_gaming
- [x] Indexes and views for performance
- [x] Triggers for automatic stats updates

**Files Created:**
- `database/schema.sql`
- `database/init_db.sh`

### ✅ 1.2 API Server (DONE)
- [x] Job queue management API
- [x] Atomic job claiming with SKIP LOCKED
- [x] Worker coordination
- [x] Statistics endpoints
- [x] Domain-based filtering
- [x] Automatic retry logic

**Files Created:**
- `api/app.py`
- `api/config.py`
- `api/requirements.txt`

### ✅ 1.3 Worker Scripts (DONE)
- [x] Video download (yt-dlp)
- [x] Pipeline processing integration
- [x] Results collection
- [x] Storage upload
- [x] Error handling and reporting
- [x] Worker setup script

**Files Created:**
- `worker/process_video.py`
- `worker/config.py`
- `worker/setup_worker.sh`
- `worker/requirements.txt`

### ✅ 1.4 Admin Tools (DONE - Partial)
- [x] Speaker population script
- [x] Video fetching from YouTube
- [x] Domain-based management
- [ ] Quality dashboard (TO DO)
- [ ] Dataset quality reports (TO DO)

**Files Created:**
- `admin/populate_speakers.py`
- `admin/fetch_channel_videos.py`

---

## Phase 2: Testing & Validation 🔄 (NEXT - Step by Step)

### 📋 2.1 Database Setup & Testing
**Objective:** Verify database works correctly

#### Steps:
1. **Install PostgreSQL**
   ```bash
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib
   ```

2. **Initialize Database**
   ```bash
   cd database
   chmod +x init_db.sh
   ./init_db.sh
   ```

3. **Test Database Connection**
   ```bash
   psql -U dataset_admin -d voxceleb_dataset -c "SELECT COUNT(*) FROM speakers;"
   ```

#### Success Criteria:
- [ ] Database created without errors
- [ ] All 7 tables exist
- [ ] Can connect and query
- [ ] Triggers working

#### Test Commands:
```bash
# List all tables
psql -U dataset_admin -d voxceleb_dataset -c "\dt"

# Check domain enum
psql -U dataset_admin -d voxceleb_dataset -c "SELECT unnest(enum_range(NULL::domain_type));"

# Verify admin worker exists
psql -U dataset_admin -d voxceleb_dataset -c "SELECT * FROM workers;"
```

---

### 📋 2.2 API Server Setup & Testing
**Objective:** Verify API server responds correctly

#### Steps:
1. **Install Dependencies**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

2. **Create .env File**
   ```bash
   cat > .env << 'EOF'
   DB_HOST=localhost
   DB_NAME=voxceleb_dataset
   DB_USER=dataset_admin
   DB_PASSWORD=changeme123
   DB_PORT=5432
   API_HOST=0.0.0.0
   API_PORT=5000
   DEBUG=True
   EOF
   ```

3. **Start API Server**
   ```bash
   python app.py
   ```

4. **Test API Endpoints** (in new terminal)
   ```bash
   # Health check
   curl http://localhost:5000/api/health
   
   # Get stats (should be empty)
   curl http://localhost:5000/api/stats
   
   # Try to claim job (should return 404 - no jobs)
   curl -X POST http://localhost:5000/api/jobs/claim \
     -H "Content-Type: application/json" \
     -d '{"worker_id": "test_worker"}'
   ```

#### Success Criteria:
- [ ] API starts without errors
- [ ] Health endpoint returns "healthy"
- [ ] Stats endpoint returns data
- [ ] Job claim returns "No jobs available"

---

### 📋 2.3 Populate Test Speakers
**Objective:** Add 5-10 test speakers from different domains

#### Steps:
1. **Install Admin Tools Dependencies**
   ```bash
   cd admin
   pip install -r requirements.txt
   ```

2. **Get YouTube API Key**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Create project
   - Enable YouTube Data API v3
   - Create API key
   - Copy key

3. **Set API Key**
   ```bash
   export YOUTUBE_API_KEY='your-api-key-here'
   ```

4. **Create Test Speakers CSV**
   ```bash
   cat > test_speakers.csv << 'EOF'
   speaker_id,channel_id,channel_name,speaker_name,domain,gender,nationality
   SPK001,UC_channel_id_1,Food Channel,Chef Name,food_blogger,M,BD
   SPK002,UC_channel_id_2,Tech Channel,Tech Person,academician,F,BD
   SPK003,UC_channel_id_3,Finance Channel,Finance Expert,financial,M,BD
   EOF
   ```
   
   **Note:** Replace `UC_channel_id_X` with real YouTube channel IDs

5. **Import Speakers**
   ```bash
   python populate_speakers.py import test_speakers.csv
   ```

6. **Verify Import**
   ```bash
   python populate_speakers.py list
   ```

#### Success Criteria:
- [ ] Speakers imported successfully
- [ ] Can see speakers with `list` command
- [ ] Domains assigned correctly

---

### 📋 2.4 Fetch Test Videos
**Objective:** Populate database with 10-20 videos per speaker

#### Steps:
1. **Fetch Videos for All Speakers**
   ```bash
   python fetch_channel_videos.py all 10
   ```

2. **Check Database**
   ```bash
   psql -U dataset_admin -d voxceleb_dataset -c "
   SELECT s.speaker_id, s.speaker_name, s.domain, COUNT(v.video_id) as video_count
   FROM speakers s
   LEFT JOIN videos v ON s.speaker_id = v.speaker_id
   GROUP BY s.speaker_id, s.speaker_name, s.domain;
   "
   ```

3. **Check Jobs Created**
   ```bash
   curl http://localhost:5000/api/stats | jq
   ```

#### Success Criteria:
- [ ] Videos fetched for each speaker
- [ ] Jobs created in 'pending' status
- [ ] API stats show pending jobs

---

### 📋 2.5 Worker Setup & Single Job Test
**Objective:** Process one video end-to-end

#### Steps:
1. **Setup Worker**
   ```bash
   cd worker
   chmod +x setup_worker.sh
   ./setup_worker.sh
   ```
   
   Enter when prompted:
   - Worker ID: `test_worker_001`
   - API URL: `http://localhost:5000`
   - Pipeline directory: `/path/to/bengali-pipeline`
   - Storage base: `./test_storage`

2. **Create Storage Directory**
   ```bash
   mkdir -p ./test_storage
   ```

3. **Run Single Job**
   ```bash
   python process_video.py
   ```

4. **Monitor Progress**
   Watch the logs for:
   - Job claimed
   - Video downloading
   - Processing stages
   - Upload complete
   - Job reported

5. **Verify Results**
   ```bash
   # Check storage
   ls -lh ./test_storage/
   
   # Check database
   psql -U dataset_admin -d voxceleb_dataset -c "
   SELECT * FROM processing_results ORDER BY created_at DESC LIMIT 1;
   "
   
   # Check API stats
   curl http://localhost:5000/api/stats | jq
   ```

#### Success Criteria:
- [ ] Job claimed successfully
- [ ] Video downloaded
- [ ] Processing completed
- [ ] Results uploaded to storage
- [ ] Database updated with results
- [ ] Job status = 'completed'

---

### 📋 2.6 Multi-Worker Test
**Objective:** Test 2-3 workers processing simultaneously

#### Steps:
1. **Setup 2 More Workers**
   ```bash
   # Terminal 2
   cd worker
   export WORKER_ID=test_worker_002
   python process_video.py
   
   # Terminal 3
   cd worker  
   export WORKER_ID=test_worker_003
   python process_video.py
   ```

2. **Monitor for 30 Minutes**
   - Watch for duplicate processing
   - Check for conflicts
   - Monitor storage

3. **Check Results**
   ```bash
   # Worker performance
   psql -U dataset_admin -d voxceleb_dataset -c "
   SELECT worker_id, jobs_completed, jobs_failed, 
          ROUND(avg_processing_time_minutes::numeric, 2) as avg_time
   FROM workers;
   "
   
   # Domain distribution
   curl http://localhost:5000/api/stats/domains | jq
   ```

#### Success Criteria:
- [ ] No duplicate processing
- [ ] All workers claiming jobs
- [ ] No database conflicts
- [ ] Jobs completing successfully

---

## Phase 3: UI Development 🎨 (Next Priority)

### 📋 3.1 Quality Dashboard
**Objective:** Web UI for monitoring and quality control

#### Features to Implement:
1. **Overview Page**
   - Total stats (videos, hours, chunks)
   - Domain distribution chart
   - Processing rate graph
   - Worker status

2. **Worker Management**
   - Active workers list
   - Performance metrics
   - Job assignment history

3. **Quality Control**
   - Random sample validator
   - Flagged videos review
   - Manual quality scoring

4. **Dataset Browser**
   - Search by speaker/domain
   - Filter by quality metrics
   - Download chunks

#### Technology Stack:
- Backend: Flask (existing API)
- Frontend: React + Tailwind CSS
- Charts: Recharts
- State: React Query

#### Files to Create:
```
frontend/
├── package.json
├── src/
│   ├── App.jsx
│   ├── components/
│   │   ├── Dashboard.jsx
│   │   ├── WorkerStats.jsx
│   │   ├── DomainChart.jsx
│   │   ├── QualityValidator.jsx
│   │   └── DatasetBrowser.jsx
│   ├── api/
│   │   └── client.js
│   └── styles/
│       └── main.css
└── public/
    └── index.html
```

---

### 📋 3.2 Admin Panel
**Objective:** Speaker and video management UI

#### Features:
1. **Speaker Management**
   - Add/edit speakers
   - Assign domains
   - View speaker stats

2. **Video Management**
   - Fetch videos from channels
   - Mark validation candidates
   - Cancel/retry jobs

3. **System Health**
   - Database status
   - API health
   - Storage usage
   - Error logs

---

## Phase 4: Production Deployment 🚀

### 📋 4.1 Server Setup
- [ ] Set up Linux server (Ubuntu 22.04)
- [ ] Install PostgreSQL
- [ ] Configure firewall
- [ ] Set up SSL certificates
- [ ] Configure nginx reverse proxy

### 📋 4.2 Production Database
- [ ] Create production database
- [ ] Set strong passwords
- [ ] Configure backups (daily)
- [ ] Set up monitoring

### 📋 4.3 API Deployment
- [ ] Use gunicorn for production
- [ ] Set up systemd service
- [ ] Configure logging
- [ ] Set up monitoring (Prometheus)

### 📋 4.4 Worker Distribution
- [ ] Package worker scripts
- [ ] Create student documentation
- [ ] Distribute to 10+ students
- [ ] Monitor for issues

---

## Phase 5: Scale to Production 📈

### 📋 5.1 Speaker Collection (Target: 50+ speakers)
**Domain Distribution Goal:**
- Food Blogger: 10 speakers
- Academician: 8 speakers
- Economic: 6 speakers
- Financial: 6 speakers
- Motivational Speaker: 8 speakers
- Comedian: 7 speakers
- Sports/Gaming: 5 speakers

#### Tasks:
- [ ] Research Bengali YouTube channels
- [ ] Create speaker list per domain
- [ ] Verify channel quality
- [ ] Import to database
- [ ] Fetch initial videos (20-30 per speaker)

### 📋 5.2 Processing at Scale
- [ ] Process 1000+ videos
- [ ] Monitor quality metrics
- [ ] Handle failures
- [ ] Optimize storage

### 📋 5.3 Quality Assurance
- [ ] Validate 100 random samples
- [ ] Create gold standard validation set
- [ ] Inter-annotator agreement checks
- [ ] Domain balance verification

---

## Phase 6: Dataset Finalization 📦

### 📋 6.1 Dataset Documentation
- [ ] Create DATASET_CARD.md
- [ ] Document collection methodology
- [ ] Include statistics
- [ ] Specify license

### 📋 6.2 Dataset Release
- [ ] Archive final data
- [ ] Create download scripts
- [ ] Publish documentation
- [ ] Release announcement

---

## Key Metrics to Track

### Quality Metrics
- Average sync score: Target >7.0
- Average face presence: Target >0.90
- Chunk retention rate: 50-70%
- Transcription coverage: >85%

### Scale Metrics
- Total hours: Target 1000+ hours
- Total speakers: Target 50+ speakers
- Total chunks: Target 100,000+ chunks
- Domain balance: No domain >20% of total

### Processing Metrics
- Videos/day: Target 50+
- Avg processing time: <30 min/video
- Failure rate: <10%
- Worker efficiency: >80%

---

## File Structure Summary

```
bengali-dataset-manager/
├── PROJECT_PLAN.md              (this file)
├── README.md                    (to create)
├── .env.example                 (to create)
├── database/
│   ├── schema.sql              ✅
│   └── init_db.sh              ✅
├── api/
│   ├── app.py                  ✅
│   ├── config.py               ✅
│   └── requirements.txt        ✅
├── worker/
│   ├── process_video.py        ✅
│   ├── config.py               ✅
│   ├── setup_worker.sh         ✅
│   └── requirements.txt        ✅
├── admin/
│   ├── populate_speakers.py    ✅
│   ├── fetch_channel_videos.py ✅
│   ├── quality_dashboard.py    (to create)
│   ├── dataset_quality_report.py (to create)
│   └── requirements.txt        (to create)
├── frontend/                    (to create)
│   ├── package.json
│   ├── src/
│   └── public/
└── docs/
    ├── DEPLOYMENT.md            (to create)
    ├── STUDENT_GUIDE.md         (to create)
    └── API_REFERENCE.md         (to create)
```

---

## Next Immediate Steps (Priority Order)

1. ✅ **Create all base files** (Done in chat)
2. 🔄 **Test database setup** (Section 2.1)
3. 🔄 **Test API server** (Section 2.2)
4. 🔄 **Add test speakers** (Section 2.3)
5. 🔄 **Fetch test videos** (Section 2.4)
6. 🔄 **Process one video** (Section 2.5)
7. 🔄 **Multi-worker test** (Section 2.6)
8. ⏳ **Build UI dashboard** (Section 3.1)
9. ⏳ **Deploy to server** (Section 4.1-4.3)
10. ⏳ **Distribute to students** (Section 4.4)

---

## Commands Quick Reference

### Database
```bash
# Initialize
cd database && ./init_db.sh

# Connect
psql -U dataset_admin -d voxceleb_dataset

# Check stats
psql -U dataset_admin -d voxceleb_dataset -c "SELECT * FROM dataset_overview;"
```

### API
```bash
# Start server
cd api && python app.py

# Health check
curl http://localhost:5000/api/health

# Get stats
curl http://localhost:5000/api/stats
```

### Admin
```bash
# Add speakers
python populate_speakers.py add

# Import CSV
python populate_speakers.py import speakers.csv

# Fetch videos
python fetch_channel_videos.py all 20

# Fetch for domain
python fetch_channel_videos.py domain food_blogger 30
```

### Worker
```bash
# Setup
cd worker && ./setup_worker.sh

# Process single job
python process_video.py

# Run continuously
while true; do python process_video.py; sleep 10; done
```

---

## Troubleshooting Guide

### Database Issues
**Problem:** Can't connect to database
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Restart if needed
sudo systemctl restart postgresql
```

**Problem:** Permission denied
```bash
# Check user privileges
psql -U postgres -c "SELECT * FROM pg_user WHERE usename='dataset_admin';"
```

### API Issues
**Problem:** Port already in use
```bash
# Find and kill process
lsof -ti:5000 | xargs kill -9
```

**Problem:** Database connection failed
- Check DB_PASSWORD in .env
- Verify database is running
- Check firewall settings

### Worker Issues
**Problem:** yt-dlp download fails
```bash
# Update yt-dlp
pip install --upgrade yt-dlp
```

**Problem:** Docker not found
```bash
# Install Docker
sudo apt-get install docker.io
sudo usermod -aG docker $USER
```

**Problem:** Storage permission denied
```bash
# Check permissions
ls -ld /mnt/dataset_storage

# Fix permissions
sudo chown -R $USER:$USER /mnt/dataset_storage
```

---

## Contact & Support

For issues or questions:
1. Check logs in respective directories
2. Review troubleshooting guide
3. Check database for error messages
4. Contact project lead

---

**Last Updated:** January 2026  
**Version:** 1.0  
**Status:** Testing Phase