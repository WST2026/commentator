# 🎙️commentator🎙️

> **입출력(챗봇) 구조 및 사용법은 [io/README.md](io/README.md) 문서를 참고하세요.**

세계 축구 대회를 관람하며 경기에 대해서 궁금한게 생기면 바로 바로 해설 해주는 챗봇!!

**2026년 북중미 세계 축구 대회**와 관련된 질문에 정확하게 답변할 수 있도록 설계된  
**RAG (Retrieval-Augmented Generation)** 기반 AI 시스템입니다.

LangChain을 기반으로 구성되었으며, **NVIDIA RTX 4090 GPU**에서 로컬 LLM을 서빙합니다.  
텔레그램 / 디스코드 등의 메신저 플랫폼을 통해 사용자와 연결됩니다.

---

## 📁 프로젝트 폴더 구조

commentator/

├── data-collection/ # 월드컵 관련 뉴스, 스탯, 위키 등 데이터 수집


├── vector-db/ # 텍스트 임베딩 및 벡터 저장소 구성

├── rag/ # LangChain 기반 RAG 체인 (Retriever + LLM)

└── io/ # 사용자 입출력 처리 (Telegram, Discord)

---

## 🧠 주요 기능

- 공식 및 비공식 월드컵 정보 수집 (선수, 경기 일정, 기록 등)
- 문서를 임베딩하여 벡터DB에 저장
- 유사 문서를 검색하여 관련 맥락 추출
- 로컬에서 추론 가능한 LLM으로 답변 생성
- 텔레그램, 디스코드 등을 통해 사용자와 응답 주고받기

---

## 🛠️ 기술 스택

- **LLM**: 아직 미정
- **프레임워크**: LangChain
- **벡터 저장소**: Open search
- **챗 인터페이스**: Telegram, Discord
- **하드웨어**: RTX 4090 GPU (로컬 추론)

---

## 🚀 실행 방법

1. 레포지토리 클론

```bash
git clone https://github.com/WST2026/commentator.git
cd commetator
가상 환경 생성 및 패키지 설치 (예: Conda 사용)
```
추후 업데이트 예정....

## 향후 계획 (RoadMap)
[ ] LLM 띄우기

[ ] 정보 수집 스크래퍼 제작

[ ] 벡터 DB 제작

[ ] 리트리벌 구현

[] io 연결(텔레그램 예정)

🙋 기여 및 문의
언제든지 PR 환영합니다!

문의: younguk137@naver.com

---