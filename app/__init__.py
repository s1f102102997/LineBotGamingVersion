from os import environ
from typing import Dict
import random

from dotenv import load_dotenv
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, Source, TextMessage, TextSendMessage, TemplateSendMessage, TextSendMessage, Message, ButtonsTemplate, MessageAction
from openai.error import InvalidRequestError, OpenAIError

from app.gpt.client import ChatGPTClient
from app.gpt.constants import PROBLEM_OCCURS_TITLE, Model, Role
from app.gpt.message import Message
from app.steam.steam_game_info import get_random_steam_game_info, get_random_action_games, get_random_adv_games, get_random_early_games
from app.iTunes.iTunes_game_info import get_game_apps, get_action_game_apps, get_adv_game_apps, get_puzzle_game_apps

load_dotenv(".env", verbose=True)

app = Flask(__name__)

# LINEチャネルへのアクセストークンの登録
if not (access_token := environ.get("LINE_CHANNEL_ACCESS_TOKEN")):
    raise Exception("access token is not set as an environment variable")

# LINEチャネルシークレットの登録
if not (channel_secret := environ.get("LINE_CHANNEL_SECRET")):
    raise Exception("channel secret is not set as an environment variable")

line_bot_api = LineBotApi(access_token)
handler = WebhookHandler(channel_secret)

chatgpt_instance_map: Dict[str, ChatGPTClient] = {}


@app.route("/", methods=["GET"])
def index() -> str:
    return "Hello, ChatGPT LINEBot Python."


@app.route("/callback", methods=["POST"])
def callback() -> str:
    signature = request.headers["X-Line-Signature"]

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ユーザーごとのメッセージカウントと状態を管理する辞書
user_state_map = {}

# 定数としてGoogleフォームのURLを定義
GOOGLE_FORM_URL = "https://forms.gle/SKKNmxfz5NVbxmE66"

