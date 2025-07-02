import os
import yaml
import json
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

# 설정 경로 및 기본값
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '../config/upload_config.yaml')

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

INDEX_NAME = config.get("index_name", "default_index")

# OpenSearch 클라이언트
client = OpenSearch("http://localhost:9200")

# 임베딩 모델
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def search_by_vector(query_text, top_k=5):
    """
    입력 텍스트(query_text)와 유사한 문서를 벡터DB에서 top_k개 반환
    반환값: [{title, content, url, datetime, score}, ...]
    """
    if not client.indices.exists(index=INDEX_NAME):
        return []
    embedding = embedding_model.encode(query_text).tolist()
    script_query = {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "knn_score",
                "lang": "knn",
                "params": {
                    "field": "embedding",
                    "query_value": embedding,
                    "space_type": "cosinesimil"
                }
            }
        }
    }
    res = client.search(index=INDEX_NAME, body={"size": top_k, "query": script_query})
    hits = res["hits"]["hits"]
    results = []
    for hit in hits:
        source = hit["_source"]
        results.append({
            "title": source.get("title", ""),
            "content": source.get("content", ""),
            "url": source.get("url", ""),
            "datetime": source.get("datetime", ""),
            "score": hit.get("_score", 0)
        })
    return results 