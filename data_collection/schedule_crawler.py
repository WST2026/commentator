from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time

# 브라우저 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # 브라우저 창 띄우지 않음
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Selenium 드라이버 실행
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# FIFA 월드컵 경기 일정 기사 URL
url = 'https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums'
driver.get(url)
time.sleep(5)  # 렌더링 대기

# HTML 파싱
soup = BeautifulSoup(driver.page_source, 'html.parser')
driver.quit()

# 결과 저장 리스트
data = []
current_date = ""

# <h4>와 <p>를 순서대로 훑으면서 날짜-경기 쌍을 추출
for elem in soup.find_all(['h4', 'p']):
    if elem.name == 'h4':
        strong_tag = elem.find('strong')
        if strong_tag:
            current_date = strong_tag.get_text(strip=True)

    elif elem.name == 'p' and 'rich-text_p__UfX5b' in elem.get('class', []):
        lines = elem.get_text(separator="\n").split("\n")
        for line in lines:
            if line.strip().startswith("Match"):
                try:
                    # 하이픈 종류 정리: 하이픈, en-dash 등 통일
                    clean_line = line.strip().replace(" - ", " – ").replace("–", " – ")
                    parts = clean_line.split(" – ")

                    if len(parts) >= 3:
                        match_no = parts[0].replace("Match", "").strip()
                        group = parts[1].strip()
                        stadium = parts[2].strip()
                    elif len(parts) == 2:
                        match_no = parts[0].replace("Match", "").strip()
                        group = parts[1].strip()
                        stadium = ""
                    else:
                        continue  # 무시

                    data.append({
                        "날짜": current_date,
                        "매치번호": match_no,
                        "조": group,
                        "경기장": stadium
                    })
                except Exception as e:
                    print("⚠️ 파싱 실패:", line, ">>", e)

# 결과 저장
df = pd.DataFrame(data)
df.to_csv("fixtures_fifa_articles.csv", index=False, encoding='utf-8-sig')

print(f"✅ {len(df)}개 경기 저장 완료!")
print(df.head())
