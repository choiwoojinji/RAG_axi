import sqlite3
import statistics
import sys
from pathlib import Path

# ========================================
#  우선 루트경로 지정 및 필수 메서드 import
# ========================================

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(errors="replace")

from transformers import logging as hf_logging

hf_logging.set_verbosity_error()

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from transformers import AutoTokenizer

from app.config import DB_PATH, EMBED_TOKENIZER, EMBED_MAX_TOKENS
from app.db import query

tok = AutoTokenizer.from_pretrained(EMBED_TOKENIZER)

# ========================================
#  커스텀 함수 정의
# ========================================
def ntok(text):
  return len(tok.encode(text))

def dist(values):
  return (f"최소 {min(values)} / 중앙 {int(statistics.median(values))} / 최대 {max(values)}")

# 접두어를 포함시켜 본문 생성 함수 (모델에게 전달하는 데이터의 문맥을 빠르게 파악시키기 위함)
# 세번째로 전달되는 인자값은 2차 청킹된 데이터가 1차 청킹만 완료된 본문
def with_context(pname, section, body):
  return f"[{pname} > {section}] {body}"

# [스킨로션 > 주의사항] 어쩌구 이렇게 써야됩니다.


# ================================================
#  필수 조절값 (실무에선 이 수치값만 조절해서 업무 활용 가능)
# ================================================
CHUNK_SIZE = 324
CHUNK_OVERLAP = 48 
PREFIX_BUDGET = 32 # [제품명 > 중제목]
RESPLIT_OVER = EMBED_MAX_TOKENS - PREFIX_BUDGET
HEADERS = [("##", "section")] 
SEPERATORS = ["\n\n", "\n", "다", "요", ".", ",", ""]



# ================================================
#  청킹할 데이터 원본을 DB 테이블엥서 꺼냄
# ================================================
details = query("""
  SELECT product_details.product_id, products.name, product_details.detail
  FROM product_details JOIN products ON product_details.product_id = products.product_id
  ORDER BY product_details.product_id
""")


# ================================================
#  추출한 데이터의 토큰 갯수 알아내기
# ================================================
full_tokens = [ntok(detail) for _, _, detail in details]
over = [n for n in full_tokens if n > EMBED_MAX_TOKENS ]



# ================================================
#  1차 청킹 시작 : md파일의 제목을 기준으로 청킹
# ================================================
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)
sections = []

for pid, pname, detail in details:
  for doc in md_splitter.split_text(detail):
    text = doc.page_content.strip() 
    if not text:
      continue
    sections.append((pid, pname, doc.metadata.get("section", "(머릿말)"), text))


# ==========================================================================
#  2차 청킹 시작 : 1차 청킹이후 추가 청킹이 필요할때 SEPARATOR, CHUNK_SIZE 기준으로 청킹
# ==========================================================================
resplitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
  tok, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=SEPERATORS, keep_separator="end"
)

rows = [] 
n_resplit = 0

for pid, pname, section, text in sections:
  if ntok(text) > RESPLIT_OVER:
    n_resplit +=1
    parts = resplitter.split_text(text)  
  else:
    parts = [text]  

  for i, part in enumerate(parts):
    rows.append((pid, pname, section, i, part))

# ===================================
#  화면에 출력할 원본 데이터테이블,
#  검색을 위한 청킹 데이터가 들어갈 테이블
#  청킹데이터의 좌표값이 들어갈 테이블 생성구문
# ====================================
con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")

# 테이블이 만들어지는 순서는 section -> chunks -> chunk_vectors순이기 때문에
# 테이블 제거시에는 역순으로 제거
con.execute("DROP TABLE IF EXISTS chunk_vectors") # 의미추론을 위한 조각들의 좌표값이 들어가는 테이블
con.execute("DROP TABLE IF EXISTS chunks") # 사용자 요청시 빠르게 문맥에 맞는 키워드를 탐색하기 위한 조각들 저장 테이블 
con.execute("DROP TABLE IF EXISTS sections") # LLM이 참고해야 되는 원문이 들어가는 테이블

