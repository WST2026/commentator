# 챗봇 서비스 자동화 및 무중단 운영 계획

## 목표
- 깃허브 액션(GitHub Actions) 또는 버셀(Vercel) 등에서 챗봇이 항상 실행되도록 구성

## 수행 방안
1. **실행 구조 점검**
   - 텔레그램 long polling, webhook 등 클라우드 환경에서 동작 가능 여부 확인
   - 서버리스 환경(Vercel 등)에서는 webhook 방식 권장

2. **GitHub Actions 워크플로우 설계**
   - Python 봇을 무한 실행/재시작하는 워크플로우 작성(예: self-hosted runner, cron/restart)
   - 환경변수/비밀키는 GitHub Secrets로 관리

3. **Vercel 배포 구조 설계(옵션)**
   - serverless function으로 webhook 엔드포인트 구현
   - Vercel 환경변수/비밀키 관리

4. **배포 인프라 정비**
   - Dockerfile, requirements.txt 등 배포용 파일 정비
   - README에 배포/운영 방법 문서화

5. **모니터링/장애 대응**
   - 장애 발생 시 자동 재시작, 슬랙/텔레그램 알림 등 모니터링 방안 설계

6. **테스트**
   - 실제 클라우드 환경에서 자동화/무중단 동작 확인 

---

## 추가 아이디어: 서버 최소화 + 외부 LLM API 활용

- 서버(또는 서버리스 함수)는 텔레그램 webhook만 처리
- LLM 추론은 무료/저렴한 외부 API(OpenAI, HuggingFace, Cohere 등)로 요청
- 서버리스(Vercel, AWS Lambda 등) 무료 티어로 운영비 최소화 가능
- LLM 직접 운영 필요 없고, API 호출량만 관리하면 됨
- 단, 무료 API는 호출량/속도/품질 제한이 있으니 참고

이 방식은 비용을 최소화하면서 챗봇을 운영할 수 있는 현실적인 대안임. 필요시 이 구조로 전환 가능. 