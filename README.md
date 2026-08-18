# axi-ai

CSV 파일 여러 개를 읽어서 **하나의 SQLite 데이터베이스**로 만들어주는 프로젝트입니다.
컬럼의 데이터 타입, 기본키(PK), 테이블 사이의 관계(FK)를 **자동으로 추측**해서 테이블을 만들어 줍니다.

---

## 1. 폴더 구조

```
axi-ai/
├── app/
│   └── config.py        # 프로그램 전체가 함께 쓰는 설정값
├── data/                # 원본 CSV 파일들
│   ├── customers.csv
│   ├── products.csv
│   ├── product_details.csv
│   └── purchases.csv
└── pipeline/
    └── 01_schema.py     # CSV → SQLite DB 변환 스크립트
```

---

## 2. 용어 미리 알기 (초보자용)

| 용어               | 쉬운 설명                                                                             |
| ------------------ | ------------------------------------------------------------------------------------- |
| **테이블(Table)**  | 엑셀의 시트 한 장. CSV 파일 하나가 테이블 하나가 됩니다.                              |
| **컬럼(Column)**   | 엑셀의 세로 열. `name`, `price` 같은 항목 이름.                                       |
| **행(Row)**        | 엑셀의 가로 줄. 데이터 한 건.                                                         |
| **타입(Type)**     | 그 컬럼에 들어가는 값의 종류 (숫자인지, 글자인지, 날짜인지).                          |
| **기본키(PK)**     | 각 행을 하나로 구분해주는 컬럼. 예: `customer_id` (고객마다 값이 다르고 중복이 없음). |
| **외래키(FK)**     | 다른 테이블을 가리키는 컬럼. 예: `purchases.customer_id` → `customers` 테이블.        |
| **스키마(Schema)** | 테이블의 설계도. "어떤 컬럼이 무슨 타입으로 있는가".                                  |

---

## 3. `app/config.py` — 설정 파일

프로그램 전체가 함께 쓰는 값을 한곳에 모아두는 파일입니다.
값이 바뀌면 여기만 고치면 되도록 만든 것입니다.

### 경로 설정

| 이름       | 설명                                           |
| ---------- | ---------------------------------------------- |
| `ROOT`     | 작업 폴더(프로젝트)의 최상위 경로              |
| `DATA_DIR` | 원본 CSV 파일들이 들어 있는 폴더 경로          |
| `DB_PATH`  | CSV를 변환해서 만들어 낼 SQLite DB 파일의 경로 |

### 임베딩 설정 (등록 예정)

텍스트를 숫자 벡터로 바꾸는 작업(**벡터라이징**)에 쓰일 설정입니다.

| 이름               | 설명                                               |
| ------------------ | -------------------------------------------------- |
| `EMBED_TOKENIZER`  | 텍스트를 벡터로 바꿀 때 사용할 임베딩 모델 이름    |
| `EMBED_MAX_TOKENS` | 그 임베딩 모델이 한 번에 받을 수 있는 최대 토큰 수 |

---

## 4. `pipeline/01_schema.py` — CSV를 DB로 바꾸는 스크립트

### 4-1. 전체 실행 흐름

```
[1] DATA_DIR 안의 모든 CSV 파일 찾기
        ↓
[2] read_csv() 로 각 CSV의 컬럼명과 행을 읽기
        ↓
[3] infer_type() / infer_pk() 로 컬럼 타입과 기본키(PK) 추측
        ↓
[4] 결과를 tables 딕셔너리에 테이블별로 모으기
        ↓
[5] owner_of() 로 테이블 사이의 외래키(FK) 관계 찾아서 추가
        ↓
[6] sort_by_dependency() 로 부모 테이블부터 처리할 순서 만들기
        ↓
[7] build_create() 로 CREATE TABLE SQL을 만들어 테이블 생성
        ↓
[8] convert() 로 CSV 값을 타입에 맞게 바꾸고 INSERT
        ↓
[9] FK 컬럼에 인덱스를 만들고 commit → DB_PATH에 저장
```

정리하면 이렇습니다.

