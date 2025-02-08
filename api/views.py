from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework import status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, serializers
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from django.db import transaction
from .models import (
    Section,
    SubSection,
    Product,
    Customer,
    Order,
    OrderItem,
    Coupon,
    Cart,
    CartItem,
    DeviceToken,
    brand,
    Banner
)
from .serializers import (
    SectionSerializer,
    SubSectionSerializer,
    ProductSerializer,
    OrderSerializer,
    CartSerializer,
    DeviceTokenSerializer,
    BrandDetailSerializer,
    BrandListSerializer,
    SectionWithSubsectionsSerializer,
    SubSectionWithProductsSerializer,
    BannerSerializer
)
from .utility import send_whatsapp_otp
from django.core.cache import cache
from .telegram_utility import send_order_to_telegram
from rest_framework.decorators import api_view
from .apns import send_ios_push_notification, send_android_push_notification
from django.db import models
from django.core.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = brand.objects.prefetch_related('brand').all()
    search_fields = ['brand_name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BrandDetailSerializer
        return BrandListSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.prefetch_related('sub_section', 'brand').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['title', 'price', 'sub_section', 'brand', "is_favoured"]
    search_fields = ['title', 'description', 'brand__brand_name', 'sub_section__name']
    ordering_fields = ['price', 'created_at']
    ordering = ['title']


class SectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Section.objects.prefetch_related(
        models.Prefetch(
            'sub_sections',
            queryset=SubSection.objects.select_related('section')
        )
    ).all()

    pagination_class = None  # Disable pagination for sections
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SectionWithSubsectionsSerializer
        return SectionSerializer


class SubSectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubSection.objects.select_related('section').prefetch_related(
        models.Prefetch(
            'products',
            queryset=Product.objects.select_related('brand')
            .prefetch_related('images')
        )
    ).all()
    search_fields = ['name']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubSectionWithProductsSerializer
        return SubSectionSerializer

    def get_queryset(self):
        """
        Optionally filter subsections by section ID from URL parameter
        """
        queryset = super().get_queryset()
        section_id = self.kwargs.get('section_pk')
        if section_id:
            return queryset.filter(section_id=section_id)
        return queryset


class AddToCartView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'cart_id': openapi.Schema(type=openapi.TYPE_STRING, description='Cart ID'),
                'products': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT),
                    description='List of products with quantity'
                )
            },
            required=['cart_id', 'products']
        )
    )
    def post(self, request):
        cart_id = request.data.get('cart_id')
        products = request.data.get('products')

        if not products:
            return Response({"خطأ": "يرجى إضافة منتجات إلى السلة"}, status=status.HTTP_400_BAD_REQUEST)

        if cart_id:
            try:
                cart = Cart.objects.get(cart_id=cart_id)
            except Cart.DoesNotExist:
                return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
        else:
            cart = Cart.objects.create()

        for product_data in products:
            product_id = product_data.get('product_id')
            quantity = product_data.get('quantity', 1)

            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response({"خطأ": f"المنتج غير موجود: {product_id}"}, status=status.HTTP_404_NOT_FOUND)

            if product.quantity < quantity:
                return Response({"خطأ": f"لا توجد كمية كافية من {product.title}"}, status=status.HTTP_400_BAD_REQUEST)

            cart_item, created = CartItem.objects.update_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

        serializer = CartSerializer(cart)
        return Response({
            "cart_id": str(cart.cart_id),
            "cart": serializer.data
        }, status=status.HTTP_201_CREATED)


