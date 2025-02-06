from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import F
import uuid
from .apns import send_ios_push_notification, send_android_push_notification
import asyncio


class Section(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم القسم")
    description = models.TextField(blank=True, null=True, verbose_name="وصف القسم")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")
    image = models.ImageField(upload_to='section_images/', verbose_name="صورة القسم الفرعي",null= True , blank= True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "اقسام المنتجات"
        verbose_name_plural = "اقسام المنتجات"

class SubSection(models.Model):
    section = models.ForeignKey(Section, related_name="sub_sections", on_delete=models.CASCADE, verbose_name="اسم القسم")
    name = models.CharField(max_length=255, verbose_name="اسم القسم الفرعي")
    description = models.TextField(blank=True, null=True, verbose_name="وصف القسم الفرعي")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")
    image = models.ImageField(upload_to='subsection_images/', verbose_name="صورة القسم الفرعي",null= True , blank= True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "الاقسام الفرعية للمنتج"
        verbose_name_plural = "الاقسام الفرعية للمنتج"
        indexes = [
            models.Index(fields=['section']),
        ]

class brand(models.Model):
    brand_name = models.CharField(max_length=255 , verbose_name="اسم البراند",null=True, blank=True)
    brand_image=models.ImageField(upload_to='brandImage/',verbose_name="صورة البراند", null=True,blank=True)

    def __str__(self):
        return self.brand_name 

    class Meta:
        verbose_name = "البراند"
        verbose_name_plural = "البراند"
        indexes = [
            models.Index(fields=['brand_name']),
        ]


class Product(models.Model):
    FIXED = 'ثابت'
    PERCENTAGE = 'نسبة مئوية'
    DISCOUNT_TYPES = [
        (FIXED, 'ثابت'),
        (PERCENTAGE, 'نسبة مئوية'),
    ]
    class IsFavoured(models.TextChoices):
        YES = "نعم", "نعم"
        NO = "لا", "لا"

    sub_section = models.ForeignKey('SubSection', related_name="products", on_delete=models.CASCADE, verbose_name="اسم اقسم الفرعي")
    title = models.CharField(max_length=255, verbose_name="اسم المنتج")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر المنتج")
    quantity = models.PositiveIntegerField(verbose_name="الكمية المتوفرة")
    description = models.TextField(blank=True, null=True, verbose_name="وصف المنتج")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, blank=True, null=True, verbose_name="نوع الخصم ان وجد")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="قيمة الخصم")
    brand= models.ForeignKey('brand',related_name="brand",on_delete=models.SET_NULL,verbose_name="الى اي براند ينمتي المنتج",null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")
    is_favoured = models.CharField(
        max_length=3,
        choices=IsFavoured.choices,
        default=IsFavoured.NO,
        verbose_name="هل تريد اظهار المنتج على الصفحة الرئيسية ؟"
    )

    class Meta:
        verbose_name = " المنتجات"
        verbose_name_plural = "المنتجات "
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    (models.Q(discount_type='ثابت') & 
                     models.Q(discount_value__gte=0) &
                     models.Q(discount_value__lte=models.F('price'))) |
                    (models.Q(discount_type='نسبة مئوية') & 
                     models.Q(discount_value__range=(0, 100))) |
                    models.Q(discount_type__isnull=True)
                ),
                name='valid_discount'
            )
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.discount_type == self.FIXED and (self.discount_value < 0 or self.discount_value > self.price):
            raise ValidationError("لا يمكن أن تتجاوز قيمة الخصم سعر المنتج بالنسبة للخصومات الثابتة.")
        if self.discount_type == self.PERCENTAGE and (self.discount_value < 0 or self.discount_value > 100):
            raise ValidationError("يجب أن تتراوح قيمة الخصم بين 0 و100 للحصول على نسبة الخصومات.")

    def calculate_discounted_price(self):
        if self.discount_type == self.FIXED and self.discount_value:
            return max(self.price - self.discount_value, 0)
        elif self.discount_type == self.PERCENTAGE and self.discount_value:
            discount = (self.discount_value / 100) * self.price
            return max(self.price - discount, 0)
        return self.price

    def update_stock(self, quantity_change):
        with transaction.atomic():
            # Lock the row to prevent race conditions
            product = Product.objects.select_for_update().get(pk=self.pk)
            new_quantity = product.quantity + quantity_change
            if new_quantity < 0:
                raise ValidationError("لا يوجد مخزون كاف متاح.")
            product.quantity = new_quantity
            product.save()

    def is_low_stock(self, threshold=5):
        return self.quantity <= threshold

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE,verbose_name="المنتج")
    image = models.ImageField(upload_to='product_images/', verbose_name="صورة المنتج")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="تاريخ الانشاء")

    def __str__(self):
        return f"صور المنتج : {self.product.title}"
    
    class Meta:
        verbose_name = "صور المنتج"
        verbose_name_plural = "صور المنتج"

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="رمز الكوبون")
    discount_type = models.CharField(
        max_length=20,
        choices=Product.DISCOUNT_TYPES,  # Using your Product discount type choices
        blank=True,
        null=True
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="قيمة الخصم"
    )
    start_date = models.DateTimeField(verbose_name="تاريخ بدأ الخصم")
    end_date = models.DateTimeField(verbose_name="تاريخ انتهاء الخصم")
    is_active = models.BooleanField(default=True, verbose_name="هل تريد تفعيل رمز الخصم؟")
    # Remove the subsection field or ignore it if not needed
    # subsection = models.ForeignKey(...)  # Removed for global coupons

    def apply_coupon_to_cart(self, cart_total):
        """
        Apply the coupon to the overall cart total.
        """
        if self.discount_type == Product.FIXED:
            # Subtract the fixed discount value from the total
            discounted_total = cart_total - self.discount_value
        elif self.discount_type == Product.PERCENTAGE:
            # Calculate discount as a percentage of the total
            discount = (self.discount_value / 100) * cart_total
            discounted_total = cart_total - discount
        else:
            discounted_total = cart_total

        return max(discounted_total, 0)

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    class Meta:
        verbose_name = "كوبون الخصم"
        verbose_name_plural = "كوبونات الخصم"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]

