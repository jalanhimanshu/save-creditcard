import time
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from agents import run_daily_market_sync, run_redemption_offer_sync, run_twitter_sync

def job_market_sync():
    print(f"\n--- Running Market Sync at {datetime.datetime.now()} ---")
    run_daily_market_sync()

def job_redemption_sync():
    print(f"\n--- Running Redemption Sync at {datetime.datetime.now()} ---")
    run_redemption_offer_sync()

def job_twitter_sync():
    print(f"\n--- Running Hourly Twitter Sync at {datetime.datetime.now()} ---")
    run_twitter_sync()

if __name__ == '__main__':
    print("Starting SavePoints Autonomous Agent Scheduler...")
    
    scheduler = BackgroundScheduler()
    
    # Schedule Market Sync daily at midnight
    scheduler.add_job(job_market_sync, 'cron', hour=0, minute=0)
    
    # Schedule Redemption Sync daily at 09:30 AM
    scheduler.add_job(job_redemption_sync, 'cron', hour=9, minute=30)
    # Schedule Twitter Sync every 60 minutes
    scheduler.add_job(job_twitter_sync, 'interval', minutes=60)
    
    # Run once immediately on startup to ensure initial data populates
    job_market_sync()
    job_redemption_sync()
    job_twitter_sync()
    
    scheduler.start()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler safely shut down.")
