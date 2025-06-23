import requests
from bs4 import BeautifulSoup
import json
import time

def extract_article_text(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # 페이지 내 모든 <p> 태그의 텍스트를 이어 붙임
        paragraphs = soup.find_all("p")
        content = "\n".join(
            [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        )

        return content if content else "본문 추출 실패"
    except Exception as e:
        return f"에러: {str(e)}"

def bing_news_search(query, num_articles=100):
    headers = {'User-Agent': 'Mozilla/5.0'}
    articles = []
    offset = 0

    while len(articles) < num_articles:
        url = f"https://www.bing.com/news/search?q={query}&first={offset}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        results = soup.select("div.news-card")

        if not results:
            print("📭 더 이상 결과 없음")
            break

        for item in results:
            title_tag = item.select_one("a.title")
            title = title_tag.text.strip() if title_tag else "제목 없음"
            link = title_tag['href'] if title_tag else "링크 없음"
            time_tag = item.select_one("span.source")
            date = time_tag.text.strip() if time_tag else "날짜 없음"

            print(f"\n▶ [{len(articles)+1}] {title}")
            print(f"URL: {link}")

            content = extract_article_text(link)
            print(f"본문 길이: {len(content)}자")

            if not content or "본문 추출 실패" in content or "에러:" in content:
                print("⚠️ 본문 추출 실패, 건너뜀")
                continue

            articles.append({
                "title": title,
                "datetime": date,
                "content": content,
                "url": link
            })

            if len(articles) >= num_articles:
                break

            time.sleep(1)

        offset += 10
        time.sleep(1)

    return articles

if __name__ == "__main__":
    result = bing_news_search("월드컵 2026", 200)
    with open("bing_articles_full.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 최종 저장된 기사 수: {len(result)}개")
