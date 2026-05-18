# Flask REST Stateful API

> Flask 세션 기반 Stateful REST API 구현

## Stateless vs Stateful

| 구분 | Stateless | Stateful |
|------|-----------|----------|
| 서버 상태 저장 | ❌ | ✅ |
| 세션/쿠키 | 미사용 | 사용 |
| 확장성 | 높음 | 낮음 |
| 주요 용도 | 일반 API | 로그인, 장바구니 |

## Flask 세션 설정

```python
from flask import Flask, session

app = Flask(__name__)
app.secret_key = 'your-secret-key'

@app.route('/login', methods=['POST'])
def login():
    session['user'] = request.json.get('username')
    return jsonify({'message': 'Logged in'})

@app.route('/profile')
def profile():
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify({'user': session['user']})

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381ae81d7e1ab610f3695)
