import os
import sys
import logging
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

# Configuraciones
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY')
NOWPAYMENTS_IPN_SECRET = os.getenv('NOWPAYMENTS_IPN_SECRET')
GROUP_ID = int(os.getenv('GROUP_ID'))
PORT = int(os.getenv('PORT', 8080))

logger.info(f"Iniciando bot con configuraciones:")
logger.info(f"- TELEGRAM_TOKEN: {'✅' if TELEGRAM_TOKEN else '❌'}")
logger.info(f"- SUPABASE_URL: {'✅' if SUPABASE_URL else '❌'}")
logger.info(f"- SUPABASE_KEY: {'✅' if SUPABASE_KEY else '❌'}")
logger.info(f"- NOWPAYMENTS_API_KEY: {'✅' if NOWPAYMENTS_API_KEY else '❌'}")
logger.info(f"- GROUP_ID: {GROUP_ID}")

# Inicializar bot y supabase
try:
    bot = Bot(TELEGRAM_TOKEN)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Bot y Supabase inicializados correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando servicios: {e}")

application = None

# Variable para obtener la URL del servidor
BASE_URL = None

def get_base_url():
    global BASE_URL
    if not BASE_URL:
        BASE_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://ghost-traders-bot.onrender.com')
    return BASE_URL

# Función para generar invoice en NOWPayments
def create_invoice(user_id, amount=10):
    logger.info(f"Creando invoice para usuario {user_id}, monto: ${amount}")
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}
    base_url = get_base_url()
    
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "trx",
        "order_id": f"user_{user_id}",
        "order_description": "Membresía Ghost Traders - 30 días",
        "ipn_callback_url": f"{base_url}/webhook/nowpayments",
        "success_url": "https://t.me/ghost_traders_bot?start=success",
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"NOWPayments response status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            logger.info(f"✅ Invoice creado exitosamente: {data.get('id')}")
            return data['invoice_url'], data['id']
        else:
            logger.error(f"❌ Error NOWPayments: {response.text}")
    except Exception as e:
        logger.error(f"❌ Error creando invoice: {e}")
    return None, None

