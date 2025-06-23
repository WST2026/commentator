# RAG 구현
## LLM을 로컬에서 띄우기 위해서 작은 버전의 LLM을 사용합니다.
3060에서 kanana-1.5-2.1b-instruct-2505 가 작동하는 것을 확인했습니다.
근데 느려요. 엄청요.

## 실행법 
* conda create -n RAG python=3.12
* conda activate RAG
* pip install transformers
* python RAG/kanan_test.py 



## 리트리벌(벡터 DB에 대해 유사도 검색)
## 출력 확인