FROM python:3.11-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# 非rootユーザーの作成
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# ポート設定（不要だがKoyebでの設定用）
EXPOSE 8000

# アプリケーション起動
CMD ["python", "main.py"] 