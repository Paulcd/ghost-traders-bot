import os
import sys
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, filters, MessageHandler, CallbackQueryHandler
from supabase import create_client, Client
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import asyncio
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
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
GROUP_ID = int(os.getenv('GROUP_ID', -1002202662368))
PORT = int(os.getenv('PORT', 8080))

logger.info(f"🚀 Iniciando Ghost Traders Bot")
logger.info(f"- TELEGRAM_TOKEN: {'✅' if TELEGRAM_TOKEN else '❌'}")
logger.info(f"- SUPABASE_URL: {'✅' if SUPABASE_URL else '❌'}")
logger.info(f"- SUPABASE_KEY: {'✅' if SUPABASE_KEY else '❌'}")
logger.info(f"- NOWPAYMENTS_API_KEY: {'✅' if NOWPAYMENTS_API_KEY else '❌'}")
logger.info(f"- GROUP_ID: {GROUP_ID}")
logger.info(f"- PORT: {PORT}")

# Inicializar servicios
try:
    bot = Bot(TELEGRAM_TOKEN)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Bot y Supabase inicializados correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando servicios: {e}")
    sys.exit(1)

# Variable global para la aplicación
application = None

def get_base_url():
    """Obtener la URL base del servidor"""
    return os.getenv('RENDER_EXTERNAL_URL', 'https://ghost-traders-bot.onrender.com')