class ViewCartView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'cart_id',
                openapi.IN_QUERY,  # This ensures it appears in Swagger UI
                description="UUID of the cart",
                type=openapi.TYPE_STRING,
                required=True
            )
        ]
    )
    def get(self, request):
        cart_id = request.query_params.get('cart_id')
        if not cart_id:
            return Response({"خطأ": "رقم السلة مطلوبة"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cart = Cart.objects.get(cart_id=cart_id)
        except Cart.DoesNotExist:
            return Response({"خطأ": "السلة فارغة او غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class ApplyCouponView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'coupon_code': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The coupon code to retrieve."
                ),
            },
            required=['coupon_code']
        ),
        responses={
            200: openapi.Response(
                description="Coupon details retrieved successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'coupon': openapi.Schema(type=openapi.TYPE_STRING, description="The coupon code."),
                        'discount_type': openapi.Schema(type=openapi.TYPE_STRING,
                                                        description="Type of discount (percentage/fixed)."),
                        'discount_value': openapi.Schema(type=openapi.TYPE_NUMBER,
                                                         description="Discount amount or percentage."),
                    }
                )
            ),
            400: openapi.Response(description="Invalid or expired coupon."),
        }
    )
    def post(self, request):
        code = request.data.get('coupon_code')

        if not code:
            return Response(
                {"خطأ": "يجب إدخال رمز الكوبون"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response(
                "رمز الكوبون غير صحيح أو غير موجود",
                status=status.HTTP_400_BAD_REQUEST
            )

        if not coupon.is_valid():
            return Response(
                "انتهت صلاحية الكوبون",
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "coupon": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
        }, status=status.HTTP_200_OK)


# class ApplyCouponView(APIView):
#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'cart_id': openapi.Schema(
#                     type=openapi.TYPE_STRING,
#                     description="The unique identifier of the cart."
#                 ),
#                 'coupon_code': openapi.Schema(
#                     type=openapi.TYPE_STRING,
#                     description="The coupon code to apply."
#                 ),
#             },
#             required=['cart_id', 'coupon_code']
#         ),
#         responses={
#             200: openapi.Response(
#                 description="Coupon successfully applied.",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         'cart': openapi.Schema(type=openapi.TYPE_OBJECT, description="Updated cart details."),
#                         'total': openapi.Schema(type=openapi.TYPE_NUMBER, description="Total cart price after discount."),
#                     }
#                 )
#             ),
#             400: openapi.Response(description="Invalid input or expired coupon."),
#             404: openapi.Response(description="Cart not found."),
#         }
#     )
#     def post(self, request):
#         cart_id = request.data.get('cart_id')
#         code = request.data.get('coupon_code')
#
#         if not cart_id or not code:
#             return Response(
#                 {"خطأ": "cart_id و coupon_code مطلوبات"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         try:
#             cart = Cart.objects.get(cart_id=cart_id)
#         except Cart.DoesNotExist:
#             return Response(
#                 {"خطأ": "السلة غير موجودة"},
#                 status=status.HTTP_404_NOT_FOUND
#             )
#
#         try:
#             coupon = Coupon.objects.get(code=code)
#         except Coupon.DoesNotExist:
#             return Response(
#                 {"خطأ": "رمز الكوبون خطأ او غير موجود"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         if not coupon.is_valid():
#             return Response(
#                 {"خطأ": "انتهت صلاحية الكوبون"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # Apply coupon to the cart globally
#         cart.applied_coupon = coupon
#         cart.save()
#
#         serializer = CartSerializer(cart)
#         return Response({
#             "cart": serializer.data,
#             "total": cart.calculate_total()
#         })
#


# class CheckoutView(APIView):
#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 "cart_id": openapi.Schema(type=openapi.TYPE_STRING, description="Unique cart identifier."),
#                 "username": openapi.Schema(type=openapi.TYPE_STRING, description="Customer's full name."),
#                 "government": openapi.Schema(type=openapi.TYPE_STRING, description="Government or region."),
#                 "address": openapi.Schema(type=openapi.TYPE_STRING, description="Delivery address."),
#                 "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Customer's phone number."),
#             },
#             required=["cart_id", "username", "government", "address", "phone_number"]
#         ),
#         responses={
#             200: openapi.Response(
#                 description="OTP sent successfully via WhatsApp.",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING, description="Confirmation message."),
#                         "checkout_data": openapi.Schema(
#                             type=openapi.TYPE_OBJECT,
#                             description="Checkout details.",
#                             properties={
#                                 "cart_id": openapi.Schema(type=openapi.TYPE_STRING, description="Cart ID."),
#                                 "username": openapi.Schema(type=openapi.TYPE_STRING, description="Username."),
#                                 "government": openapi.Schema(type=openapi.TYPE_STRING, description="Government."),
#                                 "address": openapi.Schema(type=openapi.TYPE_STRING, description="Address."),
#                                 "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number."),
#                             }
#                         ),
#                     }
#                 )
#             ),
#             400: openapi.Response(description="Missing required fields or empty cart."),
#             404: openapi.Response(description="Cart not found."),
#             500: openapi.Response(description="WhatsApp OTP sending failed."),
#         }
#     )
#     def post(self, request):
#         cart_id = request.data.get("cart_id")
#         username = request.data.get("username")
#         government = request.data.get("government")
#         address = request.data.get("address")
#         phone_number = request.data.get("phone_number")
#
#         if not all([cart_id, username, government, address, phone_number]):
#             return Response({"خطأ": "جميع الحقول و cart_id مطلوبة"}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             cart = Cart.objects.get(cart_id=cart_id)
#         except Cart.DoesNotExist:
#             return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)
#
#         if cart.items.count() == 0:
#             return Response({"خطأ": "السلة فارغة"}, status=status.HTTP_400_BAD_REQUEST)
#
#
#         try:
#             send_whatsapp_otp(phone_number)
#         except Exception as e:
#             return Response({"خطأ": f"فشل في ارسال الرمز :  {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#         return Response({
#             "message": "تم ارسال الرمز بنجاح، يرجى تفقد الواتساب الخاص بك",
#             "checkout_data": {
#                 "cart_id": str(cart_id),
#                 "username": username,
#                 "government": government,
#                 "address": address,
#                 "phone_number": phone_number
#             }
#         }, status=status.HTTP_200_OK)

# class CheckoutView(APIView):
#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 "cart_id": openapi.Schema(type=openapi.TYPE_STRING, description="Unique cart identifier."),
#                 "username": openapi.Schema(type=openapi.TYPE_STRING, description="Customer's full name."),
#                 "government": openapi.Schema(type=openapi.TYPE_STRING, description="Government or region."),
#                 "address": openapi.Schema(type=openapi.TYPE_STRING, description="Delivery address."),
#                 "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Customer's phone number."),
#                 "coupon_code": openapi.Schema(type=openapi.TYPE_STRING, description="Discount coupon code (optional)."),
#             },
#             required=["cart_id", "username", "government", "address", "phone_number"]
#         ),
#         responses={
#             200: openapi.Response(
#                 description="OTP sent successfully via WhatsApp.",
#                 schema=openapi.Schema(
#                     type=openapi.TYPE_OBJECT,
#                     properties={
#                         "message": openapi.Schema(type=openapi.TYPE_STRING, description="Confirmation message."),
#                         "checkout_data": openapi.Schema(
#                             type=openapi.TYPE_OBJECT,
#                             description="Checkout details.",
#                             properties={
#                                 "cart_id": openapi.Schema(type=openapi.TYPE_STRING, description="Cart ID."),
#                                 "username": openapi.Schema(type=openapi.TYPE_STRING, description="Username."),
#                                 "government": openapi.Schema(type=openapi.TYPE_STRING, description="Government."),
#                                 "address": openapi.Schema(type=openapi.TYPE_STRING, description="Address."),
#                                 "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Phone number."),
#                                 "total_price": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total price after discount."),
#                                 "coupon": openapi.Schema(type=openapi.TYPE_OBJECT, description="Applied coupon details."),
#                             }
#                         ),
#                     }
#                 )
#             ),
#             400: openapi.Response(description="Missing required fields or empty cart."),
#             404: openapi.Response(description="Cart not found."),
#             500: openapi.Response(description="WhatsApp OTP sending failed."),
#         }
#     )
#     def post(self, request):
#         # استخراج القيم والتأكد من أنها ليست None
#         cart_id = request.data.get("cart_id", "").strip()
#         username = request.data.get("username", "").strip()
#         government = request.data.get("government", "").strip()
#         address = request.data.get("address", "").strip()
#         phone_number = request.data.get("phone_number", "").strip()
#         coupon_code = request.data.get("coupon_code", "").strip()

#         # التحقق من القيم الفارغة
#         missing_fields = []
#         if not cart_id:
#             missing_fields.append("cart_id")
#         if not username:
#             missing_fields.append("username")
#         if not government:
#             missing_fields.append("government")
#         if not address:
#             missing_fields.append("address")
#         if not phone_number:
#             missing_fields.append("phone_number")

#         if missing_fields:
#             return Response(
#                 {"خطأ": f"يرجى التأكد من إدخال جميع الحقول المطلوبة: {', '.join(missing_fields)}"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # البحث عن السلة والتحقق من وجودها
#         try:
#             cart = Cart.objects.get(cart_id=cart_id)
#         except Cart.DoesNotExist:
#             return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

#         if cart.items.count() == 0:
#             return Response({"خطأ": "السلة فارغة"}, status=status.HTTP_400_BAD_REQUEST)

#         applied_coupon = None
#         discount_amount = 0

#         # التحقق من الكوبون وتطبيقه
#         if coupon_code:
#             try:
#                 coupon = Coupon.objects.get(code=coupon_code)

#                 # التحقق من صلاحية الكوبون
#                 if not coupon.is_valid():
#                     return Response({"خطأ": "انتهت صلاحية الكوبون"}, status=status.HTTP_400_BAD_REQUEST)

#                 # تطبيق الكوبون على السلة
#                 cart.applied_coupon = coupon
#                 cart.save()

#                 applied_coupon = {
#                     "coupon_code": coupon.code,
#                     "discount_type": coupon.discount_type,
#                     "discount_value": coupon.discount_value,
#                 }

#                 # حساب الخصم
#                 if coupon.discount_type == "percentage":
#                     discount_amount = (cart.calculate_total() * coupon.discount_value) / 100
#                 elif coupon.discount_type == "fixed":
#                     discount_amount = coupon.discount_value

#             except Coupon.DoesNotExist:
#                 return Response({"خطأ": "رمز الكوبون غير صحيح أو غير موجود"}, status=status.HTTP_400_BAD_REQUEST)

#         # حساب السعر النهائي بعد الخصم، مع التأكد من عدم تجاوز السعر الأصلي
#         total_price_after_discount = max(0, cart.calculate_total() - discount_amount)

#         # إرسال OTP عبر الواتساب
#         try:
#             send_whatsapp_otp(phone_number)
#         except Exception as e:
#             return Response({"خطأ": f"فشل في ارسال الرمز : {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         return Response({
#             "message": "تم ارسال الرمز بنجاح، يرجى تفقد الواتساب الخاص بك",
#             "checkout_data": {
#                 "cart_id": str(cart_id),
#                 "username": username,
#                 "government": government,
#                 "address": address,
#                 "phone_number": phone_number,
#                 "total_price": total_price_after_discount,
#                 "coupon": applied_coupon,
#             }
#         }, status=status.HTTP_200_OK)



class CheckoutSerializer(serializers.Serializer):
    cart_id = serializers.CharField()
    username = serializers.CharField()
    government = serializers.CharField()
    address = serializers.CharField()
    phone_number = serializers.CharField()
    coupon_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                
                try:
                    cart = Cart.objects.select_for_update().get(cart_id=data["cart_id"])
                except Cart.DoesNotExist:
                    return Response(
                        {"خطأ": "السلة غير موجودة"},
                        status=status.HTTP_404_NOT_FOUND
                    )

               
                if cart.items.count() == 0:
                    return Response(
                        {"خطأ": "السلة فارغة"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                coupon_code = data.get("coupon_code")
                if coupon_code: 
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                    except Coupon.DoesNotExist:
                        return Response(
                            {"خطأ": "رمز الكوبون خطأ او غير موجود"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    if not coupon.is_valid():
                        return Response(
                            {"خطأ": "انتهت صلاحية الكوبون"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    cart.applied_coupon = coupon
                    cart.save()
                else:
                    cart.applied_coupon = None
                    cart.save()

                
                try:
                    send_whatsapp_otp(data["phone_number"])
                except Exception as e:
                    raise Exception("فشل في ارسال الرمز : " + str(e))

                
                total_after_discount = cart.calculate_total()

        except Exception as e:
            
            return Response(
                {"خطأ": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "تم ارسال الرمز بنجاح، يرجى تفقد الواتساب الخاص بك",
            "checkout_data": {
                "cart_id": data["cart_id"],
                "username": data["username"],
                "government": data["government"],
                "address": data["address"],
                "phone_number": data["phone_number"],
                "coupon_code": data["coupon_code"],
                "total": total_after_discount,
            }
        }, status=status.HTTP_200_OK)


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BannerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['section', 'subsection']
    ordering_fields = ['created_at', 'name']
    ordering = ['created_at']

    def get_queryset(self):
        return Banner.objects.select_related('section', 'subsection').order_by('created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VerifyOTPSerializer(serializers.Serializer):
    cart_id = serializers.CharField()
    username = serializers.CharField()
    government = serializers.CharField()
    address = serializers.CharField()
    phone_number = serializers.CharField()
    code = serializers.CharField()  # OTP code

class VerifyOTPAndPurchaseView(APIView):

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "cart_id": openapi.Schema(type=openapi.TYPE_STRING, description="Cart ID."),
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="Customer's name."),
                "government": openapi.Schema(type=openapi.TYPE_STRING, description="Government/region."),
                "address": openapi.Schema(type=openapi.TYPE_STRING, description="Delivery address."),
                "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="Customer phone."),
                "code": openapi.Schema(type=openapi.TYPE_STRING, description="OTP code received on WhatsApp."),
            },
            required=["cart_id", "username", "government", "address", "phone_number", "code"]
        ),
        responses={
            201: openapi.Response(description="Order successfully created."),
            400: openapi.Response(description="Bad request (missing fields, invalid OTP, stock issues)."),
            404: openapi.Response(description="Cart not found."),
            500: openapi.Response(description="Internal server error."),
        }
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        phone_number = data["phone_number"]

        
        stored_otp = cache.get(f"otp:{phone_number}")
        if not stored_otp:
            return Response({"خطأ": "الرمز غير موجود او منتهي الصلاحية"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_otp = int(data["code"])
        except ValueError:
            return Response({"خطأ": "يجب ان يكون الرمز رقمأ"}, status=status.HTTP_400_BAD_REQUEST)

        if user_otp != stored_otp:
            return Response({"خطأ": "الرمز غير صحيح"}, status=status.HTTP_400_BAD_REQUEST)

        
        try:
            with transaction.atomic():
                
                try:
                    cart = Cart.objects.select_for_update().get(cart_id=data["cart_id"])
                except Cart.DoesNotExist:
                    return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

                
                if cart.items.count() == 0:
                    return Response({"خطأ": "السلة فارغة"}, status=status.HTTP_400_BAD_REQUEST)

               
                customer, created = Customer.objects.get_or_create(phone_number=phone_number)
                if created or not customer.username:  
                    customer.username = data["username"]
                    customer.government = data["government"]
                    customer.address = data["address"]
                    customer.is_verified = True
                    customer.save()

                
                order = Order.objects.create(
                    customer=customer,
                    coupon=getattr(cart, 'applied_coupon', None)  
                )

                order_items = []
                
                for item in cart.items.select_related("product"):
                    product = item.product
                    if product.quantity < item.quantity:
                        raise Exception(f"لا توجد كمية كافية من {product.title}.")
                    
                    product.update_stock(-item.quantity)
                    order_items.append(OrderItem(
                        order=order,
                        product=product,
                        quantity=item.quantity,
                        total_price=item.get_total_price()  
                    ))

                OrderItem.objects.bulk_create(order_items)

                order.total = order.calculate_total_price()
                order.save()

                
                cart.items.all().delete()
                cart.delete()
        except Exception as e:
           
            return Response({"خطأ": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        cache.delete(f"otp:{phone_number}")

        
        try:
            send_order_to_telegram(customer, order)
        except Exception as e:
            print(f"⚠️ Telegram notification failed: {e}")

        order_data = OrderSerializer(order).data
        return Response({"الرسالة": "تم الطلب بنجاح", "الطلب": order_data}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def save_device_token(request):
    """
    Endpoint to save the device token and platform.
    """
    # Create an instance of the serializer with the incoming data
    serializer = DeviceTokenSerializer(data=request.data)

    # Validate the data using the serializer
    if serializer.is_valid():
        # If valid, save the device token or update existing token
        token = serializer.validated_data['token']
        platform = serializer.validated_data['platform']

        # Update or create the device token in the database
        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={'platform': platform}
        )

        # Return success response
        return Response({"message": "Device token saved successfully."}, status=status.HTTP_201_CREATED)
    else:
        # If validation fails, return an error response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def send_notification(request):
    """
    Endpoint to send a notification to a device (iOS or Android).
    """
    # Extract data from the request
    token = request.data.get('token')
    platform = request.data.get('platform')
    title = request.data.get('title')
    message = request.data.get('message')

    if not all([token, platform, title, message]):
        return Response({"error": "Missing required fields (token, platform, title, message)"},
                        status=status.HTTP_400_BAD_REQUEST)

    # Validate platform
    if platform not in ['ios', 'android']:
        return Response({"error": "Invalid platform. Must be 'ios' or 'android'."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Send the notification based on the platform
        if platform == 'ios':
            success = send_ios_push_notification(token, title, message)
        elif platform == 'android':
            success = send_android_push_notification(token, title, message)

        if success:
            return Response({"message": "Notification sent successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to send notification"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
