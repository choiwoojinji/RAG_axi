import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'

def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader) # 필드명으로 반환 

# csv 를 반복돌며 read_csv 호출해서 각파일당 필드데이터와 로우데이터 정보를 출력하는 실행문
for path in sorted(DATA_DIR.glob('*.csv')):
    columns, rows = read_csv(path)
    print(f'\n{path.name} - {len(rows):,}행 - {len(columns)}열')