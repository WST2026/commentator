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

# OpenSearch 클라이언트 (인증 포함)
client = OpenSearch(
    hosts=[{"host": "localhost", "port": 9200}],
    http_auth=("admin", "OpenSearch2024"),
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

# 임베딩 모델
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def search_by_vector(query_text, top_k=5, use_hybrid=True):
    """
    입력 텍스트(query_text)와 유사한 문서를 벡터DB에서 top_k개 반환
    반환값: [{title, content, url, datetime, score}, ...]
    
    Args:
        query_text: 검색할 텍스트
        top_k: 반환할 결과 개수
        use_hybrid: 하이브리드 검색 사용 여부 (기본: True)
    """
    # 인덱스 존재 여부 확인
    try:
        if not client.indices.exists(index=INDEX_NAME):
            print(f"인덱스 {INDEX_NAME}가 존재하지 않습니다.")
            return []
    except Exception as e:
        print(f"인덱스 확인 중 오류: {e}")
        return []
    
    if use_hybrid:
        return hybrid_search(query_text, top_k)
    else:
        return pure_vector_search(query_text, top_k)

def pure_vector_search(query_text, top_k):
    """순수 벡터 검색"""
    # 쿼리 텍스트 임베딩 생성
    try:
        embedding = embedding_model.encode(query_text).tolist()
    except Exception as e:
        print(f"임베딩 생성 중 오류: {e}")
        return []
    
    # KNN 검색 쿼리
    search_body = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": top_k
                }
            }
        },
        "_source": ["title", "content", "url", "datetime"]
    }
    
    try:
        res = client.search(index=INDEX_NAME, body=search_body)
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
        
    except Exception as e:
        print(f"벡터 검색 중 오류: {e}")
        return []

def hybrid_search(query_text, top_k):
    """하이브리드 검색: 벡터 검색 + 키워드 검색 결과 합치기"""
    # 1. 벡터 검색 실행
    vector_results = pure_vector_search(query_text, top_k * 2)  # 더 많은 후보 가져오기
    
    # 2. 키워드 검색 실행
    keyword_results = keyword_search(query_text, top_k)
    
    # 3. 결과 합치기 및 중복 제거
    combined_results = combine_and_deduplicate(vector_results, keyword_results)
    
    # 4. 키워드 관련성으로 재순위
    final_results = rerank_by_keyword_relevance(combined_results, query_text)
    
    # 5. top_k개만 반환
    return final_results[:top_k]

def keyword_search(query_text, top_k):
    """키워드 검색"""
    search_body = {
        "size": top_k,
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["title^3", "content^1"],  # 제목에 3배 가중치
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "_source": ["title", "content", "url", "datetime"]
    }
    
    try:
        res = client.search(index=INDEX_NAME, body=search_body)
        hits = res["hits"]["hits"]
        
        results = []
        for hit in hits:
            source = hit["_source"]
            results.append({
                "title": source.get("title", ""),
                "content": source.get("content", ""),
                "url": source.get("url", ""),
                "datetime": source.get("datetime", ""),
                "score": hit.get("_score", 0),
                "search_type": "keyword"  # 검색 타입 표시
            })
        
        return results
        
    except Exception as e:
        print(f"키워드 검색 중 오류: {e}")
        return []

def combine_and_deduplicate(vector_results, keyword_results):
    """벡터 검색과 키워드 검색 결과를 합치고 중복 제거"""
    # URL을 키로 사용하여 중복 제거
    combined = {}
    
    # 벡터 검색 결과 추가
    for result in vector_results:
        url = result.get("url", "")
        if url and url not in combined:
            result["search_type"] = "vector"
            combined[url] = result
    
    # 키워드 검색 결과 추가 (이미 있으면 더 높은 점수로 업데이트)
    for result in keyword_results:
        url = result.get("url", "")
        if url:
            if url in combined:
                # 이미 있는 경우 더 높은 점수 선택 또는 가중 평균
                existing = combined[url]
                # 키워드 검색에서 찾은 것은 보너스 점수 추가
                existing["score"] = max(existing["score"], result["score"]) + 0.5
                existing["search_type"] = "both"
            else:
                combined[url] = result
    
    return list(combined.values())

def rerank_by_keyword_relevance(results, query_text):
    """
    검색 결과를 키워드 관련성으로 재순위
    """
    keywords = query_text.strip().split()
    
    for result in results:
        title = result.get("title", "").lower()
        content = result.get("content", "").lower()
        query_lower = query_text.lower()
        
        # 키워드 매칭 보너스 점수 계산
        keyword_bonus = 0
        
        # 정확한 문구 매칭 (높은 보너스)
        if query_lower in title:
            keyword_bonus += 2.0
        elif query_lower in content:
            keyword_bonus += 1.0
        
        # 개별 키워드 매칭
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title:
                keyword_bonus += 0.5
            elif keyword_lower in content:
                keyword_bonus += 0.2
        
        # 기존 점수에 키워드 보너스 추가
        result["score"] = result["score"] + keyword_bonus
    
    # 점수 순으로 재정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# 이전 버전과의 호환성을 위한 별칭
def search_by_vector_pure(query_text, top_k=5):
    """순수 벡터 검색 (이전 방식)"""
    return search_by_vector(query_text, top_k, use_hybrid=False)