class Customer(models.Model):
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="رقم الهاتف")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="اسم المستخدم")
    government = models.CharField(max_length=255, blank=True, null=True, verbose_name="محافظة السكن")
    address = models.TextField(verbose_name="المنطقة", blank=True, null=True)
    is_verified = models.BooleanField(default=False, verbose_name="هل تم تأكيد رقم الهاتف؟")

    def __str__(self):
        return f"{self.username or 'مستخدم عادي'} - {self.phone_number}"
    class Meta:
        verbose_name = "الزبائن"
        verbose_name_plural = "الزبائن" 
        indexes = [
            models.Index(fields=['phone_number']),  # Index on phone_number
        ]  

class Order(models.Model):
    customer = models.ForeignKey(Customer, related_name="orders", on_delete=models.CASCADE,verbose_name="الطلبات")
    coupon = models.ForeignKey(
        Coupon, 
        related_name="orders", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="الكوبون المستخدم"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="الإجمالي")

    def calculate_total_price(self):
        items_total = sum(item.total_price for item in self.items.all())
        # Apply coupon discount if available
        if self.coupon:
            return self.coupon.apply_coupon_to_cart(items_total)
        return items_total

    def __str__(self):
        return f"طلب بواسطة {self.customer.phone_number}"
    class Meta:
        verbose_name = "الطلبات "
        verbose_name_plural = "الطلبات" 
        

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE, verbose_name="الطلب")
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.CASCADE, verbose_name="المنتجات المطلوبة")
    quantity = models.PositiveIntegerField(verbose_name="الكمية االمطلوبة")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر الكلي")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")
    def save(self, *args, **kwargs):
        if not self.pk:  # Only set during creation
            self.price_at_purchase = self.product.price
            self.discount_at_purchase = self.product.discount_value
            self.total_price = self.product.calculate_discounted_price() * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"
    class Meta:
        verbose_name = "المنتجات المطلوبة"
        verbose_name_plural = "المنتجات المطلوبة" 
        indexes = [
            models.Index(fields=['order']),  # Index on order for fast item retrieval
            models.Index(fields=['product']),  # Index on product for fast item retrieval
        ]

