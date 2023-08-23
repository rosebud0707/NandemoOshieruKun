"""main_entry_point.py
    botプログラムのメインエントリポイント
"""
from mastodon_service import MastodonService


# インスタンス化
mstdnSv = MastodonService()

# 処理開始
mstdnSv.start_stream()