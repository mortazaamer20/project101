import requests
from django.conf import settings

def send_order_to_telegram(customer, order):
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    # Build the message text
    lines = []
    lines.append("📦 *يوجد لدينا طلب جديد*")
    lines.append(f"👤 *اسم المستخدم:* {customer.username or 'Unknown'}")
    lines.append(f"📱 *رقم الهاتف:* {customer.phone_number}")
    lines.append(f"🏛 *المحافظة:* {customer.government}")
    lines.append(f"📍 *المنطقة:* {customer.address}")
    lines.append("")
    lines.append("🛒 *المنتجات المطلوبة*")
    for item in order.items.all():
        product_name = item.product.title
        quantity = item.quantity
        unit_price = item.product.calculate_discounted_price()
        line = f"- {product_name} (x{quantity}) @ ${unit_price:.2f} لكل واحد"
        lines.append(line)

    total_price = order.calculate_total_price()
    lines.append("")
    lines.append(f"💰 *السعر الكلي:* الف{total_price:.2f}")

    message_text = "\n".join(lines)

    # Telegram supports Markdown, enable it if you like
    payload = {
        'chat_id': chat_id,
        'text': message_text,
        'parse_mode': 'Markdown'
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, data=payload)
    response.raise_for_status()  # Will raise an error if request failed
