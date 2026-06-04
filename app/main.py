from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Depends
import os

# 引入我們撰寫好的排程任務
from app.tasks.pipeline import KnowledgePipeline
from app.tasks.daily_review import ReviewScheduler

app = FastAPI(
    title="KnowFetch",
    description="自動化技術知識管理與間隔重複複習系統",
    version="1.0.0"
)

CRON_SECRET = os.getenv("CRON_SECRET", "default_secret")

def verify_cron_secret(x_cron_secret: str = Header(None)):
    if CRON_SECRET != "default_secret" and x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "KnowFetch 伺服器運作中！"}

@app.post("/trigger-pipeline", status_code=202, dependencies=[Depends(verify_cron_secret)])
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    透過 HTTP 呼叫觸發資料爬取與圖譜建立流水線。
    使用 BackgroundTasks 以避免 HTTP Timeout，符合 Hugging Face 部署要求。
    """
    pipeline = KnowledgePipeline()
    background_tasks.add_task(pipeline.run_daily_pipeline)
    return {"message": "Knowledge Pipeline Background Task Started"}

@app.post("/trigger-review", status_code=202, dependencies=[Depends(verify_cron_secret)])
async def trigger_review(background_tasks: BackgroundTasks):
    """
    透過 HTTP 呼叫觸發 Telegram 每日推播。
    """
    scheduler = ReviewScheduler()
    background_tasks.add_task(scheduler.send_daily_review)
    return {"message": "Daily Review Background Task Started"}
