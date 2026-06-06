from pydantic import BaseModel, Field
from datetime import datetime

class Article(BaseModel):
    """单篇文章结构"""
    title: str = Field(description="文章标题")
    link: str = Field(description="文章链接")
    summary: str = Field(default="", description="文章摘要/描述")
    published_at: str = Field(description="发布时间（ISO 8601 或原始字符串）",
                              default=datetime.now().isoformat())