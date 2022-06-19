# -*- coding: utf-8 -*-
"""Cosmetic_ingrdeients_collector.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1IYX067pg5CfCTF-1iPwsj3ujcbQvck63
"""

# 패키지 임포트 #
import requests
import urllib.request
import pandas as pd
import numpy as np
import re
import time
import json
from bs4 import BeautifulSoup
from tqdm import tqdm

# 전역 변수 설정 #

# Naver API 토큰 #
client_id = "QWVioFFnIln3wUPOCsjG"
client_secret = "p2mnFSzIQh"

# Naver API 변수 #
savecsv = 1
# 키워드셋
keywords_set = [["넥케어", "스킨", "토너", "로션", "에센스", "크림", "아이케어", "미스트", "페이스오일"], 
                ["BB크림", "CC크림", "메이크업베이스", "프라이머", "파운데이션", "파우더"],
                ["립스틱", "립케어", "립글로스", "립틴트", "립라이너", "아이새도", "아이라이너"],
                ["클렌징폼", "클렌징오일", "클렌징크림", "클렌징티슈", "스크럽"],
                ["선크림", "선스틱", "선스프레이", "선파우더", "쉐이빙폼", "컨실러"],
                ["남성올인원", "여성올인원", "톤업크림", "올인원화장품"]
]
set_num = 5
# 초기 Dafaframe 생성용 키워드
keyword_start = keywords_set[set_num][0]
# 이후 검색할 키워드 배열
keywords = keywords_set[set_num][1:]
# 1회 요청시 반환 결과 수량
result_qty = 100
# 반복횟수(qty + x*qty) 갯수만큼 데이터 요청
rpt = 9
# 내보낼 CSV 이름
d_num = (result_qty + rpt*result_qty) * (1+len(keywords))
raw_csv_name = f"smp_raw_{d_num}.csv"

# 미가공 CSV 경로 #
raw_csv_path = f"./smp_raw_{d_num}.csv"
# 전성분 포함 CSV 이름
smp_csv_name = f"smp_{d_num}.csv"
# 샘플 가공시 제거알 열 인덱스
remove_indexes = ['hprice', 'productType']
#1차 CSV 경로
smp_csv_path = f"./smp_{d_num}.csv"

# Naver API 함수 #
def openapi_request(kw, qty, num, pjson = 1):
  # kw, qty, num은 필수, pjson은 선택입력
  keyword = kw      # string  /
  show_qty = qty    # integer / 1 ~ X ~ 100
  start_num = num   # integer / 1 ~ X ~ 1000

  #open api 주소 및 토큰값
  url = "https://openapi.naver.com/v1/search/shop.json"
  option = f"&display={show_qty}&start={start_num}"
  query = "?query="+urllib.parse.quote(keyword)
  url_query = url + query + option

  # api 요청
  request = urllib.request.Request(url_query)
  request.add_header("X-Naver-Client-Id",client_id)
  request.add_header("X-Naver-Client-Secret",client_secret)

  # api 값 확인
  response = urllib.request.urlopen(request)
  rescode = response.getcode()

  # 정상호출(200) 이면 값 반환 아니면 오류코드 반환
  if(rescode == 200):
      response_body = response.read()
      if(pjson == 1):
        print(response_body.decode('utf-8'))
      return response_body
  else:
      print("Error code:"+rescode)
      return "Error code:"+rescode

# json을 Pandas의 DataFrame으로 바꾸어줌
def jsontodf(t_json):
  t_json = t_json.decode('utf-8')
  t_json = json.loads(t_json)
  df = pd.json_normalize(t_json['items'])
  return df

# 반복 API호출 및 데이터 병합
def repeatMerge(keyword):
  # api로 N00개의 화장품 데이터 검색
  for i in range(rpt+1):
    r_json = openapi_request(keyword, result_qty, 1+(i*result_qty), 0)
    df = jsontodf(r_json)

    # <- 데이터 병합처리 시작
    if(i == 0):
      data = df

    if(i != 0):
      data = pd.concat([data,df], ignore_index=True)
    # <- 데이터 병합처리 끝

  return data

