"""자료구조를 데이터베이스에 넣는다. **이 파일은 자르는 법을 모른다.**

스플리터를 부르지 않는다. 이미 만들어진 것을 받아서 넣기만 한다.
그래서 「조각이 이상하다」와 「저장이 이상하다」를 따로 볼 수 있다.

오늘 오후에 벡터 표를 만드는 함수가 여기 더 붙는다.
"""


def save_sections_and_chunks(con, sections, chunks):
  """섹션과 조각을 넣는다.

  🔴 커넥션을 밖에서 받는다. 이 함수는 sqlite3.connect() 를 부르지 않는다.
  """
  con.execute("DROP TABLE IF EXISTS chunk_vectors")
  con.execute("DROP TABLE IF EXISTS chunks")
  con.execute("DROP TABLE IF EXISTS sections")
  con.execute("""
      CREATE TABLE sections (
          section_id INTEGER PRIMARY KEY,
          product_id TEXT NOT NULL,
          section    TEXT NOT NULL,
          text       TEXT NOT NULL,
          n_tokens   INTEGER NOT NULL,
          FOREIGN KEY (product_id) REFERENCES products(product_id)
      )
  """)
  con.execute("""
      CREATE TABLE chunks (
          chunk_id    INTEGER PRIMARY KEY,
          section_id  INTEGER NOT NULL,
          product_id  TEXT NOT NULL,
          section     TEXT NOT NULL,
          chunk_index INTEGER NOT NULL,
          text        TEXT NOT NULL,
          body        TEXT NOT NULL,
          n_tokens    INTEGER NOT NULL,
          FOREIGN KEY (section_id) REFERENCES sections(section_id),
          FOREIGN KEY (product_id) REFERENCES products(product_id)
      )
  """)
  con.execute("CREATE INDEX idx_chunks_product_id ON chunks(product_id)")
  con.execute("CREATE INDEX idx_chunks_section ON chunks(section)")
  con.execute("CREATE INDEX idx_sections_product_id ON sections(product_id)")

  # 🔴 방금 붙은 번호를 담아 두는 보관함.
  #    cur.lastrowid 는 다음 INSERT 를 하면 사라진다. 나오는 그 자리에서 받아 둔다
  section_id_lookup = {}
  for section in sections:
      cur = con.execute(
          "INSERT INTO sections (product_id, section, text, n_tokens) VALUES (?, ?, ?, ?)",
          (section["product_id"], section["section"], section["text"], section["n_tokens"]),
      )
      section_id_lookup[(section["product_id"], section["section"])] = cur.lastrowid

  for chunk in chunks:
      con.execute("""
          INSERT INTO chunks (section_id, product_id, section, chunk_index, text, body, n_tokens)
          VALUES (?, ?, ?, ?, ?, ?, ?)
      """, (section_id_lookup[(chunk["product_id"], chunk["section"])],
            chunk["product_id"], chunk["section"], chunk["chunk_index"],
            chunk["text"], chunk["body"], chunk["n_tokens"]))

  con.commit()