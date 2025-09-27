# 👻 Ghost Traders Bot

## 📖 Descripción del Proyecto

**Ghost Traders Bot** es un bot de Telegram avanzado diseñado para gestionar un grupo de membresía privado de trading. Automatiza completamente el proceso de acceso al grupo VIP a través de un sistema de pagos integrado con criptomonedas, ofreciendo una experiencia fluida y segura para los usuarios.

### 🎯 **¿Qué hace?**
- Procesa pagos automáticos en USDT (TRC20)
- Genera enlaces de invitación temporales al grupo VIP
- Gestiona membresías con fechas de expiración
- Envía notificaciones automáticas de pagos y vencimientos
- Mantiene la seguridad del grupo mediante verificación constante

---

## ⚡ Características Clave

### 🔐 **Gestión Inteligente de Membresías**
- ✅ Activación automática al confirmar pago
- ⏰ Control de vencimiento con notificaciones
- 🔗 Enlaces de invitación únicos y temporales (10 min)
- 📊 Dashboard de estado de membresía para usuarios

### 💰 **Sistema de Pagos Avanzado**
- 💳 Integración completa con **NOWPayments**
- 🪙 Soporte para **USDT TRC20** (expandible a otras cryptos)
- 🔒 Verificación de firmas IPN para máxima seguridad
- ⚡ Confirmación instantánea de pagos

### 🗄️ **Base de Datos Robusta**
- 🛡️ **Supabase** como backend seguro y escalable
- 📈 Tracking completo de transacciones
- 🔄 Sincronización en tiempo real
- 📊 Análisis de datos de membresía

### 🚀 **Deployment Profesional**
- 🌐 Optimizado para **Render.com**
- 📱 Webhooks confiables para Telegram y pagos
- 🔄 Auto-reinicio y monitoreo de salud
- 📈 Escalable y mantenible

---

## 🛠️ Requisitos Previos

Antes de comenzar, asegúrate de tener:

