from django.contrib import admin
from .models import Product, ProductImage, Coupon, SubSection, Section, Customer, OrderItem, Order, Cart, CartItem,Banner,Alert,DeviceToken, brand
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .apns import send_notification_to_all_devices
import logging

from django.utils.html import format_html

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title','price', 'calculate_discounted_price','discount_value', 'quantity', 'created_at', 'is_low_stock_indicator']
    inlines = [ProductImageInline]
    @admin.display(description='هل المخزون المتبقي قليل (اقل من 5 )')
    def is_low_stock_indicator(self, obj):
        return obj.is_low_stock()
    is_low_stock_indicator.boolean = True
    @admin.display(description='السعر بعد الخصم')
    def calculate_discounted_price(self,obj):
        return obj.calculate_discounted_price()

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active']

@admin.register(SubSection)
class SubSectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'section', 'created_at']

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'username', 'is_verified', 'government', 'address']

# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ['id', 'customer', 'created_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'total_price', 'discounted_price', 'created_at']

    def discounted_price(self, obj):
        order = obj.order  # Get the related order
        if order.coupon:  # Check if a coupon is applied
            discounted_total = order.calculate_total_price()  # Get total after discount
            order_total_before_discount = sum(item.total_price for item in order.items.all())  # Original total
            
            if order_total_before_discount > 0:
                # Apply proportional discount to this item
                discount_ratio = discounted_total / order_total_before_discount
                return round(obj.total_price * discount_ratio, 2)  # Adjust price based on discount ratio
        return obj.total_price  # If no coupon, return normal price

    discounted_price.short_description = "السعر بعد الخصم"


    
@admin.register(brand)
class brandAdmin(admin.ModelAdmin):
    list_display = ['brand_name', 'image_preview']
    def image_preview(self, obj):
        return format_html(
            '<img src="{}" style="max-height: 100px;"/>', 
            obj.brand_image.url
        ) if obj.brand_image else '-'
    image_preview.short_description = 'Preview'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['id', 'image_preview', 'section', 'subsection', 'created_at']
    list_filter = ['section', 'subsection']
    search_fields = ['section__name', 'subsection__name']
    readonly_fields = ['created_at', 'image_preview']

    def image_preview(self, obj):
        return format_html(
            '<img src="{}" style="max-height: 100px;"/>', 
            obj.image.url
        ) if obj.image else '-'
    image_preview.short_description = 'Preview'






logger = logging.getLogger(__name__)

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'is_sent', 'send_now_link']
    actions = ['send_selected_alerts']

    def get_urls(self):
        """
        Adds a custom URL for sending alerts.
        """
        urls = super().get_urls()
        custom_urls = [
            path('send/<int:alert_id>/', self.admin_site.admin_view(self.send_alert_view), name='send_alert'),
        ]
        return custom_urls + urls

    def send_now_link(self, obj):
        """
        Creates a 'Send Now' button in the admin list view.
        """
        if not obj.is_sent:
            url = reverse("admin:send_alert", args=[obj.id])
            return format_html('<a class="button" href="{}">Send Now</a>', url)
        return "Already Sent"
    send_now_link.short_description = "Send Now"

    def send_alert_view(self, request, alert_id):
        """
        Custom admin view to send a specific alert.
        """
        alert = get_object_or_404(Alert, pk=alert_id)
        if not alert.is_sent:
            send_notification_to_all_devices(alert.title, alert.message)
            alert.is_sent = True
            alert.save()
            messages.success(request, "Alert sent to all devices.")
            logger.info(f"Alert '{alert.title}' sent to all devices.")
        else:
            messages.warning(request, "Alert was already sent.")
        return redirect('admin:api_alert_changelist')  # Replace 'yourapp' with your actual app name

    def send_selected_alerts(self, request, queryset):
        """
        Admin action to send multiple selected alerts.
        """
        not_sent = queryset.filter(is_sent=False)
        for alert in not_sent:
            send_notification_to_all_devices(alert.title, alert.message)
            alert.is_sent = True
            alert.save()
            logger.info(f"Alert '{alert.title}' sent to all devices.")
        self.message_user(request, f"{not_sent.count()} alerts have been sent.")
    send_selected_alerts.short_description = "Send selected alerts now"

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['token', 'platform']
    search_fields = ['token']