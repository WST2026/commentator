import os
import sys
import json
import uuid
import yaml
import argparse
import hashlib
from opensearchpy import OpenSearch, helpers

# 🔧 기본 설정
CONFIG_PATH = "../config/upload_config.yaml"
INPUT_JSON = "../data_collection/bing_articles_full.json"
BULK_JSONL = "bulk.jsonl"

# 🔗 OpenSearch 클라이언트 연결
client = OpenSearch("http://localhost:9200")

# ⚙️ 설정 로드
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

index_name = config.get("index_name", "default_index")
id_strategy = config.get("id_strategy", "sequential")  # uuid | sequential | hash

# ✅ 인데그스 생성 (벡터 필드 포함)
def create_index_if_not_exists(index_name):
    if client.indices.exists(index=index_name):
        print(f"[0] 인데그스 '{index_name}' 이미 존재")
        return

    mapping = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "content": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "url": {"type": "keyword"},
                "datetime": {"type": "text"},
                "project_name": {"type": "keyword"},
                "file_name": {"type": "keyword"},
                "page": {"type": "integer"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 384
                }
            }
        }
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"[0] 인데그스 '{index_name}' 생성 완료")

# ✅ ID 생성 전략
def generate_id(item, i):
    if id_strategy == "sequential":
        return str(i + 1)
    elif id_strategy == "hash":
        base = item.get("title", "") + item.get("content", "")
        return hashlib.md5(base.encode("utf-8")).hexdigest()
    else:
        return str(uuid.uuid4())

# ✅ bulk.jsonl 생성 (임베딩 포함)
def convert_json_to_bulk():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(BULK_JSONL, "w", encoding="utf-8") as out:
        for i, item in enumerate(data):
            doc_id = generate_id(item, i)
            text = item.get("content", "")
            embedding = embedding_model.encode(text).tolist()

            meta = {"index": {"_index": index_name, "_id": doc_id}}
            doc = {
                "title": item.get("title", ""),
                "content": text,
                "url": item.get("url", ""),
                "datetime": item.get("datetime", ""),
                "project_name": "agentic_rag",
                "file_name": os.path.basename(INPUT_JSON),
                "page": 1,
                "id": doc_id,
                "embedding": embedding
            }
            out.write(json.dumps(meta, ensure_ascii=False) + "\n")
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"[1] bulk 포맷 변화 완료: {BULK_JSONL} ({len(data)}개 문서)")

# ✅ 업로드
def upload_bulk_jsonl():
    with open(BULK_JSONL, "r", encoding="utf-8") as f:
        lines = f.readlines()

    bulk_lines = [json.loads(line) for line in lines]
    actions = []
    for i in range(0, len(bulk_lines), 2):
        meta = bulk_lines[i]["index"]
        doc = bulk_lines[i + 1]
        action = {
            "_op_type": "index",
            "_index": meta["_index"],
            "_id": meta["_id"],
            "_source": doc
        }
        actions.append(action)

    helpers.bulk(client, actions)
    print(f"[2] 업로드 완료: {len(actions)}개 문서 업로드됨")
    os.remove(BULK_JSONL)
    print(f"[3] 임시 파일 삭제 완료: {BULK_JSONL}")

# ✅ 문서 삭제 (id와 조건으로)
def delete_documents(field=None, value=None):
    if not client.indices.exists(index=index_name):
        print(f"❌ 인데그스 '{index_name}' 존재하지 않음")
        return

    if not field or not value:
        confirm = input("⚠️ 인데그스 전체를 삭제하시겠습니까? (yes/no): ").strip().lower()
        if confirm == "yes":
            client.indices.delete(index=index_name)
            print(f"🗑️ 인데그스 '{index_name}' 삭제 완료")
        else:
            print("❌ 삭제 중지")
        return

    # id 값으로 바로 삭제
    if field == "id":
        res = client.delete(index=index_name, id=value, ignore=[404])
        if res.get("result") == "deleted":
            print(f"🗑️ ID '{value}' 문서 삭제 완료")
        else:
            print(f"❌ ID '{value}' 문서 찾을 수 없음")
    else:
        # match 조건으로 검색 후 삭제
        query = {"match": {field: value}}
        search_res = client.search(index=index_name, body={"query": query, "_source": False, "size": 1000})
        hits = search_res["hits"]["hits"]

        if not hits:
            print(f"❌ 검색 결과 없음 (field: {field}, value: {value})")
            return

        for hit in hits:
            client.delete(index=index_name, id=hit["_id"], ignore=[404])
        print(f"🗑️ 검색으로 찾은 {len(hits)}개 문서 삭제 완료")

