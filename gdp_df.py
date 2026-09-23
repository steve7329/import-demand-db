import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import pycountry

# base_url을 기본 awd rds 서버로 설정하고 url로 연걸하는 base_engine 생성
base_url = 'mysql+pymysql://admin:dhgkqwlwhf5@import-demand-server.cqr8wgqy24po.us-east-1.rds.amazonaws.com:3306/'
base_engine = create_engine(base_url, connect_args={'ssl': {'ca': './global-bundle.pem'}})

# 엔진이 연결 됐으면 SQL QUREY문 실행
with base_engine.connect() as conn:
    conn.execute(text("CREATE DATABASE IF NOT EXISTS import_demand_db;"))

# 쿼리문으로 생성된 데이터베이스로 url 설정하고 url로 연걸하는 engine 생성
db_connection_url = 'mysql+pymysql://admin:dhgkqwlwhf5@import-demand-server.cqr8wgqy24po.us-east-1.rds.amazonaws.com:3306/import_demand_db'
engine = create_engine(
    db_connection_url,
    connect_args={'ssl': {'ca': './global-bundle.pem'}}
)

# 이 과정이 끝났으면 코드 파일이 aws rds 서버 안에 생성된 data base에 연결 된 것

file_path = 'data/SIPRI-Milex-data-1949-2025_v1.2.xlsx'

# 6번째 행부터 데이터가 시작 -> header = 5
df_usd_raw = pd.read_excel(file_path, sheet_name = 'Current US$', header = 5)
df_share_raw = pd.read_excel(file_path, sheet_name = 'Share of GDP', header = 5)

# 국가명이 없는 빈 행 삭제
df_usd_raw = df_usd_raw.dropna(subset = ['Country'])
df_share_raw = df_share_raw.dropna(subset = ['Country'])

# 대륙명만 적혀 있는 무의미한 행 삭제
drop = [
    'Africa', 'North Africa', 'sub-Saharan Africa', 
    'Americas', 'Central America and the Caribbean', 'North America', 'South America', 
    'Asia & Oceania', 'Oceania', 'South Asia', 'East Asia', 'South East Asia', 'Central Asia', 
    'Europe', 'Central Europe', 'Eastern Europe', 'Western Europe', 
    'Middle East', 'European Union'
]

df_usd_raw = df_usd_raw[~df_usd_raw['Country'].isin(drop)]
df_share_raw = df_share_raw[~df_share_raw['Country'].isin(drop)]

def get_iso3(country_name):
    special_mapping = {
        'Korea, South': 'KOR', 'Korea, North': 'PRK', 'United States of America': 'USA',
        'Türkiye': 'TUR', 'Congo, DR': 'COD', 'Congo, Republic': 'COG',
        'Gambia, The': 'GMB', 'Eswatini': 'SWZ', 'Timor Leste': 'TLS',
        'Cape Verde': 'CPV', 'Kyrgyz Republic': 'KGZ', 'Bosnia and Herzegovina': 'BIH',
        'USSR': 'SUN', 'Yugoslavia': 'YUG', 'Czechoslovakia': 'CSK', 
        'German Democratic Republic': 'DDR', 'Yemen, North': 'YEM'
    }
    
    if country_name in special_mapping:
        return special_mapping[country_name]
    try:
        # pycountry를 활용해 정확한 이름 탐색 후 ISO3 반환
        res = pycountry.countries.get(name=country_name)
        if res: return res.alpha_3
        # 이름이 약간 다를 경우 유사도 검색(fuzzy)
        return pycountry.countries.search_fuzzy(country_name)[0].alpha_3
    except:
        # 매핑 불가능한 국가는 None
        return None

# 4. Iso3 컬럼을 테이블의 가장 첫 번째 열(index 0)에 삽입
print("국가 코드를 매핑하는 중입니다...")
df_usd_raw.insert(0, 'Iso3', df_usd_raw['Country'].apply(get_iso3))
df_share_raw.insert(0, 'Iso3', df_share_raw['Country'].apply(get_iso3))

# GDP 계산 및 결측치 행 제거
# 연도(정수형) 컬럼만 추출
years = [col for col in df_usd_raw.columns if isinstance(col, int)]

# Country를 인덱스로 지정
df_usd_calc = df_usd_raw[['Iso3', 'Country'] + years].copy().set_index(['Iso3', 'Country'])
df_share_calc = df_share_raw[['Iso3', 'Country'] + years].copy().set_index(['Iso3', 'Country']) 

# 특수문자('. .', 'xxx' 등)를 결측치(NaN)로 변환 후 숫자형으로 변경
df_usd_calc = df_usd_calc.replace(['. .', 'xxx', '-', '...'], np.nan).apply(pd.to_numeric, errors='coerce')
df_share_calc = df_share_calc.replace(['. .', 'xxx', '-', '...'], np.nan).apply(pd.to_numeric, errors='coerce')

# GDP = (1 / Share of GDP) * Current US$
df_gdp = (1 / df_share_calc) * df_usd_calc
df_gdp = df_gdp.replace([np.inf, -np.inf], np.nan)    # 혹시 inf 나오면 NaN으로 대체

# 데이터를 DB의 테이블로 각각 삽입
# 삽입 전 컬럼명을 모두 문자열(str)로 변환
df_usd_final = df_usd_calc.reset_index()
df_usd_final.columns = [str(c) for c in df_usd_final.columns]
df_usd_final.to_sql(name='current_usd', con=engine, if_exists='replace', index=False)

df_share_final = df_share_calc.reset_index()
df_share_final.columns = [str(c) for c in df_share_final.columns]
df_share_final.to_sql(name='share_gdp', con=engine, if_exists='replace', index=False)

print("원본 시트 2개가 DB 테이블로 삽입되었습니다.")

df_gdp_final = df_gdp.reset_index()
df_gdp_final.columns = [str(c) for c in df_gdp_final.columns]

df_gdp_final.to_sql(name='gdp_calculated', con=engine, if_exists='replace', index=False)

print("GDP 테이블(gdp_calculated)이 DB에 성공적으로 생성되었습니다.")
