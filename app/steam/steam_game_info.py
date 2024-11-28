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

def get_random_action_games(limit: int = 1000) -> dict:
    # APIエンドポイント: すべてのSteamアプリケーションのリストを取得
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"

    action_games = []
    while len(action_games) < 3:

        # APIリクエストを送信
        response = requests.get(url)
    
        # レスポンスが成功した場合のみ処理
        if response.status_code == 200:
            data = response.json()
            if "applist" in data and "apps" in data["applist"]:
                apps = data["applist"]["apps"]
                # ランダムにアプリを選択
            
                random_apps = random.sample(apps, min(limit, len(apps)))

                # アクションゲームだけを抽出
                for app in random_apps:
                    appid = app["appid"]
                    app_details = get_app_details(appid)
                
                    if app_details and "genres" in app_details:
                        genres = app_details["genres"]
                        # ジャンルに「ActionのID」が含まれていれば追加
                        if any(genre['id'] == '1' for genre in genres):
                            action_games.append({
                                "appid": app["appid"],
                                "name": app["name"]
                            })
                            if len(action_games) >=3:
                                break

        else:
            print(f"HTTP Error: {response.status_code}")
    
    return {"applist": {"apps": action_games}}

def get_app_details(appid: int) -> dict:
    # APIエンドポイント: 各アプリの詳細情報を取得
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if str(appid) in data and data[str(appid)]["success"]:
            return data[str(appid)]["data"]
    
    return None

def get_random_adv_games(limit: int = 1000) -> dict:
    # APIエンドポイント: すべてのSteamアプリケーションのリストを取得
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"

    adv_games = []
    while len(adv_games) < 3:

        # APIリクエストを送信
        response = requests.get(url)
    
        # レスポンスが成功した場合のみ処理
        if response.status_code == 200:
            data = response.json()
            if "applist" in data and "apps" in data["applist"]:
                apps = data["applist"]["apps"]
                # ランダムにアプリを選択
            
                random_apps = random.sample(apps, min(limit, len(apps)))

                # アドベンチャーゲームだけを抽出
                for app in random_apps:
                    appid = app["appid"]
                    app_details = get_app_details(appid)
                
                    if app_details and "genres" in app_details:
                        genres = app_details["genres"]
                        # ジャンルに「AdventureのID」が含まれていれば追加
                        if any(genre['id'] == '25' for genre in genres):
                            adv_games.append({
                                "appid": app["appid"],
                                "name": app["name"]
                            })
                            if len(adv_games) >=3:
                                break

        else:
            print(f"HTTP Error: {response.status_code}")
    
    return {"applist": {"apps": adv_games}}

def get_random_early_games(limit: int = 1000) -> dict:
    # APIエンドポイント: すべてのSteamアプリケーションのリストを取得
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"

    early_games = []
    while len(early_games) < 3:

        # APIリクエストを送信
        response = requests.get(url)
    
        # レスポンスが成功した場合のみ処理
        if response.status_code == 200:
            data = response.json()
            if "applist" in data and "apps" in data["applist"]:
                apps = data["applist"]["apps"]
                # ランダムにアプリを選択
            
                random_apps = random.sample(apps, min(limit, len(apps)))

                # 早期アクセスのゲームだけを抽出
                for app in random_apps:
                    appid = app["appid"]
                    app_details = get_app_details(appid)
                
                    if app_details and "genres" in app_details:
                        genres = app_details["genres"]
                        # ジャンルに「早期アクセスのID」が含まれていれば追加
                        if any(genre['id'] == '70' for genre in genres):
                            early_games.append({
                                "appid": app["appid"],
                                "name": app["name"]
                            })
                            if len(early_games) >=3:
                                break

        else:
            print(f"HTTP Error: {response.status_code}")
    
    return {"applist": {"apps": early_games}}