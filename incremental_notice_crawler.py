import sqlite3
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from datetime import datetime, timezone, timedelta
import os

# 한국 시간대 설정 (UTC+9) - 표시용만
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간 반환 (표시용)"""
    return datetime.now(KST)

def get_latest_notice_date():
    """DB에서 최신 공지사항 날짜 조회"""
    try:
        conn = sqlite3.connect('school_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(created_at) FROM notices")
        latest_date = cursor.fetchone()[0]
        conn.close()
        return latest_date
    except Exception as e:
        print(f"DB 조회 오류: {e}")
        return None

def save_notices_to_db(notices_data):
    """공지사항 데이터를 DB에 저장"""
    try:
        conn = sqlite3.connect('school_data.db')
        cursor = conn.cursor()
        
        # 기존 제목 목록 (중복 방지)
        cursor.execute("SELECT title FROM notices")
        existing_titles = {row[0] for row in cursor.fetchall()}
        
        new_count = 0
        for notice in notices_data:
            if notice['title'] not in existing_titles:
                cursor.execute("""
                    INSERT INTO notices (title, content, url, created_at, tags, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    notice['title'],
                    notice['content'],
                    notice['url'],
                    notice['created_at'],
                    notice['tags'],
                    notice['category']
                ))
                new_count += 1
                print(f"새 공지사항 추가: {notice['title']}")
        
        conn.commit()
        conn.close()
        print(f"총 {new_count}개의 새로운 공지사항이 저장되었습니다.")
        return new_count
        
    except Exception as e:
        print(f"DB 저장 오류: {e}")
        return 0

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 백그라운드 실행
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    
    # Render 환경에서 ChromeDriver 경로 설정
    if os.path.exists('/usr/local/bin/chromedriver'):
        service = Service('/usr/local/bin/chromedriver')
    else:
    service = Service()
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(3)
    return driver

def extract_notice_content(driver):
    """공지사항 본문 추출"""
    try:
        el = driver.find_element(By.CSS_SELECTOR, "div.bbsV_cont")
        return el.text.strip()
    except Exception:
        return ""

def parse_date(date_str):
    """날짜 문자열을 표준 형식으로 변환"""
    try:
        # "2025.07.07" -> "2025-07-07"
        if '.' in date_str:
            return date_str.replace('.', '-')
        return date_str
    except:
        return date_str

def crawl_incremental_notices(max_new_notices=50):
    """증분 업데이트 방식으로 공지사항 크롤링"""
    latest_date = get_latest_notice_date()
    print(f"DB 최신 공지사항 날짜: {latest_date}")
    
    if not latest_date:
        print("DB에서 최신 날짜를 가져올 수 없습니다.")
        return
    
    url = "https://pajuwaseok-e.goepj.kr/pajuwaseok-e/na/ntt/selectNttList.do?mi=8476&bbsId=5794"
    driver = setup_driver()
    new_notices = []
    
    try:
        print("공지사항 페이지 접속 중...")
        driver.get(url)
        time.sleep(2)
        
        page = 1
        while len(new_notices) < max_new_notices:
            print(f"\n=== 페이지 {page} 확인 중 ===")
            
            if page > 1:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, f"a[onclick*='goPaging({page})']")
                    btn.click()
                    time.sleep(2)
                except Exception as e:
                    print(f"페이지 이동 오류: {e}")
                    break
            
            # 현재 페이지의 모든 링크 가져오기
            links = driver.find_elements(By.CSS_SELECTOR, "table tbody tr td.ta_l > a")
            print(f"현재 페이지 링크 수: {len(links)}")
            
            page_has_new = False
            for i in range(len(links)):
                if len(new_notices) >= max_new_notices:
                    break
                    
                try:
                    # 매 반복마다 links 재조회
                    links = driver.find_elements(By.CSS_SELECTOR, "table tbody tr td.ta_l > a")
                    a = links[i]
                    title = a.text.strip()
                    
                    if not title:
                        continue
                    
                    row = a.find_element(By.XPATH, "./ancestor::tr")
                    
                    try:
                        created_at = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
                        created_at = parse_date(created_at)
                    except Exception:
                        created_at = ""
                    
                    # 최신 날짜 이후 데이터만 처리
                    if created_at and created_at <= latest_date:
                        print(f"이미 처리된 공지사항: {title} ({created_at})")
                        continue
                    
                    print(f"새 공지사항 발견: {title} ({created_at})")
                    
                    # 상세 페이지로 이동
                    a.click()
                    time.sleep(1)
                    
                    detail_url = driver.current_url
                    content = extract_notice_content(driver)
                    
                    driver.back()
                    time.sleep(1)
                    
                    new_notice = {
                        "title": title,
                        "url": detail_url,
                        "content": content,
                        "created_at": created_at,
                        "tags": title,
                        "category": None
                    }
                    
                    new_notices.append(new_notice)
                    page_has_new = True
                    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    print(f"공지사항 처리 중 오류: {str(e)}")
                    continue
            
            # 현재 페이지에 새로운 공지사항이 없으면 종료
            if not page_has_new:
                print("더 이상 새로운 공지사항이 없습니다.")
                break
                
            page += 1
        
        # 새로운 데이터를 DB에 저장
        if new_notices:
            save_notices_to_db(new_notices)
        else:
            print("새로운 공지사항이 없습니다.")
            
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

