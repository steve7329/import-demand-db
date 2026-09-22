import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

base_url = 'mysql+pymysql://admin:dhgkqwlwhf5@import-demand-server.cqr8wgqy24po.us-east-1.rds.amazonaws.com:3306/'
base_engine = create_engine(base_url, connect_args={'ssl': {'ca': './global-bundle.pem'}})

with base_engine.connect() as conn:
    conn.execute(text("CREATE DATABASE IF NOT EXISTS import_demand_db;"))

db_connection_url = 'mysql+pymysql://admin:dhgkqwlwhf5@import-demand-server.cqr8wgqy24po.us-east-1.rds.amazonaws.com:3306/import_demand_db'
engine = create_engine(
    db_connection_url,
    connect_args={'ssl': {'ca': './global-bundle.pem'}}
)


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


# GDP 계산 및 결측치 행 제거
# 연도(정수형) 컬럼만 추출
years = [col for col in df_usd_raw.columns if isinstance(col, int)]

# Country를 인덱스로 지정
df_usd_calc = df_usd_raw[['Country'] + years].copy().set_index('Country')
df_share_calc = df_share_raw[['Country'] + years].copy().set_index('Country') 

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