# ✅ 인데그스 확인
def check_index():
    print("🔪 인데그스 상태 점검 중...")
    if client.indices.exists(index=index_name):
        count = client.count(index=index_name)["count"]
        print(f"✅ 인데그스 '{index_name}' 존재 (문서 수: {count})")
    else:
        print(f"❌ 인데그스 '{index_name}' 존재하지 않음")

# ✅ 문서 미리보기 (+ 검색)
def preview_documents(size=5, field=None, value=None):
    if not client.indices.exists(index=index_name):
        print(f"❌ 인데그스 '{index_name}' 존재하지 않음")
        return

    if field and value:
        if field == "id":
            query = {"term": {field: value}}
        else:
            query = {"match": {field: value}}
    else:
        query = {"match_all": {}}

    res = client.search(index=index_name, body={"size": size, "query": query})
    hits = res["hits"]["hits"]

    if not hits:
        print(f"🔍 검색 결과 없음 (field: {field}, value: {value})")
        return

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        print(f"\n📄 Document {i} (ID: {source['id']})")
        print(json.dumps({
            "title": source.get("title", ""),
            "content": source.get("content", ""),
            "url": source.get("url", ""),
            "datetime": source.get("datetime", "")
        }, indent=2, ensure_ascii=False))

# ✅ 대화형 CLI
def interactive_cli():
    print("\n무업을 하시겠습니까?")
    print("1. 업로드 (upload)")
    print("2. 인데그스 확인 (check)")
    print("3. 문서 미리보기 (preview)")
    print("4. 문서 삭제 (delete)")
    print("5. 벡터 검색 (search)")

    cmd = input("번호를 입력하세요: ").strip()

    if cmd == "1":
        print("🚀 업로드 시작")
        create_index_if_not_exists(index_name)
        convert_json_to_bulk()
        upload_bulk_jsonl()
    elif cmd == "2":
        check_index()
    elif cmd == "3":
        field = input("검색할 필드 (id, title, content): ").strip()
        value = input("검색어: ").strip()
        size = input("출력 개수 (기본 5): ").strip()
        size = int(size) if size.isdigit() else 5
        preview_documents(size=size, field=field, value=value)
    elif cmd == "4":
        field = input("삭제할 필드 (id, title, content): ").strip()
        value = input("검색어: ").strip()
        delete_documents(field=field, value=value)
    elif cmd == "5":
        print("(벡터 검색은 vector_search.py에서 import해서 사용하세요)")
    else:
        print("❌ 잘못된 입력입니다.")


# ✅ 실행 진입점
if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive_cli()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("command", choices=["upload", "check", "preview", "delete"], help="실행 명령")
        parser.add_argument("--field", help="검색할 필드 (id, title, content)")
        parser.add_argument("--value", help="검색 키워드")
        parser.add_argument("--size", type=int, default=5, help="미리보기 개수 (기본: 5)")
        args = parser.parse_args()

        if args.command == "upload":
            print("🚀 업로드 시작")
            create_index_if_not_exists(index_name)
            convert_json_to_bulk()
            upload_bulk_jsonl()
        elif args.command == "check":
            check_index()
        elif args.command == "preview":
            preview_documents(size=args.size, field=args.field, value=args.value)
        elif args.command == "delete":
            delete_documents(field=args.field, value=args.value)
