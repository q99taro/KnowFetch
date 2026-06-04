import re
from typing import List

class AdaptiveChunker:
    def __init__(self, target_chunk_size: int = 60000):
        # 期望的區塊字數大小 (可視 Gemini 處理能力微調)
        # 大幅增加 Chunk Size，利用 Gemini Flash-Lite 的大 Context Window
        # 以整篇文為單位進行提取 (60000 字涵蓋絕大多數 Medium / TDS 萬字長文)
        self.target_chunk_size = target_chunk_size

    def chunk_article(self, text: str) -> List[str]:
        """
        自適應分塊策略 (Adaptive Chunking)
        1. 隔離 Markdown 程式碼區塊 (保護機制)
        2. 以 \n\n 將普通文本切斷
        3. 重新聚合段落與程式碼，確保不會把語意截斷成太小塊
        """
        code_blocks = {}
        
        # 內部函數：暫時把程式碼區塊替換成佔位符 (Placeholder)
        def replace_with_placeholder(match):
            block_id = len(code_blocks)
            placeholder = f"__CODE_BLOCK_{block_id}__"
            code_blocks[placeholder] = match.group(0)
            # 強制在佔位符前後加上雙換行，保證它不會跟其他文字黏在一起
            return f"\n\n{placeholder}\n\n"
            
        # 1. 隔離程式碼 (使用 re.DOTALL 確保 . 也能匹配到換行符)
        protected_text = re.sub(r'```.*?```', replace_with_placeholder, text, flags=re.DOTALL)
        
        # 2. 以雙換行符切割普通文本
        raw_chunks = re.split(r'\n{2,}', protected_text)
        
        # 3. 還原程式碼區塊
        restored_chunks = []
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
                
            # 將存在於這段文字中的佔位符替換回原始的程式碼
            for placeholder, code_text in code_blocks.items():
                if placeholder in chunk:
                    chunk = chunk.replace(placeholder, code_text)
                    
            restored_chunks.append(chunk)

        # 4. 適度合併段落 (Merge small chunks)
        # LLM 抽取時，如果一次只給一句話會缺乏上下文；
        # 所以我們將相鄰的段落合併，直到稍微超過 target_chunk_size 為止
        merged_chunks = []
        current_block = ""
        
        for chunk in restored_chunks:
            # 如果單一段落超級長 (例如一整塊巨大程式碼)，就直接獨立成一塊
            if len(current_block) + len(chunk) > self.target_chunk_size:
                if current_block:
                    merged_chunks.append(current_block.strip())
                    current_block = chunk
                else:
                    merged_chunks.append(chunk)
                    current_block = ""
            else:
                if current_block:
                    current_block += "\n\n" + chunk
                else:
                    current_block = chunk
                    
        if current_block:
            merged_chunks.append(current_block.strip())
            
        return merged_chunks

# 開發階段測試
if __name__ == "__main__":
    test_text = """
資料科學的基本概念是一切的基礎。接下來我們看看 Pandas 如何讀取資料。

這裡是一個常見的讀取範例，我們使用 `read_csv`：

```python
import pandas as pd

# 讀取資料
df = pd.read_csv('data.csv')

# 清洗空值
df.dropna(inplace=True)
df.reset_index(drop=True, inplace=True)
```

執行完畢後，你就完成了第一步的清理！這非常重要。
    """
    
    chunker = AdaptiveChunker(target_chunk_size=100) # 刻意調小來測試切割
    result = chunker.chunk_article(test_text)
    
    for i, c in enumerate(result):
        print(f"--- Chunk {i+1} ---")
        print(c)
        print("---------------\n")