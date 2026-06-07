import uuid
from pathlib import Path
from typing import List

from milvus_lite import MilvusLite, FieldSchema, CollectionSchema, DataType

from app.core.config import settings


class MilvusClient:
    """Milvus Lite 嵌入式向量库封装"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db: MilvusLite | None = None
            cls._instance._collection = None
        return cls._instance

    def connect(self, data_dir: str | None = None):
        """打开 Milvus Lite 数据库，默认存储在 nexus-python/milvus_data"""
        if data_dir is None:
            data_dir = str(Path(__file__).resolve().parent.parent.parent / "milvus_data")
        try:
            self._db = MilvusLite(data_dir)
            self._ensure_collection()
        except Exception:
            self._db = None
            raise

    def disconnect(self):
        """关闭数据库，释放文件锁"""
        if self._db is not None:
            self._db.close()
            self._db = None
            self._collection = None

    def _check_connected(self) -> bool:
        if self._db is None:
            print("[Milvus] Not connected, skipping vector operation")
        return self._db is not None

    def _ensure_collection(self):
        """懒加载获取 Collection，不存在则创建"""
        if self._collection is not None:
            return

        collection_name = settings.milvus.collection
        dim = settings.llm.embedding_dimensions

        if self._db.has_collection(collection_name):
            self._collection = self._db.get_collection(collection_name)
            self._collection.load()
            return

        schema = CollectionSchema([
            FieldSchema(
                name="id", dtype=DataType.VARCHAR,
                max_length=36, is_primary=True,
            ),
            FieldSchema(
                name="content_id", dtype=DataType.VARCHAR,
                max_length=36,
            ),
            FieldSchema(
                name="embedding", dtype=DataType.FLOAT_VECTOR,
                dim=dim,
            ),
        ])
        self._collection = self._db.create_collection(collection_name, schema)
        self._collection.create_index(
            field_name="embedding",
            index_params={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200},
            },
        )
        self._collection.load()

    def insert_vectors(self, records: List[dict]) -> List[str]:
        """
        插入向量记录
        :param records: [{"content_id": str, "embedding": List[float]}]
        :return: 插入的 id 列表
        """
        if not self._check_connected():
            return []
        self._ensure_collection()

        rows, ids = [], []
        for r in records:
            vid = str(uuid.uuid4())
            ids.append(vid)
            rows.append({
                "id": vid,
                "content_id": r["content_id"],
                "embedding": r["embedding"],
            })
        self._collection.insert(rows)
        return ids

    def search_similar(
        self,
        embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.75,
    ) -> List[dict]:
        """
        相似度检索
        :return: [{"id": str, "content_id": str, "distance": float}]
        """
        if not self._check_connected():
            return []
        self._ensure_collection()

        results = self._collection.search(
            query_vectors=[embedding],
            top_k=top_k,
            metric_type="COSINE",
            anns_field="embedding",
            output_fields=["content_id"],
        )

        hits = []
        for hit in results[0]:
            # Milvus Lite returns cosine distance (0=identical); convert to similarity
            similarity = 1.0 - float(hit["distance"])
            if similarity >= threshold:
                hits.append({
                    "id": hit["id"],
                    "content_id": hit["entity"]["content_id"],
                    "distance": similarity,
                })
        return hits

    def delete_by_content_id(self, content_id: str) -> None:
        """根据 content_id 删除向量（先查询再按主键删除）"""
        if not self._check_connected():
            return
        self._ensure_collection()
        rows = self._collection.query(
            expr=f'content_id == "{content_id}"',
            output_fields=["id"],
        )
        if rows:
            self._collection.delete([r["id"] for r in rows])


milvus_client = MilvusClient()
