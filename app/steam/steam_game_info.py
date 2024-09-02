import requests
import random

def get_random_steam_game_info(limit: int = 1000) -> dict:
    # APIエンドポイント
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    
    # APIリクエストを送信
    response = requests.get(url)
    
    # レスポンスが成功した場合のみ処理
    if response.status_code == 200:
        data = response.json()
        if "applist" in data and "apps" in data["applist"]:
            apps = data["applist"]["apps"]
            # ランダムにアプリを選択
            random_apps = random.sample(apps, min(limit, len(apps)))
            return {
                "applist": {
                    "apps": [
                        {"appid": app["appid"], "name": app["name"]}
                        for app in random_apps
                    ]
                }
            }
    else:
        print(f"HTTP Error: {response.status_code}")
    
    return None