def create_invoice(user_id, amount=12):
    """Crear factura en NOWPayments"""
    logger.info(f"🧾 Creando invoice para usuario {user_id}, monto: ${amount}")
    
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    base_url = get_base_url()
    
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",  # USDT TRC20
        "order_id": f"user_{user_id}_{int(datetime.now().timestamp())}",
        "order_description": "Ghost Traders - Membresía 30 días",
        "ipn_callback_url": f"{base_url}/webhook/nowpayments",
        "success_url": "https://t.me/ghost_traders_bot?start=success",
        "cancel_url": "https://t.me/ghost_traders_bot?start=cancelled"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        logger.info(f"📡 NOWPayments response: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            logger.info(f"✅ Invoice creado: {data.get('id')}")
            return data.get('invoice_url'), data.get('id')
        else:
            logger.error(f"❌ Error NOWPayments: {response.text}")
            return None, None
            
    except requests.exceptions.Timeout:
        logger.error("⏰ Timeout creando invoice")
        return None, None
    except Exception as e:
        logger.error(f"❌ Excepción creando invoice: {e}")
        return None, None

async def start_command(update: Update, context):
    """Handler del comando /start"""
    user = update.effective_user
    user_id = user.id
    username = user.username or "Sin username"
    first_name = user.first_name or "Usuario"
    
    logger.info(f"👤 /start de {first_name} (@{username}) - ID: {user_id}")
    
    try:
        # Verificar membresía activa
        result = supabase.table('memberships').select('*').eq('telegram_user_id', user_id).execute()
        
        if result.data:
            membership = result.data[0]
            end_date_str = membership['membership_end_date']
            
            # Parsear fecha correctamente
            if end_date_str.endswith('Z'):
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            elif '+00:00' in end_date_str:
                end_date = datetime.fromisoformat(end_date_str)
            else:
                end_date = datetime.fromisoformat(end_date_str + '+00:00')
            
            if end_date > datetime.now(end_date.tzinfo):
                # Membresía activa
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Unirse al Grupo", callback_data=f"join_group_{user_id}")],
                    [InlineKeyboardButton("📊 Mi Membresía", callback_data=f"my_membership_{user_id}")]
                ])
                
                await update.message.reply_text(
                    f"¡Hola {first_name}! 👻\n\n"
                    f"✅ Tu membresía está **ACTIVA**\n"
                    f"📅 Expira: {end_date.strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"Haz clic en 'Unirse al Grupo' para obtener el enlace:",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return

        # Usuario nuevo o membresía expirada
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Pagar Membresía - $12 USDT", callback_data=f"pay_membership_{user_id}")],
            [InlineKeyboardButton("ℹ️ Información", callback_data="info")]
        ])
        
        await update.message.reply_text(
            f"¡Bienvenido a Ghost Traders! 👻\n\n"
            f"🎯 **Plan de Prueba Especial**\n"
            f"💰 Solo **$12 USDT (TRC20)**\n"
            f"⏰ Acceso por **30 días**\n\n"
            f"🔥 **¿Qué obtienes?**\n"
            f"• Acceso al grupo VIP\n"
            f"• Señales de trading premium\n"
            f"• Análisis técnico diario\n"
            f"• Soporte 24/7\n\n"
            f"👇 Haz clic para comenzar:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Error en start_command: {e}")
        await update.message.reply_text(
            "❌ Error interno. Intenta de nuevo en un momento.",
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context):
    """Handler para botones inline"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    logger.info(f"🔘 Callback: {data} de usuario {user.id}")
    
    await query.answer()
    
    if data.startswith("pay_membership_"):
        user_id = int(data.split("_")[-1])
        
        # Crear invoice
        pay_url, invoice_id = await asyncio.to_thread(create_invoice, user_id, 12)
        
        if pay_url and invoice_id:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Realizar Pago", url=pay_url)],
                [InlineKeyboardButton("🔄 Verificar Pago", callback_data=f"check_payment_{user_id}_{invoice_id}")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                f"💳 **Pago Generado**\n\n"
                f"💰 **Monto**: $12 USDT (TRC20)\n"
                f"📋 **Invoice ID**: `{invoice_id}`\n\n"
                f"**⚠️ Instrucciones:**\n"
                f"1. Haz clic en 'Realizar Pago'\n"
                f"2. Completa el pago exacto\n"
                f"3. Vuelve y haz clic en 'Verificar Pago'\n\n"
                f"⏱️ El pago expira en 30 minutos",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ Error generando el enlace de pago.\n"
                "Intenta de nuevo más tarde.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Reintentar", callback_data=f"pay_membership_{user_id}")
                ]])
            )
    
    elif data.startswith("check_payment_"):
        parts = data.split("_")
        user_id = int(parts[2])
        invoice_id = parts[3]
        
        # Verificar estado del pago
        await verify_payment_status(query, user_id, invoice_id)
    
    elif data.startswith("join_group_"):
        user_id = int(data.split("_")[-1])
        await generate_group_invite(query, user_id)
    
    elif data.startswith("my_membership_"):
        user_id = int(data.split("_")[-1])
        await show_membership_info(query, user_id)
    
    elif data == "info":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")
        ]])
        
        await query.edit_message_text(
            f"📊 **Información del Servicio**\n\n"
            f"🏷️ **Precio**: $12 USDT (TRC20)\n"
            f"⏰ **Duración**: 30 días\n"
            f"💳 **Método de pago**: Crypto (USDT TRC20)\n"
            f"🔒 **Seguro**: Pagos procesados por NOWPayments\n\n"
            f"❓ **¿Dudas?** Contacta: @admin\n",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    elif data == "back_to_start":
        # Simular comando start
        await start_command_from_callback(query)

async def verify_payment_status(query, user_id, invoice_id):
    """Verificar estado del pago en NOWPayments"""
    logger.info(f"🔍 Verificando pago {invoice_id} para usuario {user_id}")
    
    try:
        url = f"https://api.nowpayments.io/v1/payment/{invoice_id}"
        headers = {"x-api-key": NOWPAYMENTS_API_KEY}
        
        response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('payment_status', 'unknown')
            
            logger.info(f"📊 Estado del pago: {status}")
            
            if status == 'finished':
                # Activar membresía
                end_date = datetime.now() + timedelta(days=30)
                
                # Función síncrona para Supabase
                def update_membership():
                    supabase.table('memberships').upsert({
                        'telegram_user_id': user_id,
                        'membership_end_date': end_date.isoformat(),
                        'status': 'active',
                        'payment_id': invoice_id
                    }).execute()
                
                await asyncio.to_thread(update_membership)
                
                logger.info(f"✅ Membresía activada para usuario {user_id}")
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔗 Unirse al Grupo", callback_data=f"join_group_{user_id}")
                ]])
                
                await query.edit_message_text(
                    f"🎉 **¡Pago Confirmado!**\n\n"
                    f"✅ Tu membresía ha sido activada\n"
                    f"📅 Válida hasta: {end_date.strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"¡Bienvenido a Ghost Traders! 👻",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif status in ['waiting', 'confirming', 'sending']:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Verificar Nuevamente", callback_data=f"check_payment_{user_id}_{invoice_id}")],
                    [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")]
                ])
                
                await query.edit_message_text(
                    f"⏳ **Pago en Proceso**\n\n"
                    f"📊 Estado actual: `{status}`\n"
                    f"🔄 Verificaremos automáticamente tu pago\n\n"
                    f"Por favor espera unos minutos...",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            else:
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Reintentar Pago", callback_data=f"pay_membership_{user_id}")
                ]])
                
                await query.edit_message_text(
                    f"❌ **Pago No Encontrado**\n\n"
                    f"📊 Estado: `{status}`\n"
                    f"💡 Si ya pagaste, espera unos minutos\n"
                    f"🔄 O genera un nuevo enlace de pago",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        
        else:
            logger.error(f"❌ Error verificando pago: {response.status_code}")
            await query.answer("❌ Error verificando el pago. Intenta de nuevo.")
    
    except Exception as e:
        logger.error(f"❌ Excepción verificando pago: {e}")
        await query.answer("❌ Error de conexión. Intenta de nuevo.")

async def generate_group_invite(query, user_id):
    """Generar enlace de invitación al grupo"""
    logger.info(f"🔗 Generando enlace de grupo para usuario {user_id}")
    
    try:
        # Crear enlace de invitación temporal
        invite_link = await bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1,
            expire_date=int((datetime.now() + timedelta(minutes=10)).timestamp())
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Unirse Ahora", url=invite_link.invite_link)],
            [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")]
        ])
        
        await query.edit_message_text(
            f"🎯 **Enlace de Invitación**\n\n"
            f"🔗 Tu enlace personal está listo\n"
            f"⏰ Válido por **10 minutos**\n\n"
            f"👇 Haz clic para unirte:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Enlace generado para usuario {user_id}")
    
    except Exception as e:
        logger.error(f"❌ Error generando enlace: {e}")
        await query.edit_message_text(
            f"❌ Error generando enlace de invitación.\n"
            f"Contacta al administrador: @admin",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")
            ]])
        )

async def show_membership_info(query, user_id):
    """Mostrar información de la membresía"""
    try:
        def get_membership():
            return supabase.table('memberships').select('*').eq('telegram_user_id', user_id).execute()
        
        result = await asyncio.to_thread(get_membership)
        
        if result.data:
            membership = result.data[0]
            end_date_str = membership['membership_end_date']
            
            if end_date_str.endswith('Z'):
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            else:
                end_date = datetime.fromisoformat(end_date_str + '+00:00')
            
            days_left = (end_date - datetime.now(end_date.tzinfo)).days
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Unirse al Grupo", callback_data=f"join_group_{user_id}")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")]
            ])
            
            await query.edit_message_text(
                f"📊 **Tu Membresía**\n\n"
                f"✅ Estado: **Activa**\n"
                f"📅 Expira: {end_date.strftime('%d/%m/%Y %H:%M')}\n"
                f"⏰ Días restantes: **{days_left}**\n\n"
                f"🎯 Disfruta el acceso premium!",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ No tienes membresía activa",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Volver", callback_data="back_to_start")
                ]])
            )
    
    except Exception as e:
        logger.error(f"❌ Error mostrando membresía: {e}")
        await query.answer("❌ Error obteniendo información")

async def start_command_from_callback(query):
    """Comando start desde callback"""
    user = query.from_user
    user_id = user.id
    first_name = user.first_name or "Usuario"
    
    try:
        def get_membership():
            return supabase.table('memberships').select('*').eq('telegram_user_id', user_id).execute()
        
        result = await asyncio.to_thread(get_membership)
        
        if result.data:
            membership = result.data[0]
            end_date_str = membership['membership_end_date']
            
            if end_date_str.endswith('Z'):
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            else:
                end_date = datetime.fromisoformat(end_date_str + '+00:00')
            
            if end_date > datetime.now(end_date.tzinfo):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Unirse al Grupo", callback_data=f"join_group_{user_id}")],
                    [InlineKeyboardButton("📊 Mi Membresía", callback_data=f"my_membership_{user_id}")]
                ])
                
                await query.edit_message_text(
                    f"¡Hola {first_name}! 👻\n\n"
                    f"✅ Tu membresía está **ACTIVA**\n"
                    f"📅 Expira: {end_date.strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"Haz clic en 'Unirse al Grupo' para obtener el enlace:",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Pagar Membresía - $12 USDT", callback_data=f"pay_membership_{user_id}")],
            [InlineKeyboardButton("ℹ️ Información", callback_data="info")]
        ])
        
        await query.edit_message_text(
            f"¡Bienvenido a Ghost Traders! 👻\n\n"
            f"🎯 **Plan de Prueba Especial**\n"
            f"💰 Solo **$12 USDT (TRC20)**\n"
            f"⏰ Acceso por **30 días**\n\n"
            f"🔥 **¿Qué obtienes?**\n"
            f"• Acceso al grupo VIP\n"
            f"• Señales de trading premium\n"
            f"• Análisis técnico diario\n"
            f"• Soporte 24/7\n\n"
            f"👇 Haz clic para comenzar:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"❌ Error en start_command_from_callback: {e}")
        await query.edit_message_text("❌ Error interno. Intenta de nuevo.")

async def handle_message(update: Update, context):
    """Handler para mensajes de texto"""
    await update.message.reply_text(
        "👋 ¡Hola! Usa /start para comenzar el proceso de membresía.",
        parse_mode='Markdown'
    )

# ============= WEBHOOKS FLASK =============

@app.route('/webhook/nowpayments', methods=['POST'])
def nowpayments_webhook():
    """Webhook para NOWPayments IPN"""
    logger.info("💰 Webhook NOWPayments recibido")
    
    try:
        data = request.get_json()
        signature = request.headers.get('x-nowpayments-sig')
        
        if not data or not signature:
            logger.error("❌ Missing data or signature")
            return jsonify({"error": "Missing data or signature"}), 400
        
        # Verificar firma
        sorted_data = json.dumps(data, sort_keys=True, separators=(',', ':'))
        computed_sig = hmac.new(
            NOWPAYMENTS_IPN_SECRET.encode(), 
            sorted_data.encode(), 
            hashlib.sha512
        ).hexdigest()
        
        if signature != computed_sig:
            logger.error(f"❌ Invalid signature")
            return jsonify({"error": "Invalid signature"}), 400
        
        logger.info("✅ Signature válida")
        logger.info(f"📊 Datos del pago: {data}")
        
        payment_status = data.get('payment_status')
        order_id = data.get('order_id', '')
        payment_id = data.get('payment_id', '')
        
        if payment_status == 'finished' and order_id.startswith('user_'):
            try:
                user_id = int(order_id.split('_')[1])
                end_date = datetime.now() + timedelta(days=30)
                
                # Función síncrona para actualizar Supabase
                def update_membership():
                    supabase.table('memberships').upsert({
                        'telegram_user_id': user_id,
                        'membership_end_date': end_date.isoformat(),
                        'status': 'active',
                        'payment_id': payment_id
                    }).execute()
                
                # Ejecutar la actualización en un thread separado
                threading.Thread(target=update_membership).start()
                
                logger.info(f"✅ Membresía activada automáticamente para usuario {user_id}")
                
                # Enviar notificación asíncrona
                def send_notification():
                    try:
                        asyncio.run(send_payment_confirmation(user_id))
                    except Exception as e:
                        logger.error(f"❌ Error enviando notificación: {e}")
                
                threading.Thread(target=send_notification).start()
                
            except Exception as e:
                logger.error(f"❌ Error procesando pago: {e}")
                return jsonify({"error": "Processing error"}), 500
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}")
        return jsonify({"error": "Server error"}), 500

async def send_payment_confirmation(user_id):
    """Enviar confirmación de pago al usuario"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text="🎉 **¡Pago Confirmado!**\n\n"
                 "✅ Tu membresía ha sido activada\n"
                 "🔗 Ya puedes unirte al grupo VIP\n\n"
                 "Usa /start para obtener el enlace de acceso",
            parse_mode='Markdown'
        )
        logger.info(f"✅ Notificación enviada a usuario {user_id}")
    except Exception as e:
        logger.error(f"❌ Error enviando notificación: {e}")

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Webhook para Telegram"""
    logger.info("📱 Webhook Telegram recibido")
    
    try:
        json_data = request.get_json()
        if not json_data:
            logger.error("❌ No JSON data received")
            return 'error', 400
        
        logger.info(f"📋 Datos recibidos: {json_data}")
        
        update = Update.de_json(json_data, bot)
        
        if application:
            # NUEVA IMPLEMENTACIÓN: Crear un nuevo loop para el hilo
            def process_update_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(application.process_update(update))
                    loop.close()
                    logger.info("✅ Update procesado correctamente")
                except Exception as e:
                    logger.error(f"❌ Error procesando update: {e}")
            
            # Ejecutar en un hilo separado
            threading.Thread(target=process_update_thread, daemon=True).start()
        else:
            logger.error("❌ Application no está inicializada")
            return 'error', 500
        
        return 'ok', 200
        
    except Exception as e:
        logger.error(f"❌ Error en webhook telegram: {e}")
        return 'error', 500

@app.route('/check_memberships', methods=['GET'])
def check_memberships():
    """Verificar y limpiar membresías expiradas"""
    logger.info("🔍 Verificando membresías expiradas")
    
    try:
        now = datetime.now().isoformat()
        
        # Función síncrona para obtener membresías expiradas
        def get_expired_memberships():
            return supabase.table('memberships').select('telegram_user_id').lt('membership_end_date', now).eq('status', 'active').execute()
        
        expired_result = get_expired_memberships()
        expired_data = expired_result.data
        removed_count = 0
        
        for member in expired_data:
            user_id = member['telegram_user_id']
            try:
                # Función síncrona para actualizar membresía
                def update_expired_membership(u_id):
                    supabase.table('memberships').update({
                        'status': 'expired'
                    }).eq('telegram_user_id', u_id).execute()
                
                update_expired_membership(user_id)
                removed_count += 1
                logger.info(f"🗑️ Membresía expirada marcada para usuario {user_id}")
                
                # Enviar notificación de expiración
                def send_expiration():
                    try:
                        asyncio.run(send_expiration_notice(user_id))
                    except Exception as e:
                        logger.error(f"❌ Error enviando notificación de expiración: {e}")
                
                threading.Thread(target=send_expiration).start()
                
            except Exception as e:
                logger.error(f"❌ Error procesando usuario expirado {user_id}: {e}")
        
        logger.info(f"✅ Verificación completada. Membresías expiradas: {removed_count}")
        return jsonify({"status": "checked", "expired": removed_count}), 200
        
    except Exception as e:
        logger.error(f"❌ Error checking memberships: {e}")
        return jsonify({"error": "Server error"}), 500

async def send_expiration_notice(user_id):
    """Enviar notificación de expiración"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text="⏰ **Membresía Expirada**\n\n"
                 "Tu acceso premium ha terminado.\n"
                 "¿Quieres renovar? Usa /start para ver opciones.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de expiración a {user_id}: {e}")

