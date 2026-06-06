from dotenv import load_dotenv
import os
from currentsapi import CurrentsAPI
from typing import Optional
from datetime import datetime, timedelta
from dateutil import parser
from dataclasses import dataclass

@dataclass
class CurrentNews():
    country: Optional[str] = None
    language: Optional[str] = None
    keywords: Optional[str] = None
    category: Optional[str | list] = None
    page_number: Optional[int] = None
    limit: Optional[int] = None
    start_date: Optional[str | datetime] = None
    end_date: Optional[str | datetime] = None
    has_image: Optional[bool] = None
    has_description: Optional[bool] = None

    def _set_payloads(self) -> dict:
        payload = {}
        if self.keywords:
            if not isinstance(self.keywords, str):
                raise ValueError('keywords should be string')
            payload['keywords'] = self.keywords

        if self.country:
            if not isinstance(self.country, str):
                raise ValueError('country should be string')
            payload['country'] = self.country

        if self.language:
            if not isinstance(self.language, str):
                raise ValueError('language should be string')
            payload['language'] = self.language

        if self.category:
            if not isinstance(self.category, str) and not isinstance(self.category, list):
                raise ValueError('category should be string/list')
            if isinstance(self.category, list):
                payload['category'] = ','.join(self.category)
            else:
                payload['category'] = self.category

        if self.page_number:
            if not isinstance(self.page_number, int):
                raise ValueError('page_number should be integer')
            payload['page_number'] = self.page_number

        if self.limit:
            if not isinstance(self.limit, int):
                raise ValueError('limit should be integer')
            payload['limit'] = self.limit

        if self.start_date:
            if isinstance(self.start_date, str):
                date = parser.parse(self.start_date)
            elif isinstance(self.start_date, datetime):
                date = self.start_date
            else:
                raise ValueError('start_date must be string or datetime object')
            payload['start_date'] = date.strftime('%Y-%m-%dT%H:%M:%SZ')

        if self.end_date:
            if isinstance(self.end_date, str):
                date = parser.parse(self.end_date)
            elif isinstance(self.end_date, datetime):
                date = self.end_date
            else:
                raise ValueError('end_date must be string or datetime object')
            payload['end_date'] = date.strftime('%Y-%m-%dT%H:%M:%SZ')

        if self.has_image is not None:
            payload['has_image'] = 'true' if self.has_image else 'false'

        if self.has_description is not None:
            payload['has_description'] = 'true' if self.has_description else 'false'

        return payload

    def get_info(self) -> dict:
        payload = self._set_payloads()
        load_dotenv()
        api_key = os.getenv("CURRENT_NEWS_API_KEY")
        if not api_key:
            raise ValueError("请在.env文件中设置 CURRENT_NEWS_API_KEY")
        
        api = CurrentsAPI(api_key=api_key)
        r = api.search(**payload)
        return r


if __name__ == "__main__":
    ex = CurrentNews(
        country="cn",
        end_date=datetime.now() - timedelta(hours=12)
    ).get_info()
    print(ex)