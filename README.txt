Ghost Traders Bot
Descripción del Proyecto
Ghost Traders Bot es un bot de Telegram diseñado para gestionar un grupo de membresía privado. El bot automatiza el proceso de acceso al grupo, permitiendo a los usuarios unirse a través de un sistema de pago integrado con NOWPayments. La información de la membresía se almacena de forma segura en una base de datos de Supabase.

Características Principales
Gestión de Membresías: Añade y expulsa automáticamente a los usuarios del grupo VIP según el estado de su membresía.

Sistema de Pagos: Procesa pagos de membresía a través de NOWPayments (configurado para USDT en la red TRC20).

Persistencia de Datos: Utiliza Supabase como base de datos para registrar el estado de la membresía y sus fechas de vencimiento.

Despliegue Sencillo: Optimizado para el despliegue en Google Cloud Run utilizando Docker.

Requisitos Previos
Antes de ejecutar el bot, necesitarás configurar las siguientes cuentas y servicios:

Telegram: Un API Token de tu bot, obtenido a través de @BotFather.

Supabase: Un proyecto con una tabla memberships configurada para almacenar los datos de los usuarios.

NOWPayments: Una clave API y un IPN Secret para procesar los pagos.

Google Cloud (opcional): Una cuenta para el despliegue en Cloud Run.

Configuración y Despliegue
1. Variables de Entorno
Crea un archivo .env en la raíz de tu proyecto y añade las siguientes variables con tus credenciales.

TELEGRAM_TOKEN=tu-api-token-de-telegram
SUPABASE_URL=[https://tu-proyecto.supabase.co](https://tu-proyecto.supabase.co)
SUPABASE_KEY=tu-service-role-key-de-supabase
NOWPAYMENTS_API_KEY=tu-api-key-de-nowpayments
NOWPAYMENTS_IPN_SECRET=tu-ipn-secret-de-nowpayments
GROUP_ID=-123456789  # ID de tu grupo de Telegram (asegúrate de incluir el signo negativo)
PORT=8080

2. Instalación de Dependencias
El proyecto utiliza Python 3.11. Instala las dependencias necesarias con pip.

pip install -r requirements.txt

3. Despliegue en Google Cloud Run
El proyecto incluye un Dockerfile para un despliegue sencillo. Puedes usar el siguiente comando para desplegarlo, reemplazando los valores por tus propias variables.

gcloud run deploy ghost-traders-bot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars TELEGRAM_TOKEN=...,SUPABASE_URL=...,SUPABASE_KEY=...,NOWPAYMENTS_API_KEY=...,NOWPAYMENTS_IPN_SECRET=...,GROUP_ID=...

4. Configuración de Webhooks
Una vez que el bot esté desplegado, necesitas configurar los webhooks para que Telegram y NOWPayments puedan comunicarse con tu servicio.

Webhook de Telegram:

[https://api.telegram.org/bot](https://api.telegram.org/bot)<TU_TELEGRAM_TOKEN>/setWebhook?url=<TU_URL_DE_CLOUD_RUN>/webhook/telegram

Webhook de NOWPayments:
Configura la URL de IPN en la sección de ajustes de tu cuenta de NOWPayments.

https://<TU_URL_DE_CLOUD_RUN>/webhook/nowpayments

Uso
Para interactuar con el bot, simplemente inicia una conversación y usa el comando /start. El bot generará un enlace de pago de NOWPayments. Una vez que el pago sea exitoso, el usuario será añadido automáticamente al grupo VIP.