import re # 정규표현식 검사하는 파이썬 패키지 
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

# 제일기본 text 인자값들어오는게 int 인지
def looks_int(text):
    body = text[1:] if text.startswith('-') else text # 만약 음수부호 - 섞여있다면 
    if not body.isdigit():
        # 0~9 가 아닌 글자가 섞여있다면 
        print('정수가 아님')
        return False # 정수가아니고 # 만약 정수일때 앞자리가 0시작이면 전화번호로 인지하기
    #                                     위해 len길이 두자리 이상으로 설정
    return not (len(body) > 1 and body.startswith('0'))

looks_int('010')

def looks_float(text): # 실수판변하는 함수입니다 
    try:
        float(text) # 점이두개면 실수일리가없어서 밸류에러로 가서 false됨 

    except ValueError: 
        return 'False'
    
    if'.'not in text:
            return False
    
    return True # 위의 모든 예의 사항 통과하면 애는 무조건 실수 

print(looks_float('3..3'))

def looks_date(text): # 날짜판변함수 # fullmatch(검증할 정규표현식, 검사할문자값)
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None
# 정규표현식 \d 숫자고 각 연월일임

print(looks_date('2025-03-04'))