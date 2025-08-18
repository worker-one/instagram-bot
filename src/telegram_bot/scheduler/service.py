import logging
from dotenv import load_dotenv, find_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import os

# Environment variables
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

# Set up logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.WARN)
logger = logging.getLogger(__name__)


load_dotenv(find_dotenv(usecwd=True))

# Check if any of the required environment variables are not set
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    logger.warning("One or more postgresql database environment variables are not set. Using SQLite instead.")
    DATABASE_URL = "sqlite:///instagram-bot.db"
    logger.info(f"Using {DATABASE_URL} for job store")
else:
    # Construct the database URL for PostgreSQL
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    logger.info(f"Using {DB_HOST} for job store")
    
# Create a single instance of the scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=DATABASE_URL)
}

job_defaults = {
    'max_instances': 1,  # Only one instance of each job can run at a time
    # If the clock crashes, make sure to run the missed job if it's up to this much late.
    'misfire_grace_time': 60 * 60,
    'coalesce': True,  # Prevent jobs being run being run in parallel if the server was down for a while.
}

scheduler = BackgroundScheduler(jobstores=jobstores, job_defaults=job_defaults)

from .tasks import send_trend_notifications, check_balance

# scheduler.add_job(remove_past_scheduled_games, 'cron', hour=0)  # Runs daily at midnight

def init_scheduler():
    """Initialize the scheduler and start it"""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")

        # Schedule trend notifications - runs every 270 minutes
        scheduler.add_job(
            send_trend_notifications,
            'interval',
            minutes=200,
            id='trend_notifications',
            replace_existing=True
        )
        logger.info("Trend notifications scheduled to run every 200 minutes")

        # Schedule balance check - runs every 4 minutes
        scheduler.add_job(
            check_balance,
            'interval',
            minutes=30,
            id='balance_check',
            replace_existing=True
        )
        logger.info("Balance check scheduled to run every 4 minutes")
