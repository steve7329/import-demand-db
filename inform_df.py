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


file_path = 'data/INFORM2026_TREND_2017_2026_v72_ALL.xlsx'

df = pd.read_excel(file_path, sheet_name='INFORM2026Trend')

df_hazard = df[df['IndicatorName'] == 'Human Hazard'].copy()

df_hazard.columns = df_hazard.columns.str.replace(' ', '_')

df_hazard.to_sql(
    name='human_hazard_trend',
    con=engine,
    if_exists='replace',
    index=False
)

print("분쟁 위험도 테이블(human_hazard_trend)이 DB에 성공적으로 생성되었습니다.")