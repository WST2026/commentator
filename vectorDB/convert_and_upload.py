import os
import sys
import json
import uuid
import yaml
import argparse
from opensearchpy import OpenSearch, helpers

# 기본 설정
CONFIG_PATH = "../config/upload_config.yaml"
INPUT_JSON = "../data_collection/bing_articles_full.json"
BULK_JSONL = "bulk.jsonl"

# OpenSearch 클라이언트 연결
client = OpenSearch("http://localhost:9200")

# 설정 불러오기
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

index_name = config["index_name"]


# ✅ 인덱스 없으면 생성
def create_index_if_not_exists(index_name):
    if client.indices.exists(index=index_name):
        print(f"[0] 인덱스 '{index_name}' 이미 존재")
        return

    mapping = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "title": {"type": "text"},
                "content": {"type": "text"},
                "url": {"type": "keyword"},
                "datetime": {"type": "text"},
                "project_name": {"type": "keyword"},
                "file_name": {"type": "keyword"},
                "page": {"type": "integer"}
            }
        }
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"[0] 인덱스 '{index_name}' 생성 완료")


# ✅ bulk.jsonl 파일 생성
def convert_json_to_bulk():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(BULK_JSONL, "w", encoding="utf-8") as out:
        for i, item in enumerate(data):
            uid = str(uuid.uuid4())

            meta = {"index": {"_index": index_name, "_id": uid}}
            out.write(json.dumps(meta, ensure_ascii=False) + "\n")

            doc = {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
                "datetime": item.get("datetime", ""),
                "project_name": "agentic_rag",
                "file_name": os.path.basename(INPUT_JSON),
                "page": 1,
                "id": uid
            }
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"[1] bulk 포맷 변환 완료: {BULK_JSONL} ({len(data)}개 문서)")


# ✅ bulk.jsonl → OpenSearch 업로드
def upload_bulk_jsonl():
    with open(BULK_JSONL, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 짝수 줄: index, document, index, document, ...
    bulk_lines = [json.loads(line) for line in lines]

    # helpers.bulk()는 (action, document)의 튜플 리스트를 받음
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


# ✅ 인덱스 상태 확인
def check_index():
    print("🧪 인덱스 상태 점검 중...")
    if client.indices.exists(index=index_name):
        count = client.count(index=index_name)["count"]
        print(f"✅ 인덱스 '{index_name}' 존재 (문서 수: {count})")
    else:
        print(f"❌ 인덱스 '{index_name}' 존재하지 않음")


# ✅ 문서 미리보기
def preview_documents(size=5):
    if not client.indices.exists(index=index_name):
        print(f"❌ 인덱스 '{index_name}' 존재하지 않음")
        return

    res = client.search(index=index_name, body={"size": size, "query": {"match_all": {}}})
    for i, hit in enumerate(res["hits"]["hits"], 1):
        print(f"\n📄 Document {i} (ID: {hit['_id']})")
        print(json.dumps(hit["_source"], indent=2, ensure_ascii=False))


# ✅ 명령어 분기
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            check_index()
        elif sys.argv[1] == "preview":
            preview_documents()
        elif sys.argv[1] == "upload":
            print("🚀 업로드 시작")
            create_index_if_not_exists(index_name)
            convert_json_to_bulk()
            upload_bulk_jsonl()
        else:
            print("❗ 지원되지 않는 명령입니다.")
            print("  python convert_and_upload.py upload    # 변환 + 업로드")
            print("  python convert_and_upload.py check     # 인덱스 확인")
            print("  python convert_and_upload.py preview   # 문서 미리보기")
    else:
        print("❗ 명령어를 입력하세요 (upload | check | preview)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["upload", "check", "preview"], help="실행 명령")
    parser.add_argument("--field", help="검색할 필드 (id, title, content)")
    parser.add_argument("--value", help="검색 키워드")
    parser.add_argument("--size", type=int, default=5, help="미리보기 개수 (기본: 5)")

    args = parser.parse_args()

    if args.command == "check":
        check_index()
    elif args.command == "upload":
        print("🚀 업로드 시작")
        create_index_if_not_exists(index_name)
        convert_json_to_bulk()
        upload_bulk_jsonl()
    elif args.command == "preview":
        preview_documents(size=args.size, field=args.field, value=args.value)