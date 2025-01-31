from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers  

from .views import (
    SectionViewSet,
    SubSectionViewSet,
    ProductViewSet,
    AddToCartView,
    ViewCartView,
    ApplyCouponView,
    CheckoutView,
    VerifyOTPAndPurchaseView,
    save_device_token,
    BrandViewSet,
    send_notification,
    BannerViewSet
)

router = DefaultRouter()
router.register('sections', SectionViewSet, basename='section')

subsections_router = routers.NestedSimpleRouter(
    router, 
    r'sections', 
    lookup='section'
)
subsections_router.register(
    r'subsections', 
    SubSectionViewSet, 
    basename='section-subsections'
)

router.register('products', ProductViewSet, basename='product')
router.register('brands', BrandViewSet, basename="brand")
router.register(r'banners', BannerViewSet, basename='banner')

urlpatterns = [
    path('', include(router.urls)),

    # Cart & Checkout endpoints:
    path('cart/add/', AddToCartView.as_view(), name='cart-add'),
    path('cart/view/', ViewCartView.as_view(), name='cart-view'),
    path('cart/apply-coupon/', ApplyCouponView.as_view(), name='cart-apply-coupon'),
    path('cart/checkout/', CheckoutView.as_view(), name='cart-checkout'),
    path('cart/verify-otp/', VerifyOTPAndPurchaseView.as_view(), name='cart-verify-otp'),
    path('cart/save-device-token/', save_device_token, name='save_device_token'),
    path('cart/send-notification/', send_notification, name='send_notification'),
    path('', include(subsections_router.urls)),
]
