import uuid
from typing import List

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)

from app.core.config import settings


class MilvusClient:
    """Milvus 向量库封装：连接管理、Collection 创建、向量插入、相似度检索"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._collection = None
            cls._instance._connected = False
        return cls._instance

    def connect(self):
        """建立 Milvus 连接"""
        try:
            connections.connect(
                alias="default",
                host=settings.milvus.host,
                port=settings.milvus.port,
            )
            self._connected = True
        except Exception as e:
            self._connected = False
            raise e

    def disconnect(self):
        """断开 Milvus 连接"""
        if self._connected:
            connections.disconnect("default")
            self._connected = False

    def _check_connected(self) -> bool:
        if not self._connected:
            print("[Milvus] Not connected, skipping vector operation")
        return self._connected

    def _ensure_collection(self) -> Collection:
        """懒加载获取 Collection 对象"""
        if self._collection is not None:
            return self._collection

        collection_name = settings.milvus.collection
        dim = settings.milvus.embedding_dimensions

        if utility.has_collection(collection_name):
            self._collection = Collection(collection_name)
            self._collection.load()
            return self._collection

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
            FieldSchema(name="content_id", dtype=DataType.VARCHAR, max_length=36),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields, description="NexusAI content vectors")
        self._collection = Collection(collection_name, schema)

        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        self._collection.create_index(field_name="embedding", index_params=index_params)
        self._collection.load()
        return self._collection

    def insert_vectors(self, records: List[dict]) -> List[str]:
        """
        插入向量记录
        :param records: [{"content_id": str, "embedding": List[float]}]
        :return: 插入的向量 id 列表
        """
        if not self._check_connected():
            return []
        collection = self._ensure_collection()
        ids = [str(uuid.uuid4()) for _ in records]
        content_ids = [r["content_id"] for r in records]
        embeddings = [r["embedding"] for r in records]

        collection.insert([ids, content_ids, embeddings])
        collection.flush()
        return ids

    def search_similar(
        self,
        embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.75,
    ) -> List[dict]:
        """
        相似度检索
        :param embedding: 查询向量
        :param top_k: 返回数量
        :param threshold: 相似度阈值（COSINE 距离）
        :return: [{"id": str, "content_id": str, "distance": float}]
        """
        if not self._check_connected():
            return []
        collection = self._ensure_collection()
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

        results = collection.search(
            data=[embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content_id"],
        )

        hits = []
        for result in results[0]:
            if result.distance >= threshold:
                hits.append({
                    "id": result.id,
                    "content_id": result.entity.get("content_id"),
                    "distance": float(result.distance),
                })
        return hits

    def delete_by_content_id(self, content_id: str) -> None:
        """根据 content_id 删除向量"""
        if not self._check_connected():
            return
        collection = self._ensure_collection()
        collection.delete(f'content_id == "{content_id}"')


# 全局单例
milvus_client = MilvusClient()
