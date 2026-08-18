"""
  db.py : DB의 데이터를 조회하는 DB제어의 코어 로직이 담겨있음 (resposity 계층)
  retrieve.py : 해당 DB조회함수를 가져와서 고객이 사용할수 있는 서비스로직을 담는 계층 (service 계층)

  앞으로 이곳에 추가할 서비스 로직들
  - 백터검색 : 질문을 주면 관련 있는 문서 조각을 찾아옴
  - 마스킹 : 후기정보에서 개인정보를 가려서 내보내는 것
  - 추천후보 : 특정고객에게 팔릴만한 상품 추리는 것
"""

from app.db import dicts

# 고객목록 + 각 고객의 구매 건수 반환 함수
def customer_list(limit=None):
  rows = dicts("""
    SELECT  customers.customer_id, customers.name, customers.age, customers.gender, customers.skin_type, customers.city, COUNT(purchases.purchase_id) AS n_purchases
    FROM customers LEFT JOIN purchases 
    ON purchases.customer_id = customers.customer_id AND purchases.is_holdout = 0
    GROUP BY customers.customer_id, customers.name
    ORDER BY n_purchases DESC
  """
  )
  return rows[:limit] if limit else rows

# 고객아이디를 인수로 전달해서 해당고객에 대한 정보만 가져오는 함수
def get_info(customer_id):
  result = dicts("""
    SELECT * FROM customers WHERE customer_id = ?
  """, (customer_id,))
  return result

# 특정 고객 아이디를 집어넣으면 다음의 정보를 반환하는 함수 
# {customers: {고객정보}, avg_rating: 평균평점, total_spent: 구매한상품의 총금액, by_category: 구매한상품명+상품갯수, purchases: 구매횟수+리뷰}
def dashboard(customer_id):
  # 기본 고객정보를 별도의 딕셔너리 형태로 반환받음
  profile = dicts("""
    SELECT customer_id, name, age, gender, skin_type, city   -- 보안이 중요한 고객정보인 전화번호, 이메일은 애초에 제외하고 데이터 호출
    FROM customers WHERE customer_id = ?
  """, (customer_id,))

  # 위에서 반환받은 고객 정보가 없으면 이후의 탐색문이 무의미하므로 강제 함수 종료
  if not profile:
    return None 

  # 구매정보도 별도의 딕셔너리 형태로 반환받음
  purchases = dicts("""
    SELECT products.product_id, products.name, products.category, products.price,  --고객이 구매한 상품 정보
    purchases.purchased_at, purchases.rating, purchases.review    -- 고객의 구매내역 정보
    FROM purchases JOIN products ON purchases.product_id = products.product_id  --상품아이디가 같은 정보를 조인해서 가져옴
    WHERE purchases.customer_id = ?
  """, (customer_id,))

  ratings = [row["rating"] for row in purchases if row["rating"] is not None]
  prices = [row["price"] for row in purchases if row["price"] is not None]

  # {카테고리: 갯수}를 담을 빈 딕셔너리
  by_category = {}
  for row in purchases:
    by_category[row["category"]] = by_category.get(row["category"],0) +1

  # 고객정보와 구매 정보를 다시 상위 딕셔너리로 합쳐서 최종 반환
  return {
    "customers" : profile[0],  
    "avg_rating" :round(sum(ratings) / len(ratings), 2),  
    "total_spent" : sum(prices),
    "by_category" : by_category,
    "purchases": purchases[0]
  }

if __name__ == "__main__": 
  print(dashboard("C005"))

  """
  {
    'customers': {'customer_id': 'C005', 'name': '이은수', 'age': 53, 'gender': 'F', 'skin_type': '중성', 'city': '부산'}, 'avg_rating': 3.2, 
    'total_spent': 159600, 
    'by_category': {'에센스': 3, '클렌징오일': 1, '선크림': 1}, 
    'purchases': {
      'product_id': 'P032', 
      'name': '세라마이드 시카 에센스', 
      'category': '에센스', 
      'price': 38800, 
      'purchased_at': '2025-07-17', 
      'rating': 3, 
      'review': '기대가 컸나 봐요. 산뜻한 제형이라 아침에 쓰기 좋아요. 재고 문의는 010 8202 9049 로 부탁드려요.'
    }
  }
  """


# 커스터머즈 노서치 에러 ㅠㅠ 