@app.route('/test_bot', methods=['GET'])
def test_bot():
    """Endpoint para probar el bot manualmente"""
    try:
        # Simular un update de /start
        test_update = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 12345,
                    "is_bot": False,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": 12345,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": 1640995200,
                "text": "/start"
            }
        }
        
        update = Update.de_json(test_update, bot)
        
        def process_test():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(application.process_update(update))
                loop.close()
                logger.info("✅ Test update procesado")
            except Exception as e:
                logger.error(f"❌ Error en test: {e}")
        
        threading.Thread(target=process_test, daemon=True).start()
        
        return jsonify({"status": "test_enviado", "update": test_update}), 200
        
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        return jsonify({"error": str(e)}), 500

# Endpoints de salud
@app.route('/', methods=['GET'])
def home():
    """Endpoint principal"""
    return jsonify({
        "status": "Ghost Traders Bot funcionando",
        "version": "3.0",
        "timestamp": datetime.now().isoformat(),
        "bot_username": "@ghost_traders_bot"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "telegram": bool(TELEGRAM_TOKEN),
            "supabase": bool(SUPABASE_URL and SUPABASE_KEY),
            "nowpayments": bool(NOWPAYMENTS_API_KEY),
            "bot_configured": application is not None
        }
    })

@app.route('/webhook/nowpayments', methods=['GET'])
def nowpayments_webhook_get():
    """GET endpoint para verificar webhook"""
    return jsonify({
        "message": "NOWPayments webhook endpoint",
        "method": "POST required",
        "status": "ready"
    })

