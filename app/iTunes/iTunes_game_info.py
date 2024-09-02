import requests
import random

def get_app_names(app_id):
    # iTunes API URL
    url = f"https://itunes.apple.com/lookup?id={app_id}"
    
    # APIリクエストを送信
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if data['resultCount'] > 0 and 'trackName' in data['results'][0] and 'description' in data['results'][0]:
            app_name = data['results'][0]['trackName']
            app_description = data['results'][0]['description']
            return app_name, app_description
        else:
            return None, None  # 該当するアプリがない場合やtrackNameが存在しない場合
    else:
        return None, None  # APIリクエストが失敗した場合


def generate_random_app_ids(n, id_range=(1000000000, 1500000000)):
    return [random.randint(*id_range) for _ in range(n)]