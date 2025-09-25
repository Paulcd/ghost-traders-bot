Ghost Traders Bot

Descripcion del Proyecto
=========================

Ghost Traders Bot es un bot de Telegram diseñado para gestionar un grupo de membresia privado. Este bot automatiza el proceso de acceso, permitiendo a los usuarios unirse al grupo VIP a traves de un sistema de pago integrado con NOWPayments. La informacion de la membresia se almacena de forma segura en una base de datos de Supabase.

Caracteristicas Clave
=====================

• Gestion de Membresias: Añade y expulsa automaticamente a los usuarios del grupo segun el estado de su membresia.

• Sistema de Pagos: Procesa pagos de membresia a traves de NOWPayments (configurado para USDT en la red TRC20).

• Persistencia de Datos: Utiliza Supabase como base de datos para registrar el estado de la membresia y sus fechas de vencimiento.

• Despliegue Sencillo: Optimizado para el despliegue en la plataforma de Render.com.

Requisitos Previos
==================

Antes de ejecutar el bot, asegurate de tener configurado lo siguiente:

• Telegram: Un API Token de tu bot, obtenido a traves de @BotFather (https://t.me/BotFather).

• Supabase: Un proyecto con una tabla memberships y la service_role key para las operaciones de escritura.

• NOWPayments: Una clave API y un IPN Secret.

• GitHub: Tu codigo subido a un repositorio para que Render pueda acceder a el.

Configuracion y Despliegue
==========================

Paso 1: Variables de Entorno
-----------------------------

Crea un archivo .env en la raiz de tu proyecto para gestionar tus credenciales de forma segura. Recuerda no subir este archivo a tu repositorio de GitHub.

TELEGRAM_TOKEN=tu-api-token-de-telegram
SUPABASE_URL=https://bkzfxeigfgfgbtuegmtgr.supabase.co
SUPABASE_KEY=tu-service-role-key-aqui
NOWPAYMENTS_API_KEY=tu-api-key-de-nowpayments
NOWPAYMENTS_IPN_SECRET=tu-ipn-secret-de-nowpayments
GROUP_ID=-1002800092793 # ID de tu grupo de Telegram (asegurate de incluir el signo negativo)
PORT=8080

Paso 2: Despliegue en Render.com
---------------------------------

1. Crea una cuenta en https://render.com y conectala a tu cuenta de GitHub.

2. Crea un nuevo Web Service:
   • Selecciona tu repositorio de GitHub.
   • Nombre: ghost-traders-bot.
   • Environment: Python 3.
   • Build Command: pip install -r requirements.txt.
   • Start Command: gunicorn --bind 0.0.0.0:$PORT main:app.

3. Configura las variables de entorno:
   • En la seccion "Environment Variables", anade cada una de las variables de tu archivo .env con sus valores correspondientes.

4. Despliega: Haz clic en "Create Web Service". Render automaticamente construira y desplegara tu bot.

Paso 3: Configuracion de Webhooks
----------------------------------

Una vez que tu bot este desplegado, Render te proporcionara una URL publica (ej: https://ghost-traders-bot-abc123.onrender.com). Usa esta URL para configurar los webhooks.

• Webhook de Telegram:
  https://api.telegram.org/bot<TU_TELEGRAM_TOKEN>/setWebhook?url=<TU_URL_DE_RENDER>/webhook/telegram

• Webhook de NOWPayments:
  Configura la URL de IPN en la seccion de ajustes de tu cuenta de NOWPayments.
  https://<TU_URL_DE_RENDER>/webhook/nowpayments

Paso 4: Automatizar la Verificacion de Membresias
---------------------------------------------------

Debido a que Render "duerme" los servicios inactivos, puedes usar un servicio externo como Uptime Robot (https://uptimerobot.com) para hacer llamadas periodicas y mantener tu bot activo y revisando las membresias.

• Crea un monitor en Uptime Robot (https://uptimerobot.com).
• Selecciona el tipo de monitor "HTTP(s)".
• URL: https://<TU_URL_DE_RENDER>/check_memberships
• Intervalo: Configura la llamada para que se ejecute cada 24 horas.

Uso del Bot
===========

Para interactuar con el bot, simplemente inicia una conversacion y usa el comando /start. El bot generara un enlace de pago de NOWPayments. Una vez que el pago sea exitoso, el usuario sera anadido automaticamente al grupo VIP.