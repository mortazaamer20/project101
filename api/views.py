from rest_framework.response import Response
from rest_framework import status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from django.db import transaction
from .models import Section, SubSection, Product, Customer, Order, OrderItem, Coupon, Cart, CartItem,DeviceToken,brand
from .serializers import SectionSerializer, SubSectionSerializer, ProductSerializer, OrderSerializer, CartSerializer,DeviceTokenSerializer,BrandSerializer
from .utility import send_whatsapp_otp
from django.core.cache import cache
from .telegram_utility import send_order_to_telegram
from rest_framework.decorators import api_view
from .apns import send_ios_push_notification, send_android_push_notification


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = brand.objects.all()
    serializer_class =BrandSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.prefetch_related('sub_section', 'brand').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['title', 'price', 'sub_section','brand',"is_favoured"]
    search_fields = ['title', 'description','brand']
    ordering_fields = ['price', 'created_at']

class SectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Section.objects.prefetch_related('sub_sections').all()
    serializer_class = SectionSerializer
    pagination_class = None

class SubSectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubSection.objects.prefetch_related('section').all()
    serializer_class = SubSectionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['name']

class AddToCartView(APIView):
    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        cart_id = request.data.get('cart_id', None)

        try:
            product = Product.objects.get(id=product_id)
            if product.quantity < quantity:
                return Response({"خطأ": "الكمية المطلوبة غير متوفرة في المخزون"}, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({"خطأ": "المنتج غير موجود"}, status=status.HTTP_404_NOT_FOUND)

        if not product_id:
            return Response({"خطأ ": "رقم المنتج مطلوب (ID)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"خطأ": "المنتج غير موجود"}, status=status.HTTP_404_NOT_FOUND)

        try:
            quantity = int(quantity)
            if quantity <= 0:
                return Response({"خطأ": "الكمية يجب ان تكون رقماً موجباً"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"خطأ": "الكمية يجب ان تكون رقماً"}, status=status.HTTP_400_BAD_REQUEST)

        if cart_id:
            try:
                cart = Cart.objects.get(cart_id=cart_id)
            except Cart.DoesNotExist:
                cart = Cart.objects.create()
        else:
            cart = Cart.objects.create()

        CartItem.objects.create(cart=cart, product=product, quantity=quantity)

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ViewCartView(APIView):
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

class ApplyCouponView(APIView):
    def post(self, request):
        cart_id = request.data.get('cart_id')
        code = request.data['coupon_code']
        
        if not cart_id or not code:
            return Response({"خطأ": "cart_id و coupon_code مطلوبات"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart = Cart.objects.get(cart_id=cart_id)
        except Cart.DoesNotExist:
            return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response({"خطأ": "رمز الكوبون خطأ او غير موجود"}, status=status.HTTP_400_BAD_REQUEST)

        if not coupon.is_valid():
            return Response({"خطأ": "انتهت صلاحية الكوبون"}, status=status.HTTP_400_BAD_REQUEST)

        # Apply the coupon to the cart
        cart.applied_coupon = coupon
        cart.save()

        # Recalculate the total after applying the coupon
        cart_total = cart.calculate_total()

        # Return updated cart data
        serializer = CartSerializer(cart)
        return Response({
            "cart": serializer.data,
            "total": cart_total
        })


class CheckoutView(APIView):
    def post(self, request):
        cart_id = request.data.get("cart_id")
        username = request.data.get("username")
        government = request.data.get("government")
        address = request.data.get("address")
        phone_number = request.data.get("phone_number")

        if not all([cart_id, username, government, address, phone_number]):
            return Response({"خطأ": "جميع الحقول و cart_id مطلوبة"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(cart_id=cart_id)
        except Cart.DoesNotExist:
            return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

        if cart.items.count() == 0:
            return Response({"خطأ": "السلة فارغة"}, status=status.HTTP_400_BAD_REQUEST)

        # Send the OTP via WhatsApp template message
        try:
            send_whatsapp_otp(phone_number)
        except Exception as e:
            return Response({"خطأ": f"فشل في ارسال الرمز :  {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "تم ارسال الرمز بنجاح، يرجى تفقد الواتساب الخاص بك",
            "checkout_data": {
                "cart_id": str(cart_id),
                "username": username,
                "government": government,
                "address": address,
                "phone_number": phone_number
            }
        }, status=status.HTTP_200_OK)

class VerifyOTPAndPurchaseView(APIView):
    def post(self, request):
        cart_id = request.data.get("cart_id")
        username = request.data.get("username")
        government = request.data.get("government")
        address = request.data.get("address")
        phone_number = request.data.get("phone_number")
        code = request.data.get("code")

        if not all([cart_id, username, government, address, phone_number, code]):
            return Response({"خطأ": "يرجى التأكد من ادخال جميع الحقول"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(cart_id=cart_id)
        except Cart.DoesNotExist:
            return Response({"خطأ": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve the stored OTP from cache
        stored_otp = cache.get(f"otp:{phone_number}")
        if not stored_otp:
            return Response({"خطأ": "الرمز غير موجود او منتهي الصلاحية"}, status=status.HTTP_400_BAD_REQUEST)

        # Compare user-provided OTP with stored one
        try:
            user_otp = int(code)
        except ValueError:
            return Response({"خطأ": "يجب ان يكون الرمز رقمأ"}, status=status.HTTP_400_BAD_REQUEST)

        if user_otp != stored_otp:
            return Response({"خطأ": "الرمز غير صحيح"}, status=status.HTTP_400_BAD_REQUEST)

        # OTP verified - proceed to create order
        with transaction.atomic():
            customer, _ = Customer.objects.get_or_create(phone_number=phone_number)
            customer.username = username
            customer.government = government
            customer.address = address
            customer.is_verified = True
            customer.save()

            order = Order.objects.create(customer=customer)

            for item in cart.items.all():
                product = item.product
                if product.quantity < item.quantity:
                    return Response({"خطأ": "لا توجد كمية كافية في المخزن"}, status=status.HTTP_400_BAD_REQUEST)
                product.update_stock(-item.quantity)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    total_price=item.get_total_price()
                )

            # Clear the cart
            cart.items.all().delete()
            cart.delete()

        
        cache.delete(f"otp:{phone_number}")
        send_order_to_telegram(customer, order)

        serializer = OrderSerializer(order)
        return Response({"الرسالة": "تم الطلب بنجاح", "الطلب": serializer.data}, status=status.HTTP_201_CREATED)
    


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
        return Response({"error": "Missing required fields (token, platform, title, message)"}, status=status.HTTP_400_BAD_REQUEST)
    
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
