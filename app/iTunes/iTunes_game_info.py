import requests
import random

def get_game_apps(limit=5):
    # iTunes API URL
    url = "https://itunes.apple.com/search"

    max_offset = 200
    random_offset =random.randint(0, max_offset - limit)
    
    # APIリクエスト用のパラメータ
    params = {
        'term': 'ゲーム',  # 検索キーワード
        'entity': 'software',  # エンティティの種類（ソフトウェア、アプリ）
        'genreId': '6014',  # ゲームジャンルID
        'limit': limit,  # 取得するアプリの数
        'offset' : random_offset
    }
    
    # APIリクエストを送信
    response = requests.get(url, params=params)
    
    # ステータスコードが200（成功）の場合
    if response.status_code == 200:
        data = response.json()
        if data['resultCount'] > 0:
            app_info_list = []
            for result in data['results']:
                app_name = result.get('trackName', '不明なアプリ名')
                app_description = result.get('description', '説明なし')
                app_info_list.append(f"アプリ名: {app_name}\nアプリの詳細: {app_description}\n")
            return app_info_list
        else:
            return ["アプリ情報が見つかりませんでした。"]
    else:
        return [f"APIリクエストが失敗しました。ステータスコード: {response.status_code}"]

