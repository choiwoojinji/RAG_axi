"""긴 글을 조각으로 자른다. **이 파일은 데이터베이스를 모른다.**

  들어오는 것   [(상품번호, 상품명, 상세 원문), ...]   ― 그냥 파이썬 목록
  나가는 것     (섹션 목록, 조각 목록)                 ― 그냥 딕셔너리 목록

  `import sqlite3` 이 없다. 커넥션도 안 받는다. 일부러 그렇다.
  그래서 이 파일은 DB 없이 시험할 수 있다.

자르는 순서는 어제와 같은 2단이다.
  1단  '## 주의사항' 같은 사람이 만든 경계로 자른다
  2단  그래도 상한을 넘는 것만 다시 자른다

조절값은 전부 options.py 에 있다. 이 파일에는 숫자가 없다.
"""

from langchain_text_splitters import (MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter)
from transformers import AutoTokenizer

from app.core.config import EMBED_TOKENIZER
from pipeline.prep.options import (CHUNK_OVERLAP, CHUNK_SIZE, HEADERS, RESPLIT_OVER, SEPARATORS)

_tokenizer = None


def get_tokenizer():
  """토큰을 세는 자. 무거우니 한 번만 올리고 계속 쓴다."""
  global _tokenizer
  if _tokenizer is None:
    _tokenizer = AutoTokenizer.from_pretrained(EMBED_TOKENIZER)
  return _tokenizer


def count_tokens(text):
  """토큰 수 (2일차 1교시)."""
  return len(get_tokenizer().encode(text))


def with_context(product_name, section, body):
  """[상품명 > 섹션] 본문 ― 접두어가 곧 문맥이다 (2일차 3교시)."""
  return f"[{product_name} > {section}] {body}"


def split_sections(details):
  """1단 ― 사람이 만든 경계로 자른다.

  🔴 어제와 달라진 것: 튜플이 아니라 **딕셔너리**를 돌려준다.
      storage.py 가 chunking.py 를 안 읽고도 무엇이 오는지 알아야 하기 때문이다.
  """
  splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)

  sections = []
  for product_id, product_name, detail in details:
    for doc in splitter.split_text(detail):
      text = doc.page_content.strip()
      if not text:
        continue
      sections.append({
        "product_id": product_id,
        "product_name": product_name,
        "section": doc.metadata.get("section", "(머리말)"),
        "text": text,
        "n_tokens": count_tokens(text),
      })
  return sections


def split_chunks(sections):
  """2단 ― 상한을 넘는 섹션만 다시 자르고, 접두어를 붙인다.

  body  접두어를 뺀 원문 조각   ― 화면에 띄울 때 쓴다
  text  접두어를 붙인 것        ― 임베딩에 넣는다
  """
  resplitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
    get_tokenizer(), chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
    separators=SEPARATORS, keep_separator="end")

  chunks, n_resplit = [], 0
  for section in sections:
    if section["n_tokens"] > RESPLIT_OVER:
      n_resplit += 1
      parts = resplitter.split_text(section["text"])
    else:
      parts = [section["text"]]

    for chunk_index, body in enumerate(parts):
      text = with_context(section["product_name"], section["section"], body)
      chunks.append({
        "product_id": section["product_id"],
        "product_name": section["product_name"],
        "section": section["section"],
        "chunk_index": chunk_index,
        "body": body,
        "text": text,
        "n_tokens": count_tokens(text),
      })
  return chunks, n_resplit


def split_details(details):
  """1단과 2단을 순서대로. 부르는 쪽은 이 하나만 알면 된다."""
  sections = split_sections(details)
  chunks, n_resplit = split_chunks(sections)
  return sections, chunks, n_resplit