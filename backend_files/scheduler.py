import schedule
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_recent():
    logger.info("🔄 Updating recent papers...")
    subprocess.run(["python3", "fill_recent_db.py"])  

def update_daily():
    logger.info("🔄 Updating daily papers...")
    subprocess.run(["python3", "fill_daily_db.py"])

def update_weekly():
    logger.info("🔄 Updating weekly papers...")
    subprocess.run(["python3", "fill_weekly_db.py"])

# Schedule updates
schedule.every(2).hours.do(update_recent)
schedule.every().day.at("04:00").do(update_daily)
schedule.every().monday.at("05:00").do(update_weekly)

def run_scheduled_tasks():
    """Run all due scheduled tasks once and log the process."""
    logger.info("🚀 Running scheduled tasks...")
    schedule.run_pending()
    logger.info("✅ Scheduler executed pending tasks.")