# 動作上の設定
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent) -> None:
    text_message: TextMessage = event.message
    source: Source = event.source
    user_id: str = source.user_id
    user_state = user_state_map.get(user_id, None)

    if text_message.text == "ゲーム":
        buttons_template = TemplateSendMessage(
            alt_text="This is a buttons template",
            template={
                "type": "buttons",
                "title": "プラットホーム選択",
                "text": "調べたいゲームのプラットホームを選択してください",
                "actions": [
                    {
                        "type": "message",
                        "label": "PC",
                        "text": "PC"
                    },
                    {
                        "type": "message",
                        "label": "スマホ",
                        "text": "スマホ"
                    },
                ]
            }
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return
    
    if text_message.text == "取扱説明書":
        explanation = [
            TextSendMessage(text="こんにちは！\nご利用いただきありがとうございます。\nこのボットの使い方についてご説明いたします。\n①左枠のゲームボタンをタップしたら調べたいプラットホームを選択してください。\n②次に、ジャンルを選択してください\nするとゲームが３つ推薦されます。③また自身で入力をすることで条件を指定することも可能です。\n例）PCでアクション要素のあるホラーゲームがやりたい\n④また右のアンケートボタンを押すと任意で回答することが出来ます。"),
        ]
        line_bot_api.reply_message(event.reply_token, explanation)

    if text_message.text == "アンケート":
        questionnaire = f"ご利用いただき誠にありがとうございます！\n以下のアンケートへの回答にご協力ください！：\n{GOOGLE_FORM_URL}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=questionnaire))

    if text_message.text == "リセットして":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"{PROBLEM_OCCURS_TITLE}\n\n会話をリセットするよ。"),
        )

    if (gpt_client := chatgpt_instance_map.get(user_id)) is None:
        gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

    gpt_client.add_message(
        message=Message(role=Role.USER, content=text_message.text)
    )    

    # "PC"と入力されたら動作開始
    if text_message.text == "PC":

        # PCゲームのジャンル選択を開始
        user_state_map[user_id] = "PC"  # ユーザーの状態を「PC」に設定

        buttons_template = TemplateSendMessage(
            alt_text="This is a buttons template",
            template=ButtonsTemplate(
                title="ジャンル選択",
                text="調べたいゲームのジャンルを選択してください",
                actions=[
                    MessageAction(label="アクション", text="アクション"),
                    MessageAction(label="アドベンチャー", text="アドベンチャー"),
                    MessageAction(label="早期アクセス", text="早期アクセス"),
                    MessageAction(label="その他", text="その他")
                ]
            )
        )

        # ジャンル選択をユーザーに表示
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # "スマホ"と入力されたら動作開始
    elif text_message.text == "スマホ":

        # スマホゲームのジャンル選択を開始
        user_state_map[user_id] = "スマホ"  # ユーザーの状態を「スマホ」に設定

        buttons_template = TemplateSendMessage(
            alt_text="This is a buttons template",
            template=ButtonsTemplate(
                title="ジャンル選択",
                text="調べたいゲームのジャンルを選択してください",
                actions=[
                    MessageAction(label="アクション", text="アクション"),
                    MessageAction(label="アドベンチャー", text="アドベンチャー"),
                    MessageAction(label="パズル", text="パズル"),
                    MessageAction(label="その他", text="その他")
                ]
            )
        )

        # ジャンル選択をユーザーに表示
        line_bot_api.reply_message(event.reply_token, buttons_template)

    # "アクション"が選択された場合
    elif text_message.text == "アクション":

        # ユーザーがどちらのフローを使っているかを確認
        if user_state == "PC":
            # PCゲームのアクションジャンルからゲームを取得
            steam_game_info = get_random_action_games(limit=3)
            if steam_game_info:
                games_list = steam_game_info["applist"]["apps"]
                game_descriptions = "\n".join([f"(アプリ名: {game['name']}) (AppID: {game['appid']})" for game in games_list])
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "PCゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client
        
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))

        elif user_state == "スマホ":
            # スマホゲームのアクションジャンルからゲームを取得
            app_info_list = get_action_game_apps(3)
            if app_info_list:
                game_descriptions = "\n".join(app_info_list)
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "スマホゲーム情報が取得できませんでした。"
            
            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client
        
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))

    # "RPG"が選択された場合
    elif text_message.text == "アドベンチャー":

        # ユーザーがどちらのフローを使っているかを確認
        if user_state == "PC":
            # PCゲームのRPGジャンルからゲームを取得
            steam_game_info = get_random_adv_games(limit=3)
            if steam_game_info:
                games_list = steam_game_info["applist"]["apps"]
                game_descriptions = "\n".join([f"(アプリ名: {game['name']}) (AppID: {game['appid']})" for game in games_list])
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "PCゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))

        elif user_state == "スマホ":
            # スマホゲームのRPGジャンルからゲームを取得
            app_info_list = get_adv_game_apps(3)
            if app_info_list:
                game_descriptions = "\n".join(app_info_list)
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "スマホゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))

    # "早期アクセス"が選択された場合
    elif text_message.text == "早期アクセス":

        # ユーザーがどちらのフローを使っているかを確認
        if user_state == "PC":
            # PCゲームのパズルジャンルからゲームを取得
            steam_game_info = get_random_early_games(limit=3)
            if steam_game_info:
                games_list = steam_game_info["applist"]["apps"]
                game_descriptions = "\n".join([f"(アプリ名: {game['name']}) (AppID: {game['appid']})" for game in games_list])
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "PCゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))
                
    # "パズル"が選択された場合
    elif text_message.text == "パズル":
        if user_state == "スマホ":
            # スマホゲームのパズルジャンルからゲームを取得
            app_info_list = get_puzzle_game_apps(3)
            if app_info_list:
                game_descriptions = "\n".join(app_info_list)
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "スマホゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))
    
                
    # "その他"が選択された場合
    elif text_message.text == "その他":
    
        # ユーザーがどちらのフローを使っているかを確認
        if user_state == "PC":
            # PCゲームのジャンルからゲームを取得
            steam_game_info = get_random_steam_game_info(limit=3)
            if steam_game_info:
                games_list = steam_game_info["applist"]["apps"]
                game_descriptions = "\n".join([f"(アプリ名: {game['name']}) (AppID: {game['appid']})" for game in games_list])
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "PCゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client
        
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))

        elif user_state == "スマホ":
            # スマホゲームのジャンルからゲームを取得
            app_info_list = get_game_apps(3)
            if app_info_list:
                game_descriptions = "\n".join(app_info_list)
                chatgpt_input = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細は日本語で簡潔に分かりやすく箇条書きにして要約してください。:\n\n{game_descriptions}"
            else:
                chatgpt_input = "スマホゲーム情報が取得できませんでした。"

            # ChatGPTクライアントのインスタンスを取得または作成
            gpt_client = chatgpt_instance_map.get(user_id)
            if gpt_client is None:
                gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

            # Steam/スマホから取得した情報をChatGPTに渡す
            gpt_client.add_message(
                message=Message(role=Role.USER, content=chatgpt_input)
            )

            try:
                # ChatGPTからの応答を取得
                res = gpt_client.create()
                res_text: str = res["choices"][0]["message"]["content"]
            except InvalidRequestError as e:
                res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
                gpt_client.reset()
            except OpenAIError as e:
                res_text = f"問題が発生しました。\n\n{e.user_message}"

            # ChatGPTのインスタンスを再保存
            chatgpt_instance_map[user_id] = gpt_client
        
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))
                
    # 1. ユーザーからの意見をChatGPTに送信して意図を解析するプロンプトを作成
    prompt = f"以下はユーザーからの要望です。内容を分析し、関連性の高いゲームを3つ推薦してください。" \
             f"それぞれのゲームの名前と日本語で簡単な特徴を列挙形式で説明してください:\n\n「{text_message}」"
    
    gpt_client.add_message(
        message=Message(role=Role.USER, content=prompt)
    )
                
    # 2. ChatGPTからの応答を取得して解析結果をLINEに送信
    try:
        res = gpt_client.create()
        res_text: str = res["choices"][0]["message"]["content"]

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=res_text.strip()))

    except InvalidRequestError as e:
        error_message = f"エラーが発生しました。一度会話をリセットします。\n\n{e.user_message}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_message))
        gpt_client.reset()  # エラー時にChatGPTの会話をリセット
    except OpenAIError as e:
        error_message = f"問題が発生しました。\n\n{e.user_message}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_message))

    # ChatGPTのインスタンスを再保存
    chatgpt_instance_map[user_id] = gpt_client

    