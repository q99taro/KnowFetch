import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# 從環境變數取得 Supabase 的官方 REST API 連線設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_db() -> Client:
    """
    回傳 Supabase 客戶端實例。
    在 FastAPI 的依賴注入 (Dependency Injection) 中可以使用此函數。
    """
    return supabase
