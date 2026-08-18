import re
import csv
import sys
from pathlib import Path
import sqlite3

# 이 파일은 pipeline/ 안에 있는데 app/config.py 를 가져다 쓴다.
# 파이썬은 "실행한 파일이 있는 폴더" 를 기준으로 모듈을 찾기 때문에,
# 프로젝트 뿌리를 검색 경로에 직접 넣어 줘야 한다
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 경로는 config.py 한 곳에서만 정한다. 여기서는 가져다 쓰기만 한다
from app.config import DATA_DIR, DB_PATH

# 이전에 만들어둔 DB파일이 있으면 지우고 매번 새로 생성
if DB_PATH.exists():
  DB_PATH.unlink()

con = sqlite3.connect(DB_PATH)
# FK 제약조건은 기본적으로 꺼져있어서 켜줘야 REFERENCES가 실제로 검증됨
con.execute("PRAGMA foreign_keys = ON")

# csv파일 내용 리스트 변환 함수
def read_csv(path):
  with open(path, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    return reader.fieldnames, list(reader)

# csv-레코드 정렬
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)

  # 각 csv파일의 첫번째의 모든 필드값 확인
  for column in columns:
    value = rows[0][column]


# 해당 값이 정수인지 확인하는 함수
def looks_int(text):
  # 음수부호 떼고 자릿수만 검사
  body = text[1:] if text.startswith("-") else text

  if not body.isdigit():
    return False
  # 2자리 이상인데 0으로 시작하면 전화번호 등으로 보고 정수 취급 안함
  return not (len(body) > 1 and body.startswith("0"))


# 소수 판별 함수
def looks_float(text):
  # 일단 float()로 변환되는지부터 확인
  try:
    float(text)

  except ValueError:
    return False

  # "1" 같은 정수문자열도 float() 변환은 되므로, 점이 있어야만 진짜 소수로 인정
  if "." not in text:
      return False

  return True


# 날짜 판별 함수
def looks_date(text):
  return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None

# 타입 추론 함수 생성
def infer_type(values):
  seen = [v for v in values if v!=""]

  if not seen: 
    return "TEXT"

  if all(looks_int(v) for v in seen):
    return "INTEGER"

  if all(looks_float(v) for v in seen):
    return "FLOAT"

  if all(looks_date(v) for v in seen):
    return "DATE"

  return "TEXT"


# 모든 csv파일을 하나씩 검사해서 컬럼명과 각 행의 값의 타입을 분석
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)

  for column in columns:
    kind = infer_type([r[column]  for r in rows]) 


# PK를 찾아주는 함수
def infer_pk(columns, rows):
  for col in columns:
    if not col.endswith("_id"):
      continue
  
    values = [r[col] for r in rows]
    if "" in values: 
      continue
   
    if len(set(values)) == len(values):
      return col
  return None

# 특정 PK의 주인 테이블 찾기
def owner_of(column, tables):
  # "product_id" -> "product" 로 뒤에 "_id" 3글자 제거
  stem = column[:-3]
  # 단수/복수(s, es) 다 시도해서 테이블 목록에 있는 이름 찾기
  for candidate in (stem, stem+"s", stem+"es") :
    if candidate in tables:
      return candidate

  return None


# 1.모든 테이블별 필드, 데이터타입, PK 구하기
tables = {}
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)
  tables[path.stem] = {
    "columns": columns,
    "rows":rows,
    "type": {col: infer_type([r[col] for r in rows]) for col in columns},
    "pk":infer_pk(columns, rows)
  }

# 2. 특정 테이블에 연결되어 있는 외래키 찾기
for name, table in tables.items(): 
  fks = []
  for col in table["columns"]:
    if not col.endswith("_id"):
      continue  
    owner= owner_of(col, tables)
  
    if not owner or owner == name:
      continue
  
    if tables[owner]["pk"] != col:
      continue

    fks.append(( col, owner))

  table["fks"] = fks


# CREATE TABLE문 문자열을 만들어주는 함수
def build_create(name, table):
  lines = []

  # 컬럼마다 "컬럼명 타입" 한줄씩 만들고, PK인 컬럼이면 뒤에 PRIMARY KEY 붙임
  for col in table["columns"]:
    piece = f"   {col} {table['type'][col]}"

    if col == table["pk"]:
      piece += " PRIMARY KEY"

    lines.append(piece)

  # FK로 잡힌 컬럼마다 FOREIGN KEY 제약조건 줄 추가
  for col, owner in table["fks"]:
    lines.append(f"   FOREIGN KEY ({col}) REFERENCES {owner}({col})")

  return f"CREATE TABLE {name} (\n"+ ",\n".join(lines) + "\n)"


# 테이블 생성 순서 지정을 위한 함수
# FK가 가리키는 부모테이블이 먼저 done에 들어가야 자식테이블을 order에 넣는 방식 (위상정렬)
def sort_by_dependency(tables):
  done = set()  # 순서 정해진 테이블 이름 모음
  order = []  # 실제 생성순서 리스트

  while len(order) < len(tables):
    moved = False  # 이번 바퀴에 하나라도 order에 추가됐는지 체크

    for name, table in tables.items():
      if name in done:
        continue

      # 이 테이블의 FK가 참조하는 부모테이블들이 전부 done이면 이제 만들어도 됨
      if all(owner in done for _, owner in table["fks"]):
        order.append(name)
        done.add(name)
        moved = True

    # 한바퀴 돌았는데 아무것도 못넣었으면(순환참조 등) 남은거 그냥 다 붙이고 종료
    if not moved:
      order += [n for n in tables if n not in done]
      break

  return order

table_order = sort_by_dependency(tables)

# 각 필드의 데이터의 타입에 맞게 변환해주는 함수
def convert(value, kind):
  if value == "":
    return None

  if kind == "INTEGER":
    return int(value)

  if kind == "FLOAT":
    return float(value)

  return value

# 앞에서 정산 테이블 생성 순서대로 데이터 저장
# execute() 괄호안에는 SQL문 1개만 들어감 (테이블생성, 인덱스생성에 사용)
# executemany() 괄호안에는 SQL문 1개 + 값 리스트(튜플 여러개) 이렇게 2개가 들어감, values 개수만큼 INSERT 반복실행
# 진행순서: 테이블생성(execute) -> 값변환 -> INSERT(executemany) -> FK인덱스생성(execute) -> commit(확정저장)

for name in table_order:
  table = tables[name]
  con.execute(build_create(name, table))

  columns = table["columns"]

  placeholders = ", ".join("?" for _ in columns)

  values = [
    tuple(convert(row[col], table["type"][col]) for col in columns)
    for row in table["rows"]
  ]

  con.executemany(f"INSERT INTO {name} ({", ".join(columns)}) VALUES ({placeholders})", values,)

  for col, _owner in table["fks"]:
    con.execute(f"CREATE INDEX idx_{name}_{col} on {name}({col})")
con.commit()