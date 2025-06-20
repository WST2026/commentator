from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time

# 크롬 드라이버 자동 설치 및 브라우저 실행
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # 브라우저 창 안 띄우기
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# FIFA 경기 일정 페이지로 이동
url = 'https://www.fifa.com/fifaplus/en/tournaments/mens/worldcup/canadamexicousa2026/fixtures'
driver.get(url)
time.sleep(5)  # JavaScript 렌더링 대기 (필요에 따라 조정)

# 전체 페이지 로드가 끝날 때까지 스크롤 다운
SCROLL_PAUSE = 2
last_height = driver.execute_script("return document.body.scrollHeight")
for _ in range(5):  # 충분히 내려줘야 전체 경기 로드됨
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# HTML 파싱
soup = BeautifulSoup(driver.page_source, 'html.parser')
with open("dumped_page.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())

driver.quit()

# 경기 카드 전체 찾기
match_cards = soup.find_all('a', class_='match-card-match-card')  # class는 실제 HTML 구조에 맞게 조정 필요

# 결과 저장용 리스트
matches = []

for card in match_cards:
    try:
        date = card.find('span', class_='match-date').text.strip()
        time_ = card.find('span', class_='match-time').text.strip()
        teams = card.find_all('span', class_='match-teams-name')
        team1 = teams[0].text.strip()
        team2 = teams[1].text.strip()
        stadium = card.find('span', class_='match-venue-name').text.strip()
        city = card.find('span', class_='match-venue-city').text.strip()

        matches.append({
            '날짜': date,
            '시간': time_,
            '팀1': team1,
            '팀2': team2,
            '경기장': stadium,
            '도시': city
        })
    except Exception as e:
        print(f"경기 카드 파싱 실패: {e}")

# CSV로 저장
df = pd.DataFrame(matches)
df.to_csv('fixtures.csv', index=False, encoding='utf-8-sig')

print(f"{len(df)}개의 경기 일정이 저장되었습니다.")
