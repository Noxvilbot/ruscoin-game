import os
import random
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Создаем экземпляр бота и диспетчера
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher()

# Словарь для хранения данных пользователей
user_data = {}

def load_user_data():
    try:
        with open('user_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data():
    with open('user_data.json', 'w') as f:
        json.dump(user_data, f)

def get_user_data(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'balance': 10,  # Начальный баланс
            'last_reward': '',
            'current_bet': 0
        }
        save_user_data()
        logger.info(f"Created new user {user_id} with initial balance")
    return user_data[str(user_id)]

def check_daily_reward(user_id):
    user = get_user_data(user_id)
    current_time = datetime.now()
    
    if not user['last_reward']:
        user['last_reward'] = current_time.isoformat()
        save_user_data()
        logger.info(f"Set initial reward time for user {user_id}")
        return
    
    last_reward_time = datetime.fromisoformat(user['last_reward'])
    if current_time - last_reward_time >= timedelta(days=1):
        give_daily_reward(user_id)
        logger.info(f"Gave daily reward to user {user_id}")

def give_daily_reward(user_id):
    user = get_user_data(user_id)
    user['balance'] += 10
    user['last_reward'] = datetime.now().isoformat()
    save_user_data()
    logger.info(f"Added 10 Ruscoin to user {user_id}, new balance: {user['balance']}")

def get_time_until_reward(user_id):
    user = get_user_data(user_id)
    if not user['last_reward']:
        return "Сейчас"
        
    last_reward_time = datetime.fromisoformat(user['last_reward'])
    next_reward_time = last_reward_time + timedelta(days=1)
    time_left = next_reward_time - datetime.now()
    
    if time_left.total_seconds() <= 0:
        return "Сейчас"
        
    hours = int(time_left.total_seconds() // 3600)
    minutes = int((time_left.total_seconds() % 3600) // 60)
    return f"{hours}ч {minutes}м"

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    check_daily_reward(user_id)
    user = get_user_data(user_id)
    
    # Создаем кнопку для открытия Web App
    webapp_button = InlineKeyboardButton(
        text="🎮 Играть",
        web_app=WebAppInfo(url="https://noxvilbot.github.io/ruscoin-game/")
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [webapp_button]
    ])
    
    await message.answer(
        f"🎮 Добро пожаловать в игру 'Орёл или Решка'!\n\n"
        f"💰 Ваш баланс: {user['balance']} Ruscoin\n"
        f"🎁 Каждые 24 часа вы получаете 10 Ruscoin!\n\n"
        f"🎲 Нажмите 'Играть' чтобы начать!",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.web_app_data is not None)
async def web_app_handler(message: types.Message):
    user_id = message.from_user.id
    check_daily_reward(user_id)
    user = get_user_data(user_id)
    
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        
        if action == 'get_balance':
            response = {
                'balance': user['balance'],
                'current_bet': user['current_bet'],
                'time_until_reward': get_time_until_reward(user_id)
            }
            await message.answer(
                json.dumps(response),
                reply_markup=types.ReplyKeyboardRemove()
            )
            
        elif action == 'set_bet':
            bet = int(data.get('bet', 0))
            if bet < 0 or bet > user['balance']:
                await message.answer(
                    json.dumps({
                        'error': 'Неверная ставка',
                        'balance': user['balance'],
                        'current_bet': user['current_bet']
                    }),
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
                
            user['current_bet'] = bet
            save_user_data()
            await message.answer(
                json.dumps({
                    'success': True,
                    'balance': user['balance'],
                    'current_bet': bet
                }),
                reply_markup=types.ReplyKeyboardRemove()
            )
            
        elif action == 'play':
            if user['current_bet'] <= 0:
                await message.answer(
                    json.dumps({
                        'error': 'Установите ставку',
                        'balance': user['balance'],
                        'current_bet': user['current_bet']
                    }),
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
                
            if user['current_bet'] > user['balance']:
                await message.answer(
                    json.dumps({
                        'error': 'Недостаточно средств',
                        'balance': user['balance'],
                        'current_bet': user['current_bet']
                    }),
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
                
            result = random.choice(['heads', 'tails'])
            choice = data.get('choice')
            
            if result == choice:
                win_amount = user['current_bet']
                user['balance'] += win_amount
                save_user_data()
                response = {
                    'result': 'win',
                    'balance': user['balance'],
                    'win_amount': win_amount,
                    'current_bet': 0
                }
                await message.answer(
                    json.dumps(response),
                    reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                lose_amount = user['current_bet']
                user['balance'] -= lose_amount
                save_user_data()
                response = {
                    'result': 'lose',
                    'balance': user['balance'],
                    'lose_amount': lose_amount,
                    'current_bet': 0
                }
                await message.answer(
                    json.dumps(response),
                    reply_markup=types.ReplyKeyboardRemove()
                )
            
            user['current_bet'] = 0
            save_user_data()
            
    except Exception as e:
        logger.error(f"Error in web_app_handler: {e}")
        await message.answer(
            json.dumps({
                'error': str(e),
                'balance': user['balance'],
                'current_bet': user['current_bet']
            }),
            reply_markup=types.ReplyKeyboardRemove()
        )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 