con.execute("""
  CREATE TABLE sections (
    section_id   INTEGER PRIMARY KEY,  --자동으로 들어가는 값 레코드가 추가될때마다 1씩 자동카운트
    product_id   TEXT NOT NULL,        --어느 상품인지
    section      TEXT NOT NULL,        --'주의사항' 같은 항 섹션별 제목
    body         TEXT NOT NULL,        --접두어가 붙기전의 원문 (통짜 원문이 아닌 1차 청킹 이후 제목뒤의 본문)
    n_tokens     INTEGER NOT NULL,     --(필요없을 수도 있음)
    FOREIGN KEY (product_id) REFERENCES products(product_id)
  )
""")

con.execute("""
  CREATE TABLE chunks (
    chunk_id     INTEGER PRIMARY KEY,   --자동으로 들어가는 각 레코드 PK  
    section_id   INTEGER NOT NULL,      --해당 청킹된 조각이 바라보는 섹션 테이블 아이디
    product_id   TEXT NOT NULL,         --해당 청킹된 조각이 바라보는 제품 아이디
    section      TEXT NOT NULL,         --'주의사항' 같은 항 섹션별 제목
    text         TEXT NOT NULL,         --접두어가 붙기전의 원문 (검색용도)
    body         TEXT NOT NULL,         --접두어가 붙은 짤리지 않은 원문 (검색 키워드가 매칭되는 원문 탐색하기 위한)
    n_tokens     INTEGER NOT NULL,
    FOREIGN KEY (section_id) REFERENCES sections(section_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
  )
""")

# 생성된 테이블의 외래키 컬럼에 index 추가
con.execute("CREATE INDEX idx_chunks_proudct_id ON chunks(product_id)")
con.execute("CREATE INDEX idx_sections_proudct_id ON chunks(product_id)")


# ===================================
#  테이블에 데이터 저장
# ====================================
# sections 테이블에 데이터 저장
section_id_of = {}
# {
#   ("P001","제품설명"):1,
#   ("P001","주의사항"):2,
#   ("P001","성분"):3,
# }

# sections테이블과 chunks 테이블을 조인시키지 않으면 연결시킬수 있는 접점이 없음
# 2개 테이블에 접점일수 있는 부분은 동일하게 들어가는 컬럼명인 pid, section밖에 없음
# 저 두개의 값을 키로 활용하는 공통의 접점을 생성
# section 테이블에서 필드값에 숫자는 무조건 정수인 PK가 지정되어 있기 때문에 공통의 컬럼값을 매칭처리 필요 (pic, section)

# 이렇게 번거롭게 sections테이블과 chunks 테이블을 연결하는 이유
# 테이블에서 원본 데이터를 꺼낸이후에 청킹을 시작하면 문제가 안되지만
# 유지보수의 편의성을 위해서 실제 DB에 데이터를 저장하기 전에 청킹과 벡터라이징을 미리 끝내놓은 상태
# 이때 청킹이 완료된 상태이기 때문에 저 2개의 테이블은 연결할 방법이 없음 
# 이떄 유일한 접점이 (상품아이디와 상품의 섹션 제목) 해당 필드가 공통으로 공유하는 값이 청킹 데이터가 봐라바야될 원본 테이블의 행

for pid, _pname, section, text in sections:
  cur = con.execute(
    "INSERT INTO sections (product_id, section, body, n_tokens) VALUES (?,?,?,?)",
    (pid, section, text, ntok(text)),
  )
  # sections와 chunks 테이블을 연결할 공통의 id값 
  section_id_of[(pid, section)] = cur.lastrowid

# chunks 테이블에 데이터 저장
for pid, pname, section, chunk_index, body in rows:
  text = with_context(pname, section, part)
  con.execute("""
    INSERT INTO chunks (section_id, product_id, section, chunk_index, text, body, n_tokens)
    VALUES (?,?,?,?,?,?,?)""", (section_id_of[(pid, section)], pid, section, chunk_index, text, text, ntok(part)  ),
  )

con.commit()


# =============================================
#  임베딩이 없을때 데이터 검색의 한계 
# =============================================





