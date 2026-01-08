# Test database connection
cd database
export $(cat ../.env | xargs)
psql "$DATABASE_URL" -c "SELECT 1;"

# If that works, initialize database
./init_render.sh

# Test API
cd ../api
pip3 install -r requirements.txt
python3 app.py