import asyncio
import os
import httpx
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re

from urllib.parse import urlparse, parse_qs

class ArticleScraper:
    FEEDS = {
        "kdnuggets": "https://www.kdnuggets.com/feed",
        "towardsdatascience": "https://towardsdatascience.com/feed/"
    }

    async def fetch_latest_articles(self) -> List[Dict[str, str]]:
        """
        一次取得多個來源的最新文章 (24 小時內)。
        """
        all_articles = []
        now_utc = datetime.now(timezone.utc)
        one_day_ago = now_utc - timedelta(days=1)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for source_name, url in self.FEEDS.items():
                print(f"正在擷取: {source_name}")
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    root = ET.fromstring(response.text)
                    
                    # 處理 Atom / RSS XML
                    if root.tag.endswith('feed'):
                        ns = {'atom': 'http://www.w3.org/2005/Atom'}
                        for entry in root.findall('.//atom:entry', ns):
                            title = entry.find('atom:title', ns).text
                            link = entry.find('atom:link', ns).get('href')
                            
                            abstract = ""
                            content = entry.find('atom:content', ns)
                            if content is not None and content.text:
                                soup = BeautifulSoup(content.text, 'html.parser')
                                abstract = soup.get_text(separator=' ').strip()[:500]
                                
                            pub_date_str = entry.find('atom:published', ns).text
                            try:
                                pub_date = datetime.fromisoformat(pub_date_str)
                            except ValueError as e:
                                print(f"無法解析時間 {pub_date_str}: {e}")
                                pub_date = now_utc

                            all_articles.append({
                                "source": source_name,
                                "title": title,
                                "url": link,
                                "abstract": abstract.strip(),
                                "pub_date": pub_date.isoformat(),
                                "is_recent": pub_date >= one_day_ago
                            })
                    else:
                        for item in root.findall('.//item'):
                            title = item.find('title').text
                            link = item.find('link').text
                            
                            # 解析摘要 (過濾掉 HTML 標籤)
                            description_node = item.find('description')
                            abstract = ""
                            if description_node is not None and description_node.text:
                                soup = BeautifulSoup(description_node.text, 'html.parser')
                                abstract = soup.get_text(separator=' ').strip()
                                
                            # 解析時間
                            pub_date_str = item.find('pubDate').text
                            try:
                                # KDnuggets & Medium RSS pubDate 格式通常是: "Wed, 03 Jun 2026 12:00:00 +0000" 或 "GMT"
                                if pub_date_str.endswith('GMT'):
                                    pub_date_str = pub_date_str.replace('GMT', '+0000')
                                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                            except ValueError as e:
                                print(f"無法解析時間 {pub_date_str}: {e}")
                                pub_date = now_utc

                            if pub_date >= one_day_ago:
                                all_articles.append({
                                    "source": source_name,
                                    "title": title,
                                    "url": link,
                                    "abstract": abstract,
                                    "pub_date": pub_date.isoformat(),
                                    "is_recent": True
                                })
                            else:
                                all_articles.append({
                                    "source": source_name,
                                    "title": title,
                                    "url": link,
                                    "abstract": abstract,
                                    "pub_date": pub_date.isoformat(),
                                    "is_recent": False
                                })
                except Exception as e:
                    import traceback
                    print(f"擷取 {source_name} 發生錯誤: {e}")
                    print(traceback.format_exc())
                    
        return all_articles

    async def fetch_article_content(self, url: str, source: str) -> str:
        """
        依據網址來源抓取文章，並遵守該網站的禮貌限制 (例如 TDS 停留 10 秒)。
        將 HTML 轉為純文字，保留 Markdown 程式碼區塊。
        """
        # --- 禮貌性延遲 ---
        if source == "towardsdatascience":
            print(f"進入 Towards Data Science 前，強制等待 10 秒: {url}")
            await asyncio.sleep(10)
        else:
            print(f"正在抓取文章: {url}")

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            # 加入 User-Agent，避免被部分網站擋掉
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"無法抓取 {url} (HTTP {response.status_code})")
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- 處理程式碼轉換 ---
            for pre in soup.find_all(['pre', 'code']):
                if pre.name == 'code' and pre.parent.name == 'pre':
                    continue
                code_text = pre.get_text()
                markdown_code = f"\n\n```python\n{code_text}\n```\n\n"
                pre.replace_with(BeautifulSoup(markdown_code, 'html.parser'))
                
            for p in soup.find_all('p'):
                p.append("\n\n")

            # --- 尋找主體與抽取內文 ---
            if source == "kdnuggets":
                content_div = soup.select_one('div#post-, div.post-content, div.entry-content')
            elif source == "towardsdatascience":
                # Medium 文章有很多 section 或 article 標籤
                content_div = soup.select_one('article')
                if not content_div:
                    # Fallback: 將所有的 h1, h2, p 合併
                    elements = soup.find_all(['h1', 'h2', 'h3', 'p'])
                    content = "\n\n".join([el.get_text() for el in elements])
                    return self._clean_text(content)
            else:
                content_div = soup.body

            if not content_div:
                return ""

            return self._clean_text(content_div.get_text(separator=' '))

    def _clean_text(self, text: str) -> str:
        # 清理多餘的空白與換行，確保最多雙換行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
