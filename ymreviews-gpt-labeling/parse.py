import time
import random
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from selenium_stealth import stealth

import streamlit as st
    
# @st.cache_resource
def get_driver():
    options = Options()
    options.add_argument('--headless')

    ua = UserAgent()
    user_agent = ua.random
    print(user_agent)
    options.add_argument(f'--user-agent={user_agent}')

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager("114.0.5735.90").install()), 
        options=options
    )
    stealth(driver=driver,
        user_agent = user_agent,
        languages=["ru-RU", "ru"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        run_on_insecure_origins=True,
        )
    return driver

# @st.cache_resource
def initialize_driver(reviews_page, _driver, n_tries=0, tries_limit=3):
    if n_tries >= tries_limit:
        st.error('Не удалось открыть страницу, попробуйте позже')
        st.stop()
        # raise TimeoutError('Connection attempts limit reached')

    def interceptor(request):
        del request.headers['Host']
        del request.headers['Referer']
        request.headers['Host'] = 'market.yandex.ru'
        request.headers['Referer'] = reviews_page['url'].split("?")[0]

    print(f"ATTEMPT {n_tries+1}/{tries_limit}")

    _driver.request_interceptor = interceptor
    _driver.get(reviews_page['url'])
    time.sleep(random.randint(5, 20))

    if WebDriverWait(_driver, 15).until(EC.presence_of_element_located((By.XPATH, "//h1[@data-baobab-name='title']"))).text:    
        print("=== Parsing page")
        return _driver
    elif EC.presence_of_element_located((By.XPATH, "//form[@id='checkbox-captcha-form]")):
        # raise Exception("CAPTCHA")
        print("CLEARING CACHE")
        st.cache_resource.clear()
        time.sleep(random.randint(10, 20))  
        _driver = get_driver()
        return initialize_driver(reviews_page, _driver, n_tries=n_tries+1)        
        
def reviews_data_extract(page_source_code):
    soup = BeautifulSoup(page_source_code, 'html.parser')
    
    reviews_container = soup.find('div', {'data-baobab-name': 'reviewList'})
    reviews = reviews_container.find_all('div', {'class': '_3K8Ed'})
    
    reviews_data = []
    
    for review in reviews:
        reviewer_name = review.find('div', {'data-auto': 'user_name'}).text.strip()

        review_element = review.find('div', {'class': '_3IXcz'})

        review_el = []
        for el in ['review-pro', 'review-contra', 'review-comment']:
            try:
                review_el.append(review_element.find('dl', {'data-auto': el}).text.strip())
            except:
                None
        review_text = '\n'.join(review_el).strip()

        try:
            rating_element = review.find('div', {'data-auto': 'rating-stars'})
            rating = rating_element['data-rate']
        except:
            rating = None
            
        reviews_data.append({'reviewer': reviewer_name, 'rating': rating, 'review': review_text})

    return reviews_data

def reviews_parse_pagination(reviews_page, driver):
    reviews_data = []
    with st.spinner('Подготовка к скачиванию...'):
        driver = initialize_driver(reviews_page, driver)
    
    product_title = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//h1[@data-baobab-name='title']"))).text
    print('PRODUCT TITLE:', product_title)

    WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@data-apiary-widget-name='@MarketNode/ProductReviewsList']")))

    with st.spinner('Скачивание в процессе...'):
        max_reviews_num = int(st.session_state.MAX_REVIEWS_NUM)
        while len(reviews_data) <= max_reviews_num:
            reviews_data_curr = reviews_data_extract(driver.page_source)
            time.sleep(random.randint(3, 10))
            reviews_data.extend(reviews_data_curr)
            try:
                WebDriverWait(driver, 20).until(EC.presence_of_element_located(
                    (By.XPATH, f"//*[@data-apiary-widget-name='@MarketNode/ProductReviewsPaginator']//a[contains(text(),'Вперёд')]")
                )).click()
                time.sleep(random.randint(5, 15))
            except:
                break
    
    driver.close()
    driver.quit()
    return product_title, reviews_data[:max_reviews_num]

@st.cache_data
def product_reviews_parse(PRODUCT):
    driver = get_driver()
    reviews_res = []
    product_titles_res = []

    product_title, reviews_curr = reviews_parse_pagination(PRODUCT, driver)
    reviews_res.extend(reviews_curr)
    product_titles_res.extend(product_title)

    return product_titles_res, reviews_res