@app.route('/webhook/telegram', methods=['GET'])
def telegram_webhook_get():
    """GET endpoint para verificar webhook"""
    return jsonify({
        "message": "Telegram webhook endpoint", 
        "method": "POST required",
        "status": "ready"
    })

# ============= CONFIGURACIÓN DEL BOT =============

def setup_application():
    """Configurar la aplicación de Telegram"""
    global application
    
    if application is not None:
        logger.info("✅ Aplicación ya configurada")
        return True
    
    try:
        # Crear la aplicación
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Registrar handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("✅ Aplicación configurada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error configurando aplicación: {e}")
        return False

async def initialize_bot():
    """Inicializar el bot de forma asíncrona"""
    if not setup_application():
        logger.error("❌ No se pudo configurar la aplicación")
        return False
    
    try:
        # Inicializar la aplicación
        await application.initialize()
        await application.start()
        
        # Establecer webhook
        webhook_url = f"{get_base_url()}/webhook/telegram"
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook establecido en: {webhook_url}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando bot: {e}")
        return False

# ============= INICIALIZACIÓN =============

def init_bot_sync():
    """Inicializar el bot de forma síncrona para Gunicorn"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(initialize_bot())
        if success:
            logger.info("✅ Bot inicializado correctamente")
        else:
            logger.error("❌ Error inicializando bot")
        return success
    except Exception as e:
        logger.error(f"❌ Error en inicialización síncrona: {e}")
        return False

# Inicializar el bot cuando se importa el módulo
logger.info("🎬 Inicializando bot...")
init_bot_sync()

if __name__ == '__main__':
    # Modo desarrollo
    logger.info("🌐 Modo desarrollo - usando Flask dev server")
    app.run(host='0.0.0.0', port=PORT, debug=False)