def get_latest_meal_date():
    """DB에서 최신 급식 날짜 조회"""
    try:
        conn = sqlite3.connect('school_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM meals")
        latest_date = cursor.fetchone()[0]
        conn.close()
        return latest_date
    except Exception as e:
        print(f"DB 조회 오류: {e}")
        return None

def save_meals_to_db(meals_data):
    """급식 데이터를 DB에 저장"""
    try:
        conn = sqlite3.connect('school_data.db')
        cursor = conn.cursor()
        
        # 기존 데이터 확인을 위한 날짜 목록
        cursor.execute("SELECT date FROM meals")
        existing_dates = {row[0] for row in cursor.fetchall()}
        
        new_count = 0
        for meal in meals_data:
            if meal['date'] not in existing_dates:
                cursor.execute("""
                    INSERT INTO meals (date, meal_type, menu, image_url)
                    VALUES (?, ?, ?, ?)
                """, (meal['date'], meal['meal_type'], meal['menu'], meal['image_url']))
                new_count += 1
                print(f"새 급식 추가: {meal['date']}")
        
        conn.commit()
        conn.close()
        print(f"총 {new_count}개의 새로운 급식 데이터가 저장되었습니다.")
        return new_count
        
    except Exception as e:
        print(f"DB 저장 오류: {e}")
        return 0

def extract_weekday_lunch(driver):
    """현재 페이지의 월~금 중식 데이터 추출"""
    results = []
    try:
        date_els = driver.find_elements(By.CSS_SELECTOR, 'thead tr th')[1:]
        dates = [el.text.split('\n')[1] for el in date_els]
        
        for i in range(1, 6):
            menu = ''
            img_url = ''
            try:
                xpath = f'//*[@id="detailForm"]/div/table/tbody/tr[2]/td[{i+1}]/p[4]'
                menu = driver.find_element(By.XPATH, xpath).text.strip()
            except Exception:
                continue
                
            try:
                td_xpath = f'//*[@id="detailForm"]/div/table/tbody/tr[2]/td[{i+1}]'
                td_html = driver.find_element(By.XPATH, td_xpath).get_attribute('innerHTML')
                img_match = re.search(r'<img[^>]+src=["\"]([^"\"]+)["\"]', td_html)
                if img_match:
                    img_url = img_match.group(1)
            except Exception:
                pass
                
            if menu:  # 메뉴가 있는 경우만 추가
                results.append({
                    'date': dates[i],
                    'meal_type': '중식',
                    'menu': menu,
                    'image_url': img_url
                })
    except Exception as e:
        print(f"데이터 추출 오류: {e}")
    
    return results

def crawl_incremental_meals():
    """증분 업데이트 방식으로 급식 크롤링"""
    latest_date = get_latest_meal_date()
    print(f"DB 최신 급식 날짜: {latest_date}")
    
    if not latest_date:
        print("DB에 급식 데이터가 없습니다. 전체 크롤링을 시작합니다.")
        latest_date = "1900-01-01"  # 모든 데이터를 가져오기 위한 초기 날짜
    
    driver = setup_driver()
    new_meals = []
    
    try:
        print("급식 페이지 접속 중...")
        driver.get('https://pajuwaseok-e.goepj.kr/pajuwaseok-e/ad/fm/foodmenu/selectFoodMenuView.do?mi=8432')
        time.sleep(2)
        
        week_count = 0
        max_weeks = 10  # 최대 10주까지만 확인 (안전장치)
        
        while week_count < max_weeks:
            print(f"\n=== {week_count + 1}번째 주 확인 중 ===")
            
            # 현재 페이지의 급식 데이터 추출
            week_data = extract_weekday_lunch(driver)
            
            if not week_data:
                print("더 이상 급식 데이터가 없습니다.")
                break
            
            # 최신 날짜 이후 데이터만 필터링
            filtered_data = []
            for meal in week_data:
                if meal['date'] > latest_date:
                    filtered_data.append(meal)
                    print(f"새 급식 발견: {meal['date']}")
            
            new_meals.extend(filtered_data)
            
            # 다음 주로 이동
            try:
                prev_btn = driver.find_element(By.CSS_SELECTOR, 'a:has(i.xi-angle-right)')
                prev_btn.click()
                time.sleep(1)
                week_count += 1
            except NoSuchElementException:
                print("더 이상 이전 주 버튼이 없습니다.")
                break
            except Exception as e:
                print(f"페이지 이동 오류: {e}")
                break
        
        # 새로운 데이터를 DB에 저장
        if new_meals:
            save_meals_to_db(new_meals)
        else:
            print("새로운 급식 데이터가 없습니다.")
            
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()

def main():
    """공지사항 크롤링 후 급식 크롤링 실행"""
    print("🚀 공지사항 크롤링 시작...")
    crawl_incremental_notices()
    
    print("\n" + "="*50)
    print("🍽️  급식 크롤링 시작...")
    print("="*50)
    crawl_incremental_meals()
    
    print("\n🎉 모든 크롤링 완료!")

if __name__ == "__main__":
    main() 