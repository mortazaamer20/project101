from rest_framework import serializers
from .models import Section, SubSection, Product, ProductImage, Coupon, brand, OrderItem, Order, Cart, CartItem,Banner,DeviceToken

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'price', 'quantity', 'description',
            'discount_type', 'discount_value', 'discounted_price',  
            'images', 'brand','created_at','is_favoured'
        ]

    def get_discounted_price(self, obj):
        return obj.calculate_discounted_price()

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id','product', 'quantity']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity')

        if product.quantity < quantity:
            raise serializers.ValidationError(f"لا توجد كمية كافية من {product.title}. هنالك {product.quantity} فقط متوفرة.")
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id','cart_id', 'items', 'total','applied_coupon']

    def get_total(self, obj):
        return obj.calculate_total()



class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name', 'image', 'created_at']

class SubSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubSection
        fields = ['id', 'name', 'image', 'created_at']

class SectionWithSubsectionsSerializer(SectionSerializer):
    sub_sections = SubSectionSerializer(many=True, read_only=True)

    class Meta(SectionSerializer.Meta):
        fields = SectionSerializer.Meta.fields + ['sub_sections']

class SubSectionWithProductsSerializer(SubSectionSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta(SubSectionSerializer.Meta):
        fields = SubSectionSerializer.Meta.fields + ['products']


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = ['id','code', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active', 'is_valid']

    def get_is_valid(self, obj):
        return obj.is_valid()

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'customer', 'items', 'created_at', 'total_price']

    def get_total_price(self, obj):
        return obj.calculate_total_price()



class BannerSerializer(serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'image', 'target_type', 'target_id', 'created_at']
        read_only_fields = ['created_at']

    def get_target_type(self, obj):
        if obj.section:
            return 'section'
        return 'subsection'

    def get_target_id(self, obj):
        return obj.section.id if obj.section else obj.subsection.id

    def validate(self, data):
        if data.get('section') and data.get('subsection'):
            raise serializers.ValidationError(
                "لا يمكن ربط الشعار إلا بقسم أو قسم فرعي، وليس بكليهما."
            )
        if not data.get('section') and not data.get('subsection'):
            raise serializers.ValidationError(
                "يجب أن يرتبط الشعار إما بقسم أو قسم فرعي."
            )
        return data
    

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = '__all__'

class BrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = brand
        fields = '__all__'

class BrandDetailSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True, source='brand')  
    
    class Meta:
        model = brand
        fields = '__all__'