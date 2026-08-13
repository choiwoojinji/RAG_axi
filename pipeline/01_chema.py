import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
# 인자로 csv파일이 있는 패스경로를 전달하면 각 파일의 필드명만 리스트형태로 반환하는 함수
def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader) # 필드명으로 반환 

# csv 를 반복돌며 read_csv 호출해서 각파일당 필드데이터와 로우데이터 정보를 출력하는 실행문
for path in sorted(DATA_DIR.glob('*.csv')):
    columns, rows = read_csv(path)
#실제 각 csv파일의 필드명 확인
    for column in columns:
        value = rows[0][column] # 각csv파일의 첫번째 모든 필드값을 확인
        print(value)