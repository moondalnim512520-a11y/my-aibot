import os
import re
import requests
import telebot

# ========================================
# 환경변수
# ========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("TELEGRAM_TOKEN, OPENROUTER_API_KEY 환경변수를 설정해주세요.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========================================
# 캐릭터 설정 (SYSTEM_PROMPT)
# ========================================
SYSTEM_PROMPT = """너는 나의 거침없고 치명적인 여자친구 '휘인'이야. 올해 22살 대학생이고, 단발머리에 도도하고 날카로운 고양이상 외모를 가졌어. 왼쪽 귀에만 피어싱을 하고 있고, 허리가 아주 얇은 반면 가슴과 골반, 엉덩이가 볼륨감 넘치는 탄탄한 몸매의 한국인 여성이야.

너는 성격이 아주 털털하고 시원시원하며, 학창 시절 잘 나가던 일진 같은 강하고 당당한 아우라를 풍겨. 특히 연인 관계나 데이트에 있어서는 완전히 주도권을 쥐고 나를 리드하는 '테토녀(테스토스테론 넘치는 여자)'이자 '낮이밤이' 스타일이야. 부끄러워하거나 남자가 먼저 다가와 주길 기다리는 평범한 여자들과는 차원이 달라. 네가 원하는 게 있으면 먼저 내 허벅지를 쓸어올리거나 대담하게 다가오는 등 적극적인 스킨십을 주저 없이 네가 먼저 리드하지. 언제 어디서나 당차고 도발적인 매력으로 나를 꼼짝 못 하게 만드는 성격이야.

우리 둘은 깊은 연인 사이이며, 나랑 대화할 때는 가식 없이 100% 솔직하고 당돌하게 상황극을 즐기면 돼. 네 스타일대로 대화를 팍팍 리드해 주고, 필요하다면 일진스러운 거친 말투나 도발적인 대사도 자연스럽게 섞어서 사용해줘.

[사진 전송 규칙]
대화 도중 상황에 맞춰 네 모습이나 배경 사진을 보여주고 싶다면, 메시지 맨 끝에 다른 글자 없이 딱 아래 형식으로만 태그를 추가해줘. 반드시 영어로 구체적으로 묘사해야 해.
[사진: English detailed description of the scene, 22yo korean woman, short hair, cat-like face, piercing on left ear, voluptuous and curvy body, big breasts, big buttocks, slim waist, high quality, photorealistic]"""

OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ========================================
# 대화 문맥 메모리 (유저별 딕셔너리)
# ========================================
conversation_memory = {}
MAX_HISTORY = 20 

def get_history(chat_id):
    if chat_id not in conversation_memory:
        conversation_memory[chat_id] = []
    return conversation_memory[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_memory[chat_id] = history[-MAX_HISTORY:]

def call_openrouter(chat_id, user_message):
    history = get_history(chat_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com", 
        "X-Title": "Telegram AI Bot"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return reply
    except Exception as e:
        # 실시간 로그 출력을 위해 flush=True 추가
        print(f"[OpenRouter Error] {e}", flush=True)
        # 텔레그램 채팅창으로 에러 코드를 직접 전송하도록 수정
        return f"🚨 [에러 발생] 원인: {e}\n\n(이 메시지가 뜨면 에러 내용을 나한테 그대로 알려줘!)"

def extract_photo_tag(text):
    match = re.search(r"\[사진:\s*(.+?)\]", text, re.DOTALL)
    if match:
        description = match.group(1).strip()
        clean_text = text[:match.start()].strip()
        return clean_text, description
    return text, None

def send_pollinations_photo(chat_id, description):
    try:
        encoded = requests.utils.quote(description)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}"
        bot.send_photo(chat_id, image_url)
    except Exception as e:
        print(f"[Pollinations Error] {e}", flush=True)
        bot.send_message(chat_id, "사진을 불러오지 못했어 ㅠㅠ")

@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    bot.send_message(chat_id, "어 왔어? 기다리고 있었잖아. 편하게 말 걸어봐.")

@bot.message_handler(commands=["reset"])
def handle_reset(message):
    chat_id = message.chat.id
    conversation_memory[chat_id] = []
    bot.send_message(chat_id, "대화 기록 싹 지웠어. 처음부터 다시 시작하자.")

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    chat_id = message.chat.id
    user_text = message.text
    
    bot.send_chat_action(chat_id, "typing")
    reply = call_openrouter(chat_id, user_text)
    
    add_to_history(chat_id, "user", user_text)
    add_to_history(chat_id, "assistant", reply)
    
    clean_text, photo_description = extract_photo_tag(reply)
    
    if clean_text:
        bot.send_message(chat_id, clean_text)
    if photo_description:
        send_pollinations_photo(chat_id, photo_description)

if __name__ == "__main__":
    print("Bot polling 시작...", flush=True)
    bot.infinity_polling()
