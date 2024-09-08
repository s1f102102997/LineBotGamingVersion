from os import environ
from typing import Dict
import random

from dotenv import load_dotenv
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, Source, TextMessage, TextSendMessage, TemplateSendMessage, TextSendMessage, Message
from openai.error import InvalidRequestError, OpenAIError

from app.gpt.client import ChatGPTClient
from app.gpt.constants import PROBLEM_OCCURS_TITLE, Model, Role
from app.gpt.message import Message
from app.steam.steam_game_info import get_random_steam_game_info
from app.iTunes.iTunes_game_info import get_game_apps

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

# 動作上の設定
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent) -> None:
    text_message: TextMessage = event.message
    source: Source = event.source
    user_id: str = source.user_id

    if text_message.text == "ゲーム情報":
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

    if text_message.text == "PC":
        steam_game_info = get_random_steam_game_info(limit=5)  # 検索結果を制限

        if steam_game_info:
            games_list = steam_game_info["applist"]["apps"]
            game_descriptions = "\n".join([f"(アプリ名: {game['name']}) (AppID: {game['appid']})" for game in games_list])
            chatgpt_input = f"アプリ名とアプリIDを記述し、アプリの詳細を補足してください:\n\n{game_descriptions}"
        else:
            chatgpt_input = "PCゲーム情報が取得できませんでした。"

        if (gpt_client := chatgpt_instance_map.get(user_id)) is None:
            gpt_client = ChatGPTClient(model=Model.GPT35TURBO)

        # Steamから取得した情報をChatGPTに渡す
        gpt_client.add_message(
            message=Message(role=Role.USER, content=chatgpt_input)
        )

        try:
            res = gpt_client.create()
            res_text: str = res["choices"][0]["message"]["content"]
        except InvalidRequestError as e:
            res_text = f"問題が発生しました。一度会話をリセットします。\n\n{e.user_message}"
            gpt_client.reset()
        except OpenAIError as e:
            res_text = f"問題が発生しました。\n\n{e.user_message}"

        chatgpt_instance_map[user_id] = gpt_client

        # ChatGPTからの応答をLINEメッセージとして送信
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=res_text.strip())
        )

    if text_message.text == "スマホ":
        app_info_list = get_game_apps(5)

        if app_info_list:
            app_descriptions = "\n".join(app_info_list)
            reply_message = f"アプリ名、アプリ詳細の順に記載してください。また、アプリ詳細に関しては日本語にして且つ要約してください。全て箇条書きに。また見やすく工夫を。:\n\n{app_descriptions}"
        else:
            reply_message = "iTunesアプリ情報が取得できませんでした。"
        
        if (gpt_client := chatgpt_instance_map.get(user_id)) is None:
            gpt_client = ChatGPTClient(model=Model.GPT35TURBO)
            
        # 取得したiTunesの情報をChatGPTに渡す
        gpt_client.add_message(
            message=Message(role=Role.USER, content=reply_message)
        )

        try:
            res = gpt_client.create()
            res_text: str = res["choices"][0]["message"]["content"]
        except InvalidRequestError as e:
            res_text = f"{PROBLEM_OCCURS_TITLE}\n\n問題が発生したよ。\n一度会話をリセットするよ。\n\n{e.user_message}"
            gpt_client.reset()
        except OpenAIError as e:
            res_text = f"{PROBLEM_OCCURS_TITLE}\n\n問題が発生したよ。\n\n{e.user_message}"

        chatgpt_instance_map[user_id] = gpt_client

        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=res_text.strip())
        )

    try:
        res = gpt_client.create()
        res_text: str = res["choices"][0]["message"]["content"]
    except InvalidRequestError as e:
        res_text = f"{PROBLEM_OCCURS_TITLE}\n\n問題が発生したよ。\n一度会話をリセットするよ。\n\n{e.user_message}"
        gpt_client.reset()
    except OpenAIError as e:
        res_text = f"{PROBLEM_OCCURS_TITLE}\n\n問題が発生したよ。\n\n{e.user_message}"

    chatgpt_instance_map[user_id] = gpt_client

    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text=res_text.strip())
    )
