import os
import resend
import markdown

class EmailSender:
    def __init__(self):
        resend.api_key = os.getenv("RESEND_API_KEY")
        self.sender_email = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL")

    async def send_article_summary(self, title: str, article_url: str, markdown_summary: str) -> bool:
        """
        寄送單篇文章的 Markdown 總結到指定信箱 (透過 Resend API)。
        """
        if not resend.api_key or not self.recipient_email:
            print("⚠️ 未設定 RESEND_API_KEY 或 RECIPIENT_EMAIL，無法寄送 Email。")
            return False

        subject = f"[KnowFetch] 新文章重點：{title}"

        # 將 Markdown 轉換為 HTML
        html_summary = markdown.markdown(markdown_summary, extensions=["extra"])
        
        # 簡單地將轉換後的 HTML 包裝起來，為了更好的閱讀體驗
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
                .footer {{ margin-top: 20px; font-size: 0.9em; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <h3>文章標題：<a href="{article_url}">{title}</a></h3>
            <hr/>
            <!-- 轉換後的 HTML -->
            <div>{html_summary}</div>
            <div class="footer">
                <p>這封郵件由 KnowFetch 自動寄送 (via Resend API)。</p>
            </div>
        </body>
        </html>
        """

        try:
            r = resend.Emails.send({
                "from": self.sender_email,
                "to": self.recipient_email,
                "subject": subject,
                "html": html_content
            })
            print(f"✅ Email 寄送成功! Resend ID: {r.get('id') if isinstance(r, dict) else r}")
            return True
        except Exception as e:
            print(f"❌ 寄送 Email 失敗: {e}")
            return False