# Cart Models

class Cart(models.Model):
    cart_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        verbose_name="الرمز الفريد للسلة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")
    applied_coupon = models.ForeignKey(
        Coupon, blank=True, null=True, on_delete=models.SET_NULL,
        verbose_name="الكوبون المطبق اذا كان هنالك"
    )

    def calculate_total(self):
        # Sum up each cart item's total price (each should include any product-specific discounts)
        items_total = sum(item.get_total_price() for item in self.items.all())
        # If there's a coupon, apply it to the overall total
        if self.applied_coupon:
            return self.applied_coupon.apply_coupon_to_cart(items_total)
        return items_total

    def __str__(self):
        return f"السلة {self.cart_id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE,verbose_name="المنتجات")
    quantity = models.PositiveIntegerField(verbose_name="الكمية")

    def get_total_price(self):
        return self.product.calculate_discounted_price() * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"
    
    class Meta:
        verbose_name = "طلبات السلة (هنا يمكنك معرفة المنتجات التي اضافها المستخدم الى سلته لكنه لم يكمل طلبه)"
        verbose_name_plural = "طلبات السلة (هنا يمكنك معرفة المنتجات التي اضافها المستخدم الى سلته لكنه لم يكمل طلبه)"




class Banner(models.Model):
    image = models.ImageField(upload_to='banner_images/', verbose_name="صورة الشعار")
    section = models.ForeignKey(Section, related_name='banners', on_delete=models.SET_NULL, null=True, blank=True,verbose_name="اسم القسم ")
    subsection = models.ForeignKey(SubSection, related_name='banners', on_delete=models.SET_NULL, null=True, blank=True,verbose_name="اسم القسم الفرعي")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="تاريخ الانشاء")

    def clean(self):
        # Ensure that exactly one of section or subsection is set
        if self.section and self.subsection:
            raise ValidationError("يمكن أن يرتبط الشعار إما بقسم أو قسم فرعي، وليس كليهما.")
        if not self.section and not self.subsection:
            raise ValidationError("يجب أن يرتبط الشعار بقسم أو قسم فرعي.")

    def __str__(self):
        if self.section:
            return f"شعار للقسم:  {self.section.name}"
        return f"شعار للقسم الفرعي {self.subsection.name}"

    class Meta:
        verbose_name = "الصور في الصفحة الرئيسية"
        verbose_name_plural = "الصور في الصفحة الرئيسية"



class DeviceToken(models.Model):
    token = models.CharField(max_length=255)
    platform = models.CharField(
        max_length=10, 
        choices=[('ios', 'iOS'), ('android', 'Android')],
        help_text="Platform of the device (iOS or Android)"
    )

    def __str__(self):
        return f"Token: {self.token}, Platform: {self.platform}"
    
class Alert(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False, help_text="هل تم ارسال هذا الاشعار الى المستخدمين؟")

    def __str__(self):
        return self.title

    async def send_notification(self):
        """
        Sends a notification to all devices registered for this alert.
        Marks the alert as 'sent' after notification is sent.
        """
        # Get all device tokens
        tokens = DeviceToken.objects.values_list('token', flat=True)

        # Loop through each device token and send the notification
        for token in tokens:
            platform = DeviceToken.objects.get(token=token).platform  # Assuming platform is stored in DeviceToken model

            if platform == 'ios':
                await send_ios_push_notification(token, self.title, self.message)  # Await the async call
            elif platform == 'android':
                await send_android_push_notification(token, self.title, self.message)

        # After sending the notification, mark the alert as sent
        self.is_sent = True
        self.save()

    def save(self, *args, **kwargs):
        """
        Overriding the save method to send notifications when a new alert is created.
        """
        super().save(*args, **kwargs)
        if not self.is_sent:  # Only send if it's not already marked as sent
            # Run the asynchronous method within the event loop
            asyncio.run(self.send_notification())  # Use asyncio to run the async method