from django.urls import path
from . import views

urlpatterns = [
    path('product_list/', views.product_list), path('products/<slug:slug>/', views.product_detail),
    path('categories/', views.category_list), path('categories/<slug:slug>/', views.category_detail), path('search/', views.product_search),
    path('auth/csrf/', views.csrf_cookie), path('auth/register/', views.register), path('auth/login/', views.login_view), path('auth/logout/', views.logout_view), path('auth/me/', views.me),
    path('add_review/', views.add_review), path('update_review/<int:pk>/', views.review_detail), path('delete_review/<int:pk>/', views.review_detail), path('reviews/<int:pk>/', views.review_detail),
    path('addresses/', views.addresses), path('addresses/<int:pk>/', views.address_detail),
    path('payment-methods/', views.payment_methods), path('payment-methods/<int:pk>/', views.payment_methods), path('payment-methods/available/', views.payment_methods_available),
    path('cart/', views.cart_detail), path('cart/items/', views.cart_add), path('cart/items/<int:pk>/', views.cart_item), path('cart/clear/', views.cart_clear), path('cart/coupon/', views.cart_coupon),
    path('wishlist/', views.wishlist), path('wishlist/<int:product_id>/', views.wishlist),
    path('checkout/quote/', views.checkout_quote), path('orders/', views.orders), path('orders/create/', views.create_order), path('orders/<str:number>/', views.order_detail),
    path('orders/<str:number>/payment/initialize/', views.payment_initialize), path('orders/<str:number>/payment/retry/', views.payment_retry),
    path('payments/verify/<str:reference>/', views.payment_verify), path('payments/paystack/webhook/', views.paystack_webhook),
    path('site-settings/', views.site_settings),
]
