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

import streamlit as st

from app import MAX_REVIEWS_NUM
    
def page_source_code_selenium_get(url, driver, element_wait_xpath):
    """Get page source code from url using selenium."""
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    if element_wait_xpath:
        try:
            _ = wait.until(EC.presence_of_element_located((By.XPATH, element_wait_xpath)))
        except TimeoutException:
            return None

    page_source_code = driver.page_source

    return page_source_code

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

def reviews_page_parse(reviews_page, driver):
    page_source_code = page_source_code_selenium_get(reviews_page["url"], driver, reviews_page["element_wait_xpath"])
    if page_source_code is None:
        return None
    
    page_reviews = reviews_data_extract(page_source_code)

    return page_reviews

def initialize_driver(reviews_page, driver, n_tries=0, tries_limit=3):
    if n_tries >= tries_limit:
        st.error('Не удалось открыть страницу, попробуйте позже')
        st.stop()
        # raise TimeoutError('Connection attempts limit reached')
    print(f"ATTEMPT {n_tries+1}/{tries_limit}")
    try:
        driver.get(reviews_page['url'])
        time.sleep(random.randint(5, 20))
        # if WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//form[@id='checkbox-captcha-form]"))):
        if EC.presence_of_element_located((By.XPATH, "//form[@id='checkbox-captcha-form]")):
            raise Exception("CAPTCHA")
        else:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//h1[@data-baobab-name='title']"))).text
            return driver
    except Exception:
        print("CLEARING CACHE")
        st.cache_resource.clear()
        time.sleep(random.randint(10, 20))  
        driver = get_driver()
        return initialize_driver(reviews_page, driver, n_tries=n_tries+1)

def reviews_parse_pagination(reviews_page, driver):
    reviews_data = []
    with st.spinner('Подготовка к скачиванию...'):
        driver = initialize_driver(reviews_page, driver)
    # if not driver:
    #     st.stop()
    #     return ConnectionError("Couldn't initialize driver")
    
    product_title = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//h1[@data-baobab-name='title']"))).text
    print('PRODUCT TITLE:', product_title)

    WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@data-apiary-widget-name='@MarketNode/ProductReviewsList']")))

    with st.spinner('Скачивание в процессе...'):
        while len(reviews_data) <= int(MAX_REVIEWS_NUM):
            reviews_data_curr = reviews_data_extract(driver.page_source)
            time.sleep(random.randint(3, 10))
            reviews_data.extend(reviews_data_curr)
            try:
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, f"//*[@data-apiary-widget-name='@MarketNode/ProductReviewsPaginator']//a[contains(text(),'Вперёд')]"))).click()
                time.sleep(10)
            except:
                break
    return product_title, reviews_data

@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--headless')
    ua = UserAgent()
    user_agent = ua.random
    print(user_agent)
    options.add_argument(f'--user-agent={user_agent}')
    return webdriver.Chrome(service=Service(ChromeDriverManager("114.0.5735.90").install()), options=options)

def product_reviews_parse(PRODUCTS):
    driver = get_driver()
    reviews_res = []
    product_titles_res = []

    for product_page in PRODUCTS:
        product_title, reviews_curr = reviews_parse_pagination(product_page, driver)
        reviews_res.extend(reviews_curr)
        product_titles_res.extend(product_title)

    return product_titles_res, reviews_res