### 📱 **Telegram**
- [ ] Bot Token de [@BotFather](https://t.me/BotFather)
- [ ] ID de tu grupo privado (con el bot como administrador)

### 🗄️ **Supabase**
- [ ] Proyecto activo en [Supabase](https://supabase.com)
- [ ] Tabla `memberships` configurada
- [ ] Service Role Key (no la anon key)

### 💳 **NOWPayments**
- [ ] Cuenta verificada en [NOWPayments](https://nowpayments.io)
- [ ] API Key activa
- [ ] IPN Secret configurado

### 👨‍💻 **Desarrollo**
- [ ] Repositorio en GitHub
- [ ] Python 3.9+ (para desarrollo local)

---

## 🚀 Configuración y Despliegue

### 📋 **Paso 1: Estructura de la Base de Datos**

Crea esta tabla en tu proyecto de Supabase:

```sql
CREATE TABLE memberships (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    membership_end_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    payment_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para mejor performance
CREATE INDEX idx_telegram_user_id ON memberships(telegram_user_id);
CREATE INDEX idx_membership_end_date ON memberships(membership_end_date);
CREATE INDEX idx_status ON memberships(status);
```

### 🔐 **Paso 2: Variables de Entorno**

Crea un archivo `.env` en la raíz de tu proyecto:

```bash
# Bot de Telegram
TELEGRAM_TOKEN=1234567890:ABCdefGhIjKlMnOpQrStUvWxYz
GROUP_ID=-1002202662368

# Base de datos Supabase  
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=tu-service-role-key-aqui

# Procesador de pagos NOWPayments
NOWPAYMENTS_API_KEY=tu-api-key-aqui
NOWPAYMENTS_IPN_SECRET=tu-ipn-secret-aqui

# Configuración del servidor
PORT=8080
RENDER_EXTERNAL_URL=https://tu-app.onrender.com
```

> ⚠️ **Importante**: Nunca subas el archivo `.env` a GitHub. Añádelo a tu `.gitignore`

### 🌐 **Paso 3: Despliegue en Render.com**

#### 3.1 **Crear el Servicio**
1. Ve a [Render.com](https://render.com) y conecta tu GitHub
2. Crea un nuevo **Web Service**:
   - **Repository**: Tu repo de GitHub  
   - **Name**: `ghost-traders-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 main:app`

#### 3.2 **Configurar Variables de Entorno**
En la sección **Environment Variables**, añade todas las variables de tu `.env`:

```
TELEGRAM_TOKEN = tu-token-aqui
SUPABASE_URL = tu-url-aqui
SUPABASE_KEY = tu-key-aqui
NOWPAYMENTS_API_KEY = tu-api-key-aqui
NOWPAYMENTS_IPN_SECRET = tu-secret-aqui
GROUP_ID = -1002202662368
RENDER_EXTERNAL_URL = https://ghost-traders-bot.onrender.com
```

#### 3.3 **Desplegar**
- Haz clic en **"Create Web Service"**
- Render construirá y desplegará automáticamente
- Espera a que el estado sea **"Live"** 🟢

### 🔗 **Paso 4: Configurar Webhooks**

Una vez desplegado, tendrás una URL como `https://ghost-traders-bot-xyz.onrender.com`

#### 4.1 **Webhook de Telegram**
Ejecuta este comando (reemplaza los valores):

```bash
curl "https://api.telegram.org/bot<TU_TELEGRAM_TOKEN>/setWebhook?url=<TU_URL_DE_RENDER>/webhook/telegram"
```

#### 4.2 **Webhook de NOWPayments** 
1. Entra a tu [dashboard de NOWPayments](https://nowpayments.io)
2. Ve a **Settings → IPN**  
3. Configura la URL: `https://tu-app.onrender.com/webhook/nowpayments`

### ⚙️ **Paso 5: Monitoreo Automático**

Para mantener el bot activo 24/7 y verificar membresías:

#### 5.1 **UptimeRobot (Recomendado - Gratis)**
1. Crea una cuenta en [UptimeRobot](https://uptimerobot.com)
2. Nuevo Monitor:
   - **Type**: HTTP(s)
   - **URL**: `https://tu-app.onrender.com/check_memberships`
   - **Interval**: 24 horas
   - **Name**: Ghost Traders Health Check

#### 5.2 **Cron-job.org (Alternativa)**
1. Ve a [cron-job.org](https://cron-job.org)
2. Crea un trabajo:
   - **URL**: `https://tu-app.onrender.com/check_memberships`
   - **Schedule**: `0 12 * * *` (diario a las 12:00)

---

## 🎮 Uso del Bot

### 👤 **Para Usuarios**

1. **Iniciar**: Envía `/start` al bot
2. **Pagar**: Clic en "💰 Pagar Membresía - $12 USDT"  
3. **Completar**: Realiza el pago en USDT TRC20
4. **Verificar**: Clic en "🔄 Verificar Pago"
5. **Acceder**: Una vez confirmado, clic en "🔗 Unirse al Grupo"

### 🔧 **Para Administradores**

#### **Endpoints de Monitoreo**:
- `GET /` - Estado general del bot
- `GET /health` - Health check detallado  
- `GET /check_memberships` - Verificar y limpiar membresías expiradas

#### **Logs en Tiempo Real**:
```bash
# Ver logs en Render
render logs -s tu-servicio-id --tail
```

---

## 📊 Estructura del Proyecto

```
ghost-traders-bot/
├── main.py                 # 🚀 Aplicación principal
├── requirements.txt        # 📦 Dependencias Python
├── render.yaml            # ⚙️ Configuración de Render
├── .env                   # 🔐 Variables de entorno (local)
├── .gitignore            # 🚫 Archivos a ignorar
└── README.md             # 📖 Este archivo
```

---

## 🔧 Desarrollo Local

### **Instalación**:
```bash
# Clonar el repositorio
git clone https://github.com/Paulcd/ghost-traders-bot
cd ghost-traders-bot

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# Ejecutar en modo desarrollo
python main.py
```

### **Testing con ngrok**:
```bash
# Instalar ngrok
npm install -g ngrok

# Exponer puerto local
ngrok http 8080

# Usar la URL https://xxx.ngrok.io para webhooks
```

---

## 🚨 Solución de Problemas

### **❌ Bot no responde**
- [ ] Verificar que el webhook esté configurado correctamente
- [ ] Revisar logs en Render: `render logs -s tu-servicio`
- [ ] Verificar variables de entorno en Render

### **💳 Pagos no se procesan**  
- [ ] Confirmar configuración del webhook de NOWPayments
- [ ] Verificar API Key y IPN Secret
- [ ] Revisar logs del endpoint `/webhook/nowpayments`

### **🗄️ Errores de base de datos**
- [ ] Verificar que la tabla `memberships` existe
- [ ] Usar Service Role Key (no anon key) de Supabase
- [ ] Confirmar permisos de lectura/escritura

### **⏰ Membresías no expiran**
- [ ] Verificar que UptimeRobot esté activo
- [ ] Probar manualmente: `GET /check_memberships`
- [ ] Revisar zona horaria de las fechas

---

## 🛡️ Seguridad

### **🔒 Buenas Prácticas Implementadas**:
- ✅ Verificación de firmas IPN de NOWPayments
- ✅ Variables de entorno para credenciales sensibles
- ✅ Enlaces de invitación temporales (10 minutos)
- ✅ Validación de datos de entrada en todos los endpoints
- ✅ Logging detallado sin exponer información sensible

### **🚨 Recomendaciones Adicionales**:
- Rotar API keys periódicamente
- Monitorear logs de acceso regularmente
- Mantener actualizadas las dependencias
- Hacer backups regulares de la base de datos

---

## 📈 Roadmap

### **🔜 Próximas Características**:
- [ ] Dashboard web de administración
- [ ] Múltiples niveles de membresía  
- [ ] Integración con más criptomonedas
- [ ] Sistema de referidos
- [ ] Notificaciones por email
- [ ] API REST completa para terceros

### **🎯 Mejoras Técnicas**:
- [ ] Tests automatizados
- [ ] Docker containerization
- [ ] CI/CD con GitHub Actions
- [ ] Métricas y analytics avanzadas

---

## 🤝 Contribución

¿Quieres contribuir? ¡Genial! 

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit tus cambios: `git commit -m 'Añadir nueva funcionalidad'`  
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

<div align="center">

**⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub ⭐**

Hecho con ❤️ por Paúl Damián(https://github.com/Paulcd)

</div>