> 여러 개의 CSV 파일
> → 컬럼 타입 · PK · FK 분석
> → 테이블 생성 및 데이터 삽입
> → `DB_PATH` 위치에 SQLite DB 파일 하나 완성

### 4-2. 함수 목록

#### 읽기

**`read_csv(path)`** — CSV 한 개를 읽어 옵니다.

- 전달값: `path` — 읽을 CSV 파일의 경로
- 반환값: `(컬럼명 목록, 전체 행 목록)`

#### 타입 판별 (이 값이 무슨 종류인지 확인)

**`looks_int(text)`** — 문자열이 정수로 저장하기 적합한지 확인

- 전달값: `text` — CSV에서 읽은 문자열 하나
- 반환값: 정수로 저장할 수 있으면 `True`, 아니면 `False`

**`looks_float(text)`** — 문자열이 소수로 저장하기 적합한지 확인

- 전달값: `text` — CSV에서 읽은 문자열 하나
- 반환값: 소수로 저장할 수 있으면 `True`, 아니면 `False`

**`looks_date(text)`** — 문자열이 `YYYY-MM-DD` 형식의 날짜인지 확인

- 전달값: `text` — CSV에서 읽은 문자열 하나
- 반환값: `YYYY-MM-DD` 형식이면 `True`, 아니면 `False`

**`infer_type(values)`** — 한 컬럼의 값들을 전부 검사해서 그 컬럼의 타입을 정합니다.

- 전달값: `values` — 한 컬럼에 들어 있는 모든 문자열 값의 목록
- 반환값: `"INTEGER"`, `"FLOAT"`, `"DATE"`, `"TEXT"` 중 하나

#### 키(Key) 찾기

**`infer_pk(columns, rows)`** — 각 행을 유일하게 구분할 수 있는 기본키(PK) 컬럼을 찾습니다.

- 전달값: `columns` — 컬럼명 목록 / `rows` — 전체 행 목록
- 반환값: PK로 판단한 컬럼명, 찾지 못하면 `None`

**`owner_of(column, tables)`** — 어떤 외래키(FK) 후보 컬럼이 어느 테이블을 가리키는지 찾습니다.

- 전달값: `column` — FK 후보 컬럼명 / `tables` — 전체 테이블 정보
- 반환값: 해당 컬럼이 가리키는 테이블명, 찾지 못하면 `None`

#### 테이블 만들기

**`build_create(name, table)`** — 분석한 컬럼·타입·PK·FK 정보로 `CREATE TABLE` SQL문을 만듭니다.

- 전달값: `name` — 테이블명 / `table` — 해당 테이블의 분석 정보
- 반환값: 테이블을 생성할 `CREATE TABLE` SQL 문자열

**`sort_by_dependency(tables)`** — 참조되는 부모 테이블이 먼저 만들어지도록 테이블 순서를 정합니다.

- 전달값: `tables` — 전체 테이블 정보
- 반환값: 부모 테이블부터 정렬된 테이블명 목록
- 왜 필요한가요? `purchases`가 `customers`를 참조하는데 `customers`가 아직 없으면 테이블을 만들 수 없기 때문입니다.

#### 값 변환

**`convert(value, kind)`** — CSV의 문자열 값을 DB 컬럼 타입에 맞는 파이썬 값으로 바꿉니다.

- 전달값: `value` — CSV 문자열 값 / `kind` — 저장할 데이터 타입
- 반환값: 타입에 맞게 변환된 `int`, `float`, 문자열 또는 `None`
- 왜 필요한가요? CSV는 모든 값이 글자(문자열)입니다. `"25400"`을 숫자 `25400`으로 바꿔야 DB에서 계산·정렬을 제대로 할 수 있습니다.

---

## 5. 데이터 예시

`data/` 폴더의 CSV들은 대략 이런 관계입니다.

```
customers (고객)              products (상품)
  customer_id (PK)              product_id (PK)
        ▲                             ▲
        │                             │
        └──────┬──────────────────────┘
               │
          purchases (구매)          product_details (상품 상세)
            purchase_id (PK)          product_id (PK, FK → products)
            customer_id (FK)
            product_id  (FK)
```