# Handler para /start
async def start(update: Update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Sin username"
    logger.info(f"📩 Comando /start recibido de usuario {user_id} (@{username})")
    
    try:
        # Verificar membresía existente
        logger.info(f"Verificando membresía existente para usuario {user_id}")
        result = supabase.table('memberships').select('*').eq('telegram_user_id', user_id).execute()
        
        if result.data:
            membership = result.data[0]
            end_date_str = membership['membership_end_date']
            logger.info(f"Membresía encontrada, expira: {end_date_str}")
            
            # Parsear fecha
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            
            if end_date > datetime.now(end_date.tzinfo):
                await update.message.reply_text(
                    f"¡Hola {username}! Ya eres miembro activo.\n"
                    f"Tu membresía expira el: {end_date.strftime('%d/%m/%Y %H:%M')}\n\n"
                    "Intentando añadirte al grupo..."
                )
                try:
                    await bot.unban_chat_member(GROUP_ID, user_id)
                    await bot.send_message(user_id, "✅ Has sido añadido al grupo exitosamente!")
                    logger.info(f"✅ Usuario {user_id} añadido al grupo")
                except Exception as e:
                    logger.error(f"❌ Error añadiendo al grupo: {e}")
                    await update.message.reply_text(f"❌ Error al añadir al grupo: {str(e)}")
                return

        # Crear nueva factura de pago
        logger.info(f"Creando nueva factura para usuario {user_id}")
        pay_url, invoice_id = create_invoice(user_id)
        if pay_url:
            await update.message.reply_text(
                f"¡Bienvenido a Ghost Traders! 👻\n\n"
                f"Para unirte al grupo VIP, realiza el pago de **10 USD en TRX**:\n\n"
                f"🔗 **Link de pago**: {pay_url}\n\n"
                f"📋 **Invoice ID**: {invoice_id}\n\n"
                f"Una vez completado el pago, serás añadido automáticamente al grupo.\n"
                f"Tu membresía durará 30 días."
            )
            logger.info(f"✅ Enlace de pago enviado a usuario {user_id}")
        else:
            await update.message.reply_text("❌ Error generando el enlace de pago. Intenta de nuevo más tarde.")
            logger.error(f"❌ No se pudo crear invoice para usuario {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Error en comando start: {e}")
        await update.message.reply_text("❌ Error interno. Intenta de nuevo más tarde.")

# Handler para otros mensajes
async def handle_message(update: Update, context):
    logger.info(f"📨 Mensaje recibido de usuario {update.message.from_user.id}")
    await update.message.reply_text("Usa /start para comenzar el proceso de membresía.")

# Webhook para NOWPayments IPN
@app.route('/webhook/nowpayments', methods=['POST'])
def nowpayments_webhook():
    logger.info("💰 Webhook NOWPayments recibido")
    try:
        data = request.get_json()
        signature = request.headers.get('x-nowpayments-sig')
        
        logger.info(f"Datos recibidos: {data}")
        logger.info(f"Signature: {signature}")
        
        if not data or not signature:
            logger.error("❌ Missing data or signature")
            return jsonify({"error": "Missing data or signature"}), 400
        
        # Verificar firma
        sorted_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        computed_sig = hmac.new(NOWPAYMENTS_IPN_SECRET.encode(), sorted_data.encode(), hashlib.sha512).hexdigest()
        
        if signature != computed_sig:
            logger.error(f"❌ Invalid signature. Expected: {computed_sig}, Got: {signature}")
            return jsonify({"error": "Invalid signature"}), 400

        logger.info("✅ Signature válida")

        if data.get('payment_status') == 'finished':
            order_id = data.get('order_id', '')
            logger.info(f"🎉 Pago completado para orden: {order_id}")
            
            if order_id.startswith('user_'):
                try:
                    user_id = int(order_id.split('_')[1])
                    end_date = datetime.now() + timedelta(days=30)
                    
                    # Insertar o actualizar membresía
                    supabase.table('memberships').upsert({
                        'telegram_user_id': user_id,
                        'membership_end_date': end_date.isoformat(),
                        'status': 'active'
                    }).execute()
                    
                    logger.info(f"✅ Membresía actualizada para usuario {user_id}")
                    
                    # Enviar mensaje de confirmación y añadir al grupo
                    asyncio.run_coroutine_threadsafe(
                        confirm_payment(user_id), 
                        asyncio.get_event_loop()
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando pago: {e}")
                    return jsonify({"error": "Processing error"}), 500
        else:
            logger.info(f"Estado de pago: {data.get('payment_status')} - No procesado")
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}")
        return jsonify({"error": "Server error"}), 500

async def confirm_payment(user_id):
    logger.info(f"Confirmando pago para usuario {user_id}")
    try:
        await bot.send_message(
            user_id, 
            "🎉 ¡Pago confirmado! Bienvenido a Ghost Traders.\n\n"
            "Añadiéndote al grupo VIP... ✅"
        )
        await bot.unban_chat_member(GROUP_ID, user_id)
        await bot.send_message(user_id, "✅ ¡Has sido añadido al grupo exitosamente!")
        logger.info(f"✅ Usuario {user_id} confirmado y añadido al grupo")
    except Exception as e:
        logger.error(f"❌ Error confirmando pago: {e}")
        await bot.send_message(user_id, f"❌ Error al añadir al grupo: {str(e)}")

# Endpoint para verificar membresías expiradas
@app.route('/check_memberships', methods=['GET'])
def check_memberships():
    logger.info("🔍 Verificando membresías expiradas")
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
                logger.info(f"Usuario {user_id} removido por membresía expirada")
            except Exception as e:
                logger.error(f"Error removiendo usuario {user_id}: {e}")

        logger.info(f"✅ Verificación completada. Usuarios removidos: {removed_count}")
        return jsonify({"status": "checked", "removed": removed_count}), 200
        
    except Exception as e:
        logger.error(f"❌ Error checking memberships: {e}")
        return jsonify({"error": "Server error"}), 500

# Webhook para Telegram
@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    logger.info("📱 Webhook Telegram recibido")
    try:
        json_data = request.get_json()
        logger.info(f"Datos de Telegram: {json_data}")
        
        update = Update.de_json(json_data, bot)
        if application:
            asyncio.run_coroutine_threadsafe(
                application.process_update(update),
                asyncio.get_event_loop()
            )
        logger.info("✅ Update procesado correctamente")
        return 'ok', 200
    except Exception as e:
        logger.error(f"❌ Error en webhook telegram: {e}")
        return 'error', 500

# Endpoints de salud
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "Ghost Traders Bot funcionando", 
        "timestamp": datetime.now().isoformat(),
        "version": "2.0"
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "bot_configured": bool(TELEGRAM_TOKEN and SUPABASE_URL and SUPABASE_KEY)
    })

# Configurar el bot
def setup_bot():
    global application
    logger.info("🤖 Configurando aplicación de Telegram")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Handlers configurados")

# Inicializar en un hilo separado
def start_bot():
    logger.info("🚀 Iniciando bot en hilo separado")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    setup_bot()
    logger.info("✅ Bot configurado, manteniendo loop activo")
    loop.run_forever()

if __name__ == '__main__':
    logger.info("🎬 Iniciando aplicación principal")
    
    # Iniciar bot en hilo separado
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("✅ Hilo del bot iniciado")
    
    # Iniciar servidor Flask
    logger.info(f"🌐 Iniciando servidor Flask en puerto {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)