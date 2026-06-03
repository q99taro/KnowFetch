import json
from typing import List, Dict, Any
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import os

class ArticleFilterResult(BaseModel):
    url: str = Field(description="文章的 URL")
    keep: bool = Field(description="是否符合爬取條件 (true/false)")
    reason: str = Field(description="判斷原因 (簡短一行)")

class BatchFilterResponse(BaseModel):
    results: List[ArticleFilterResult] = Field(description="文章過濾結果陣列")

class LLMExtractor:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY")
        
        # 初始化 Gemini Client
        self.client = genai.Client(api_key=api_key)
        # 固定使用 Flash-Lite 節省額度 (符合 README)
        self.model_name = "gemini-2.5-flash"  # 使用 2.5 flash 或 flash-lite
        
    def batch_filter_articles(self, articles: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        批次將文章的 title 與 abstract 送交給 Gemini API 判斷是否應該抓取。
        返回符合條件的文章列表。
        """
        if not articles:
            return []

        # 構建 Prompt
        prompt = """
你是專業的 AI 技術編輯。請根據以下文章的「標題 (Title)」與「摘要 (Abstract)」過濾文章。

【符合條件的文章必須包含以下領域之一】：
1. AI (尤其是 LLM / NLP)
2. Data Science (資料科學)
3. Machine Learning / Deep Learning
4. Python (尤其是和前面資料科學/AI相關的教學)
5. 針對上述領域的 Career Advice (職涯建議)

【絕對排除】：
1. Computer Vision (CV) / Image Processing / Object Detection 等視覺相關
2. 非技術文或不相干的廣告

請回傳一個 JSON，針對每篇文章給出是否保留 (keep: true/false) 與簡短原因。
"""
        # 將文章列表加上編號
        article_text = "【文章列表】\n"
        for i, art in enumerate(articles):
            article_text += f"{i+1}. URL: {art['url']}\n   Title: {art['title']}\n   Abstract: {art['abstract']}\n\n"

        prompt += article_text

        # 呼叫 Gemini 的結構化輸出
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BatchFilterResponse,
                temperature=0.0  # 設為 0 以獲得一致的判斷
            ),
        )

        try:
            # 解析回傳的 JSON
            result_data = json.loads(response.text)
            filtered_urls = [
                res['url'] for res in result_data.get('results', []) if res['keep']
            ]
            
            # 從原本的 articles 中挑選出 keep=True 的文章
            final_articles = [art for art in articles if art['url'] in filtered_urls]
            return final_articles

        except Exception as e:
            print("Gemini JSON 解析失敗:", e)
            return []