- `customers.csv` — 고객 정보 (`customer_id`, `name`, `age`, `skin_type` 등)
- `products.csv` — 상품 정보 (`product_id`, `name`, `brand`, `price` 등)
- `product_details.csv` — 상품 상세 설명 (`product_id`, `detail`)
- `purchases.csv` — 구매 내역 (`purchase_id`, `customer_id`, `product_id`, `rating`, `review` 등)

`customer_id`, `product_id`처럼 **다른 테이블의 PK와 이름이 같은 컬럼**을 스크립트가 찾아서 FK로 연결해 줍니다.

### 각 테이블 생성 sql문 (테이블 필드명 및 데이터 타입 확인용도)

```
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT,
    gender TEXT,
    age INTEGER,
    skin_type TEXT,
    phone TEXT,
    email TEXT,
    city TEXT,
    joined_at DATE
)
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    name TEXT,
    brand TEXT,
    category TEXT,
    price INTEGER,
    volume TEXT,
    skin_type TEXT,
    ingredient TEXT,
    concern TEXT,
    tags TEXT,
    description TEXT
)
CREATE TABLE purchases (
    purchase_id TEXT PRIMARY KEY,
    customer_id TEXT,
    product_id TEXT,
    purchased_at DATE,
    quantity INTEGER,
    rating INTEGER,
    review TEXT,
    is_holdout INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)
CREATE TABLE product_details (
    product_id TEXT PRIMARY KEY,
    detail TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)
```

---

## 6. 실행 방법

**반드시 프로젝트 루트(`axi-ai/`)에서** 아래 명령으로 실행합니다.

```bash
python -m pipeline.01_schema
```

실행이 끝나면 `config.py`의 `DB_PATH` 위치에 SQLite DB 파일이 생성됩니다.

### 왜 `python pipeline/01_schema.py`가 아니라 `python -m` 인가요?

`-m`은 "파일을 직접 실행"하는 게 아니라 **모듈로 불러와서 실행**하라는 뜻입니다.
이 방식을 쓰면 항상 루트에서 명령을 치게 되고, 거기서 두 가지 이점이 생깁니다.

**1) 매번 하위 폴더로 이동할 필요가 없습니다**

```bash
# 이렇게 왔다 갔다 할 필요 없이
cd pipeline
python 01_schema.py
cd ..

# 루트에 그대로 있으면서 실행
python -m pipeline.01_schema
```

터미널의 현재 위치가 항상 루트로 고정되므로, `config.py`의 `ROOT`·`DATA_DIR`·`DB_PATH` 같은
경로도 매번 같은 기준에서 동작합니다. 어디서 실행했느냐에 따라 파일을 못 찾는 문제가 생기지 않습니다.

**2) 실수로 인한 잘못된 git commit을 막아줍니다**

터미널이 하위 폴더(`pipeline/`)에 들어가 있는 상태에서 아무 생각 없이 아래처럼 커밋하면,
**그 폴더 안의 변경사항만** 커밋되고 상위 폴더(`app/`, `data/` 등)의 변경사항은 빠집니다.

```bash
cd pipeline
git add .        # ← pipeline/ 안의 변경사항만 스테이징됨
git commit -m "작업"
```

`git add .`와 `git commit .`의 `.`은 "저장소 전체"가 아니라 **"지금 있는 폴더 아래"** 를 뜻하기 때문입니다.
루트에 머물러 있으면 `.`이 곧 저장소 전체가 되므로 이런 누락이 생기지 않습니다.

> 참고: `git status`나 옵션 없는 `git commit -m "..."`은 하위 폴더에서 실행해도 저장소 전체를 기준으로 동작합니다.
> 문제가 되는 건 위처럼 `.`(현재 폴더)을 경로로 넘기는 경우입니다.

### 실행 전 확인

- 터미널 프롬프트의 경로가 `.../axi-ai` 인지 확인하세요.
- 모듈명에 `.py`는 붙이지 않습니다. (`pipeline.01_schema` ○ / `pipeline.01_schema.py` ✗)
- 폴더 구분은 `/`가 아니라 `.`을 씁니다. (`pipeline.01_schema` ○ / `pipeline/01_schema` ✗)
