import numpy as np
import pandas as pd
import pycountry

df = pd.read_csv(
    "trade-register.csv",
    skiprows=11,
    encoding="cp1252"
)

arms_year = (
    df.groupby(["Recipient", "Delivery year"])
      ["TIV delivery values"]
      .sum()
      .reset_index()
)

arms_year.columns = [
    "Country",
    "Year",
    "Arms_Import_TIV"
]

arms_year.to_csv(
    'arms_year.csv',
    index=False,
    encoding='utf-8-sig'
)

print('저장 완료: arms_year.csv')

# pycountry에서 바로 인식되지 않는 실제 국가 이름 보정
country_alias = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Brunei": "Brunei Darussalam",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "DR Congo": "Congo, The Democratic Republic of the",
    "Russia": "Russian Federation",
    "Turkiye": "Turkey",
    "Palestine": "Palestine, State of",
}

# 국가명을 ISO3 코드로 변환하는 함수
def get_country_code(country_name):
    
    # 별칭이 있으면 정식 국가명으로 변경
    search_name = country_alias.get(country_name, country_name)

    try:
        country = pycountry.countries.lookup(search_name)
        return country.alpha_3
    
    except LookupError:
        return None

df2 = pd.read_csv("arms_year.csv")

df2["Country_Code"] = df2["Country"].apply(get_country_code)

df2.to_csv(
    'df2.csv',
    index=False,
    encoding='utf-8-sig'
)

print('저장 완료: df2.csv')

# 국가코드가 없는 행 = 실제 국가가 아닌 것으로 보고 삭제
df2 = df2.dropna(subset=["Country_Code"]).reset_index(drop=True)


# 국가 × 연도 표로 펼치기 (수입 없는 해는 0)
tiv_wide = df2.pivot_table(index='Country_Code', columns='Year',
                          values='Arms_Import_TIV', aggfunc='sum', fill_value=0)

# 끝연도 기준 5년 TIV 합계 (예: 2025년 = 2021~2025 합)
first_year = tiv_wide.columns.min()
rows = []
for end in tiv_wide.columns:
    start = end - 4
    if start < first_year:   # 5년 못채우면 건너뛰기 (2000~2003)
        continue
    s = tiv_wide.loc[:, start:end].sum(axis=1)
    rows.append(pd.DataFrame({
        'Country_Code': s.index,
        'Year': end,
        'Window': f'{start}-{end}',
        'TIV_5Y_Sum': s.values
    }))
tiv_5y = pd.concat(rows, ignore_index=True)


# 전 세계 5년 합으로 나눠 점유율 계산
tiv_5y['World_TIV_5Y_Sum'] = tiv_5y.groupby('Year')['TIV_5Y_Sum'].transform('sum')
tiv_5y['TIV_5Y_Share'] = tiv_5y['TIV_5Y_Sum'] / tiv_5y['World_TIV_5Y_Sum'] * 100

# 원본에 결합
merged = df2.merge(tiv_5y, on=['Country_Code', 'Year'], how='left')

merged.to_csv(
    'merged.csv',
    index=False,
    encoding='utf-8-sig'
)

print('저장 완료: merged.csv')