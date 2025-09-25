import os
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, filters, MessageHandler
from supabase import create_client, Client
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import asyncio
import threading

load_dotenv()

app = Flask(__name__)

# Configuraciones
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
NOWPAYMENTS_IPN_SECRET = os.getenv('NOWPAYMENTS_IPN_SECRET')
GROUP_ID = int(os.getenv('GROUP_ID', -1002877292793))
PORT = int(os.getenv('PORT', 8080))

# Inicializar bot y supabase
bot = Bot(TELEGRAM_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
application = None

# Variable para obtener la URL del servidor
BASE_URL = None

def get_base_url():
    global BASE_URL
    if not BASE_URL:
        # En Render, puedes usar la variable de entorno RENDER_EXTERNAL_URL
        BASE_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
    return BASE_URL

# Función para generar invoice en NOWPayments
# CAMBIO: El precio ahora es 12
def create_invoice(user_id, amount=12):
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}
    base_url = get_base_url()
    
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "trx",
        "order_id": f"user_{user_id}",
        # CAMBIO: La descripción de la orden ahora es de 1 hora
        "order_description": "Membresía de prueba Ghost Traders - 1 hora",
        "ipn_callback_url": f"{base_url}/webhook/nowpayments",
        "success_url": "https://t.me/ghost_traders_bot?start=success",
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            data = response.json()
            return data['invoice_url'], data['id']
    except Exception as e:
        print(f"Error creando invoice: {e}")
    return None, None

# Handler para /start
async def start(update: Update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Sin username"
    
    try:
        # Verificar membresía existente
        result = supabase.table('memberships').select('*').eq('telegram_user_id', user_id).execute()
        
        if result.data:
            membership = result.data[0]
            end_date = datetime.fromisoformat(membership['membership_end_date'].replace('Z', '+00:00'))
            
            if end_date > datetime.now(end_date.tzinfo):
                await update.message.reply_text(
                    f"¡Hola {username}! Ya eres miembro activo.\n"
                    f"Tu membresía expira el: {end_date.strftime('%d/%m/%Y %H:%M')}\n\n"
                    "Intentando añadirte al grupo..."
                )
                try:
                    await bot.unban_chat_member(GROUP_ID, user_id)
                    await bot.send_message(user_id, "✅ Has sido añadido al grupo exitosamente!")
                except Exception as e:
                    await update.message.reply_text(f"❌ Error al añadir al grupo: {str(e)}")
                return

        # Crear nueva factura de pago
        pay_url, invoice_id = create_invoice(user_id)
        if pay_url:
            await update.message.reply_text(
                f"¡Bienvenido a Ghost Traders! 👻\n\n"
                # CAMBIO: El mensaje ahora indica 12 USDT y 1 hora
                f"Para unirte al grupo de prueba, realiza el pago de **12 USDT en TRX**:\n\n"
                f"🔗 **Link de pago**: {pay_url}\n\n"
                f"📋 **Invoice ID**: {invoice_id}\n\n"
                f"Una vez completado el pago, serás añadido automáticamente al grupo.\n"
                f"Tu membresía durará 1 hora."
            )
        else:
            await update.message.reply_text("❌ Error generando el enlace de pago. Intenta de nuevo más tarde.")
            
    except Exception as e:
        print(f"Error en comando start: {e}")
        await update.message.reply_text("❌ Error interno. Intenta de nuevo más tarde.")

# Handler para otros mensajes
async def handle_message(update: Update, context):
    await update.message.reply_text("Usa /start para comenzar el proceso de membresía.")

# Webhook para NOWPayments IPN
@app.route('/webhook/nowpayments', methods=['POST'])
def nowpayments_webhook():
    try:
        data = request.get_json()
        signature = request.headers.get('x-nowpayments-sig')
        
        if not data or not signature:
            return jsonify({"error": "Missing data or signature"}), 400
        
        # Verificar firma
        sorted_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        computed_sig = hmac.new(NOWPAYMENTS_IPN_SECRET.encode(), sorted_data.encode(), hashlib.sha512).hexdigest()
        
        if signature != computed_sig:
            print(f"Invalid signature. Expected: {computed_sig}, Got: {signature}")
            return jsonify({"error": "Invalid signature"}), 400

        print(f"Webhook recibido: {data}")

        if data.get('payment_status') == 'finished':
            order_id = data.get('order_id', '')
            
            if order_id.startswith('user_'):
                try:
                    user_id = int(order_id.split('_')[1])
                    # CAMBIO: La membresía ahora dura 1 hora
                    end_date = datetime.now() + timedelta(hours=1)
                    
                    # Insertar o actualizar membresía
                    supabase.table('memberships').upsert({
                        'telegram_user_id': user_id,
                        'membership_end_date': end_date.isoformat(),
                        'status': 'active'
                    }).execute()
                    
                    # Enviar mensaje de confirmación y añadir al grupo
                    asyncio.run_coroutine_threadsafe(
                        confirm_payment(user_id), 
                        asyncio.get_event_loop()
                    )
                    
                except Exception as e:
                    print(f"Error procesando pago: {e}")
                    return jsonify({"error": "Processing error"}), 500
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        print(f"Error en webhook: {e}")
        return jsonify({"error": "Server error"}), 500

async def confirm_payment(user_id):
    try:
        await bot.send_message(
            user_id, 
            "🎉 ¡Pago confirmado! Bienvenido a Ghost Traders.\n\n"
            "Añadiéndote al grupo VIP... ✅"
        )
        await bot.unban_chat_member(GROUP_ID, user_id)
        await bot.send_message(user_id, "✅ ¡Has sido añadido al grupo exitosamente!")
    except Exception as e:
        print(f"Error confirmando pago: {e}")
        await bot.send_message(user_id, f"❌ Error al añadir al grupo: {str(e)}")

# Endpoint para verificar membresías expiradas
@app.route('/check_memberships', methods=['GET'])
def check_memberships():
    try:
        now = datetime.now().isoformat()
        expired = supabase.table('memberships').select('telegram_user_id').lt('membership_end_date', now).eq('status', 'active').execute()
        
        removed_count = 0
        for member in expired.data:
            user_id = member['telegram_user_id']
            try:
                asyncio.run_coroutine_threadsafe(
                    bot.ban_chat_member(GROUP_ID, user_id),
                    asyncio.get_event_loop()
                )
                supabase.table('memberships').update({'status': 'expired'}).eq('telegram_user_id', user_id).execute()
                removed_count += 1
            except Exception as e:
                print(f"Error removiendo usuario {user_id}: {e}")

        return jsonify({"status": "checked", "removed": removed_count}), 200
        
    except Exception as e:
        print(f"Error checking memberships: {e}")
        return jsonify({"error": "Server error"}), 500

# Webhook para Telegram
@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        if application:
            asyncio.run_coroutine_threadsafe(
                application.process_update(update),
                asyncio.get_event_loop()
            )
        return 'ok', 200
    except Exception as e:
        print(f"Error en webhook telegram: {e}")
        return 'error', 500

# Endpoints de salud
@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Ghost Traders Bot funcionando", "timestamp": datetime.now().isoformat()})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Configurar el bot
def setup_bot():
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Inicializar en un hilo separado
def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    setup_bot()
    loop.run_forever()

if __name__ == '__main__':
    # Iniciar bot en hilo separado
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=PORT, debug=False)
