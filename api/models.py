from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import F
import uuid

class Section(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم القسم")
    description = models.TextField(blank=True, null=True, verbose_name="وصف القسم")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")

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

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "الاقسام الفرعية للمنتج"
        verbose_name_plural = "الاقسام الفرعية للمنتج"

class Product(models.Model):
    FIXED = 'ثابت'
    PERCENTAGE = 'نسبة مئوية'
    DISCOUNT_TYPES = [
        (FIXED, 'ثابت'),
        (PERCENTAGE, 'نسبة مئوية'),
    ]

    sub_section = models.ForeignKey('SubSection', related_name="products", on_delete=models.CASCADE, verbose_name="اسم اقسم الفرعي")
    title = models.CharField(max_length=255, verbose_name="اسم المنتج")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر المنتج")
    quantity = models.PositiveIntegerField(verbose_name="الكمية المتوفرة")
    description = models.TextField(blank=True, null=True, verbose_name="وصف المنتج")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, blank=True, null=True, verbose_name="نوع الخصم ان وجد")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="قيمة الخصم")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الانشاء")

    class Meta:
        verbose_name = "المنتجات"
        verbose_name_plural = "المنتجات"
        ordering = ['created_at']

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
        if self.quantity + quantity_change < 0:
            raise ValidationError("لا يوجد مخزون كاف متاح.")
        self.quantity = F('quantity') + quantity_change
        self.save(update_fields=['quantity'])

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
        choices=Product.DISCOUNT_TYPES,
        blank=True,
        null=True
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قيمة الخصم")
    start_date = models.DateTimeField(verbose_name="تاريخ بدأ الخصم")
    end_date = models.DateTimeField(verbose_name="تاريخ انتهاء الخصم")
    is_active = models.BooleanField(default=True, verbose_name="هل تريد تفعيل رمز الخصم؟")
    subsection = models.ForeignKey(SubSection, related_name='coupons', null=True, blank=True, on_delete=models.CASCADE, verbose_name="اسم القسم الفرعي")

    def __str__(self):
        return self.code

    def apply_coupon(self, product):
        if not self.is_valid():
            return 0
        if self.subsection and product.sub_section != self.subsection:
            return 0
        return self.calculate_discount(product.calculate_discounted_price())

    def calculate_discount(self, price):
        if self.discount_type == Product.PERCENTAGE:
            return (self.discount_value / 100) * price
        elif self.discount_type == Product.FIXED:
            return self.discount_value
        return 0

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    class Meta:
        verbose_name = "كوبونات الخصم"
        verbose_name_plural = "كوبونات الخصم"

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

class Order(models.Model):
    customer = models.ForeignKey(Customer, related_name="orders", on_delete=models.CASCADE,verbose_name="الطلبات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")

    def calculate_total_price(self):
        return sum(item.total_price for item in self.items.all())

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

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.product.calculate_discounted_price()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"
    class Meta:
        verbose_name = "المنتجات المطلوبة"
        verbose_name_plural = "المنتجات المطلوبة" 

# Cart Models
class Cart(models.Model):
    cart_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,verbose_name="الرمز الفريد للسلة")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="تاريخ الانشاء")
    applied_coupon = models.ForeignKey(Coupon, blank=True, null=True, on_delete=models.SET_NULL,verbose_name="الكوبون المطبق اذا كان هنالك")

    def calculate_total(self):
        items_total = sum(i.get_total_price() for i in self.items.all())
        if self.applied_coupon:
            discount_amount = 0
            for item in self.items.all():
                product_discount = self.applied_coupon.apply_coupon(item.product)
                discount_amount += product_discount * item.quantity
            final_total = items_total - discount_amount
            return max(final_total, 0)
        return items_total

    def __str__(self):
        return f"السلة {self.cart_id}"
    class Meta:
        verbose_name = "السلة"
        verbose_name_plural = "السلة"

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
    token = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token
    
class Alert(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False, help_text="هل تم ارسال هذا الاشعار الى المستخدمين؟")

    def __str__(self):
        return self.title