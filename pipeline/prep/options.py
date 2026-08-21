"""조각을 어떻게 자를지 정하는 값들 ― 실습에서 손대는 건 여기뿐이다.

이 파일을 따로 뗀 이유
    값을 바꿔 보는 실습을 할 때 240줄짜리 파일에서 여섯 줄을 찾아 헤매지 않는다.
    그리고 chunking.py 는 값이 바뀌어도 한 글자도 안 바뀐다 ― 그게 목적이다.
"""

from app.core.config import EMBED_MAX_TOKENS

CHUNK_SIZE = 384            # 조각 하나의 토큰 상한
CHUNK_OVERLAP = 48          # 경계에서 겹치는 몫
PREFIX_BUDGET = 32          # 접두어("[상품명 > 섹션]")가 쓸 토큰 자리

# 계산해서 잡는다. 상한이 바뀌면 문턱도 따라 움직인다 ― 손으로 두 번 적으면 한쪽만 고치게 된다
RESPLIT_OVER = EMBED_MAX_TOKENS - PREFIX_BUDGET

HEADERS = [("##", "section")]

SEPARATORS = ["\n\n", "\n", "다. ", "요. ", ". ", " ", ""]