# 전성분 스크래핑 함수 #

# 화장품 이름 정제
def removeTag(title):
  text = title
  text = re.sub('<b>', '', text)
  text = re.sub('</b>', '', text)
  text = re.sub('\(.*\)', '', text)
  text = re.sub('\[.*\]', '', text)
  text = re.sub('\d+ml', '', text)
  text = re.sub('\d+매', '', text)
  text = re.sub('\d+호[\s\S]*', '', text)
  text = re.sub('(\d+\.?\d*\s?g)|(\d+\.)', '', text)
  text = text.strip()
  text = text.strip()
  return text

# 화장품 성분 정제
def refineText(ingred):
  text = ingred
  text = text.replace(" ","")
  text = text.replace("1,2","1/2")
  text = text.replace("헥산디올","헥산다이올")
  text = text.replace("트리메칠실록시", "트라이메틸실록시")
  text = re.sub('\"', '', text)
  text = re.sub("\(\d+\%\)", '', text)
  text = text.strip()
  return text

# 화장품 전성분 스크래핑
def getIngred(pid):
  product = pid
  detailurl = f'https://search.shopping.naver.com/catalog/{pid}'
  product_detail = requests.get(detailurl)
  soup = BeautifulSoup(product_detail.text, 'html.parser')

  if(len(soup.select('#__next > div > div.style_container__3iYev > div.style_inner__1Eo2z > div.top_summary_title__15yAr > div.top_grade__3jjdl')) > 0):
    rank = soup.select('#__next > div > div.style_container__3iYev > div.style_inner__1Eo2z > div.top_summary_title__15yAr > div.top_grade__3jjdl')[0].text
    rank = re.sub('^평점','', rank)
    rank = rank.strip()
  else:
    rank = "NaN"

  if(len(soup.select('#section_ingredient > div > p')) > 0):
    ingredients = soup.select('#section_ingredient > div > p')[0].text
  else:
    ingredients = "NaN"
  
  ingredients = refineText(ingredients)
  return ingredients, rank

# 최종 호출 함수 #
def naver_call_main():
  result_msg = "Raw csv export disabled"
  result_df = repeatMerge(keyword_start)
  for keyword in keywords:
    df = repeatMerge(keyword)
    result_df = pd.concat([result_df,df], ignore_index=True)

  # CSV파일로 내보내기
  if(savecsv == 1):
    result_df.to_csv(raw_csv_name)
    result_msg = "Raw csv export completed!"

  return result_msg

def ingredients_scrap_main():
  # DataFrame 가공
  df = pd.read_csv(raw_csv_path, index_col=0)
  df.drop(remove_indexes, axis=1, inplace=True)
  df['title'] = df['title'].apply(removeTag)
  df['ingredients'] = np.nan
  df['Rank'] = np.nan
  tqdm.pandas()
  df['ingredients'], df['Rank'] = zip(*df['productId'].progress_apply(getIngred))

  df.to_csv(smp_csv_name)
  return "Scrapped csv export completed!"

def removeNaN():
  df = pd.read_csv(smp_csv_path, index_col=0)
  df.dropna(subset=['ingredients'], inplace=True)
  df.reset_index(drop=True, inplace=True)
  df.rename(columns={'title':'Name', 'brand':'Brand', 'maker':'Company', 'ingredients':'Ingredients', 'productId':'NaverPID', 'lprice':'Price'},inplace=True)
  r_num = len(df)
  result_csv_name = f"data_{r_num}.csv"
  df.to_csv(result_csv_name)
  return "NaN removed."

# 메인 함수 #
if __name__=="__main__":
  call_api = naver_call_main()
  print(call_api)
  scrap_ingred = ingredients_scrap_main()
  print(scrap_ingred)
  result = removeNaN()
  print(result)