import hashlib
import hmac
import json
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Address, Cart, CartItem, Category, Coupon, Order, OrderItem, PaymentTransaction, Product, ProductVariant, Review, SavedPaymentMethod, ShippingRate, SiteSetting, WishlistItem
from .serializers import (AddressSerializer, CartItemSerializer, CartSerializer, CategoryDetailSerializer, CategoryListSerializer, OrderSerializer, ProductDetailSerializer, ProductListSerializer, RegistrationSerializer, ReviewSerializer, SavedPaymentMethodSerializer, SiteSettingSerializer, UserSerializer, WishlistSerializer)


def cart_for(user): return Cart.objects.get_or_create(user=user)[0]
def error(message, code=status.HTTP_400_BAD_REQUEST): return Response({'detail': message}, status=code)


@ensure_csrf_cookie
def csrf_cookie(request):
    """Set the CSRF cookie for the separately served static storefront."""
    return JsonResponse({'detail': 'CSRF cookie set.'})


@api_view(['GET'])
@permission_classes([AllowAny])
def site_settings(request):
    return Response(SiteSettingSerializer(SiteSetting.get_solo()).data)


def get_available_payment_methods():
    methods = [{'id': Order.PAYSTACK, 'name': 'Card / Bank', 'description': 'Pay securely with your card or bank account via Paystack.', 'icon': 'card'}]
    if settings.ALLOW_CASH_ON_DELIVERY:
        methods.append({'id': Order.COD, 'name': 'Cash on Delivery', 'description': 'Pay with cash when your order is delivered.', 'icon': 'cash'})
    methods.append({'id': Order.BANK_TRANSFER, 'name': 'Bank Transfer', 'description': 'Transfer to our account and upload proof of payment.', 'icon': 'bank'})
    return methods


def validate_payment_method(method):
    if method == Order.PAYSTACK and not settings.PAYSTACK_SECRET_KEY:
        raise ValueError('Secure card and bank payments are not configured yet. Please contact the store administrator.')
    if method == Order.COD and not settings.ALLOW_CASH_ON_DELIVERY:
        raise ValueError('Cash on delivery is not available.')
    if method not in [choice[0] for choice in Order.PAYMENT_METHOD_CHOICES]:
        raise ValueError('Invalid payment method selected.')

@api_view(['GET'])
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-featured', '-created_at')
    query = request.query_params.get('query')
    if query: products = products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query))
    if category := request.query_params.get('category'): products = products.filter(category__slug=category)
    if request.query_params.get('in_stock') == 'true': products = products.filter(Q(stock_quantity__gt=0) | Q(variants__stock_quantity__gt=0, variants__is_active=True)).distinct()
    if min_price := request.query_params.get('min_price'): products = products.filter(price__gte=min_price)
    if max_price := request.query_params.get('max_price'): products = products.filter(price__lte=max_price)
    ordering = request.query_params.get('ordering', '-featured,-created_at')
    allowed = {'price', '-price', 'name', '-name', 'created_at', '-created_at', 'featured', '-featured'}
    products = products.order_by(*[field for field in ordering.split(',') if field in allowed])
    return Response(ProductListSerializer(products, many=True, context={'request': request}).data)

@api_view(['GET'])
def product_detail(request, slug): return Response(ProductDetailSerializer(get_object_or_404(Product, slug=slug, is_active=True), context={'request': request}).data)
@api_view(['GET'])
def category_list(request): return Response(CategoryListSerializer(Category.objects.all(), many=True, context={'request': request}).data)
@api_view(['GET'])
def category_detail(request, slug): return Response(CategoryDetailSerializer(get_object_or_404(Category, slug=slug), context={'request': request}).data)
@api_view(['GET'])
def product_search(request): return product_list(request._request)

@api_view(['POST'])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def login_view(request):
    identifier = request.data.get('email', '').strip()
    if not identifier:
        return error('Email is required.')
    User = get_user_model()
    user = User.objects.filter(email__iexact=identifier, is_active=True).first()
    if not user: return error('No active account exists for this email.', status.HTTP_401_UNAUTHORIZED)
    login(request, user)
    return Response(UserSerializer(user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request): logout(request); return Response(status=status.HTTP_204_NO_CONTENT)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'PATCH':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True); serializer.save()
    return Response(UserSerializer(request.user).data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_review(request):
    serializer = ReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    product = get_object_or_404(Product, pk=request.data.get('product_id'), is_active=True)
    review, created = Review.objects.update_or_create(product=product, user=request.user, defaults=serializer.validated_data)
    data = ReviewSerializer(review).data
    data['was_created'] = created
    return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
def owned_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if review.user != request.user and not request.user.is_staff: return None
    return review
@api_view(['PATCH', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def review_detail(request, pk):
    review = owned_review(request, pk)
    if not review: return error('You do not have permission to change this review.', status.HTTP_403_FORBIDDEN)
    if request.method == 'DELETE': review.delete(); return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = ReviewSerializer(review, data=request.data, partial=True); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def addresses(request):
    if request.method == 'POST':
        serializer = AddressSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        first_address = not request.user.addresses.exists()
        address = serializer.save(user=request.user, is_default_shipping=serializer.validated_data.get('is_default_shipping', first_address), is_default_billing=serializer.validated_data.get('is_default_billing', first_address))
        if address.is_default_shipping: Address.objects.filter(user=request.user).exclude(pk=address.pk).update(is_default_shipping=False)
        if address.is_default_billing: Address.objects.filter(user=request.user).exclude(pk=address.pk).update(is_default_billing=False)
        return Response(AddressSerializer(address).data, status=201)
    return Response(AddressSerializer(request.user.addresses.all(), many=True).data)

@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def address_detail(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'DELETE': address.delete(); return Response(status=204)
    if request.method == 'PATCH':
        serializer = AddressSerializer(address, data=request.data, partial=True); serializer.is_valid(raise_exception=True); address = serializer.save()
    return Response(AddressSerializer(address).data)

@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def payment_methods(request, pk=None):
    if request.method == 'GET': return Response(SavedPaymentMethodSerializer(request.user.saved_payment_methods.all(), many=True).data)
    method = get_object_or_404(SavedPaymentMethod, pk=pk, user=request.user)
    method.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_detail(request): return Response(CartSerializer(cart_for(request.user)).data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_add(request):
    serializer = CartItemSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    product, variant, quantity = serializer.validated_data['product'], serializer.validated_data.get('variant'), serializer.validated_data['quantity']
    if variant and variant.product_id != product.id: return error('Variant does not belong to this product.')
    stock, price = (variant.stock_quantity, variant.current_price) if variant else (product.stock_quantity, product.current_price)
    cart = cart_for(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant, defaults={'quantity': 0, 'unit_price': price})
    if item.quantity + quantity > stock: return error('Requested quantity exceeds available stock.')
    item.quantity += quantity; item.unit_price = price; item.save()
    return Response(CartSerializer(cart).data, status=201 if created else 200)
@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def cart_item(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    if request.method == 'DELETE': item.delete(); return Response(status=204)
    quantity = int(request.data.get('quantity', 0))
    if quantity < 1 or quantity > item.available_stock: return error('Quantity must be within available stock.')
    item.quantity = quantity; item.save(); return Response(CartSerializer(item.cart).data)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cart_clear(request): cart_for(request.user).items.all().delete(); return Response(status=204)
@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def cart_coupon(request):
    cart = cart_for(request.user)
    if request.method == 'DELETE': cart.coupon = None; cart.save(); return Response(CartSerializer(cart).data)
    coupon = get_object_or_404(Coupon, code=request.data.get('code', '').upper())
    try: coupon.discount_for(cart.subtotal)
    except ValueError as exc: return error(str(exc))
    cart.coupon = coupon; cart.save(); return Response(CartSerializer(cart).data)

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def wishlist(request, product_id=None):
    if request.method == 'GET': return Response(WishlistSerializer(request.user.wishlist_items.select_related('product'), many=True).data)
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if request.method == 'DELETE': WishlistItem.objects.filter(user=request.user, product=product).delete(); return Response(status=204)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    return Response(WishlistSerializer(item).data, status=201 if created else 200)

def quote(user, payload):
    cart = cart_for(user)
    if not cart.items.exists(): raise ValueError('Your cart is empty.')
    try:
        shipping = get_object_or_404(Address, pk=payload.get('shipping_address_id'), user=user)
        billing = get_object_or_404(Address, pk=payload.get('billing_address_id', shipping.id), user=user)
    except Http404:
        raise ValueError('Invalid shipping or billing address selected.')
    rate = ShippingRate.objects.filter(is_active=True).filter(Q(state__iexact=shipping.state) | Q(state='')).order_by('-state').first()
    if not rate: raise ValueError('No shipping rate is configured for this destination.')
    subtotal = cart.subtotal
    discount = cart.coupon.discount_for(subtotal) if cart.coupon else Decimal('0.00')
    return cart, shipping, billing, subtotal, rate.amount, discount
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout_quote(request):
    try:
        _, _, _, subtotal, shipping, discount = quote(request.user, request.data)
        return Response({'subtotal': subtotal, 'shipping_fee': shipping, 'discount': discount, 'total': subtotal + shipping - discount})
    except (ValueError, Address.DoesNotExist) as exc: return error(str(exc))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    try:
        with transaction.atomic():
            cart, shipping, billing, subtotal, shipping_fee, discount = quote(request.user, request.data)
            items = list(cart.items.select_for_update().select_related('product'))
            for item in items:
                if item.quantity > item.available_stock: raise ValueError(f'{item.product.name} no longer has enough stock.')
            method = request.data.get('payment_method', Order.PAYSTACK)
            validate_payment_method(method)
            order = Order.objects.create(user=request.user, shipping_address=shipping.as_snapshot(), billing_address=billing.as_snapshot(), subtotal=subtotal, shipping_fee=shipping_fee, discount=discount, total=subtotal + shipping_fee - discount, coupon_code=cart.coupon.code if cart.coupon else '', payment_method=method, payment_status=Order.PENDING, fulfillment_status=Order.NEW, customer_note=request.data.get('customer_note', ''))
            for item in items:
                subject = item.variant or item.product
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    product_name=item.product.name,
                    sku=subject.sku or f'AGB-PRODUCT-{item.product_id}',
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    line_total=item.line_total,
                )
            if cart.coupon: Coupon.objects.filter(pk=cart.coupon_id).update(used_count=cart.coupon.used_count + 1)
            cart.items.all().delete(); cart.coupon = None; cart.save()
            if method == Order.COD:
                order.payment_status = Order.PENDING
                order.save(update_fields=['payment_status', 'updated_at'])
        return Response(OrderSerializer(order).data, status=201)
    except (ValueError, Address.DoesNotExist) as exc: return error(str(exc))
    except Exception as exc: return error('Something went wrong while placing your order. Please try again.', status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_verify(request, reference):
    payment = get_object_or_404(PaymentTransaction.objects.select_related('order'), reference=reference, order__user=request.user)
    if payment.status == 'success':
        return Response({'status': 'success', 'order': OrderSerializer(payment.order).data})
    if payment.status == 'failed':
        return Response({'status': 'failed', 'order': OrderSerializer(payment.order).data})
    if not settings.PAYSTACK_SECRET_KEY:
        return Response({'status': 'pending', 'detail': 'Payment provider not configured. Cannot verify.'})
    try:
        remote_request = Request(f'https://api.paystack.co/transaction/verify/{reference}', headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}, method='GET')
        with urlopen(remote_request, timeout=15) as remote_response: result = json.loads(remote_response.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        return error(f'Unable to verify payment: {exc}')
    data = result.get('data', {})
    if not result.get('status'): return error(result.get('message', 'Unable to verify payment.'))
    with transaction.atomic():
        payment = PaymentTransaction.objects.select_for_update().select_related('order').get(reference=reference)
        if payment.status == 'success': return Response({'status': 'success', 'order': OrderSerializer(payment.order).data})
        if data.get('status') == 'success':
            payment.status = 'success'; payment.provider_response = data; payment.save(update_fields=['status', 'provider_response', 'updated_at'])
            order = payment.order
            for item in order.items.select_related('product', 'variant'):
                subject = item.variant or item.product
                if not subject or subject.stock_quantity < item.quantity: return error('Stock unavailable.', 409)
                subject.stock_quantity -= item.quantity; subject.save(update_fields=['stock_quantity'])
            authorization = data.get('authorization') or {}
            if authorization.get('reusable') and authorization.get('authorization_code') and authorization.get('last4'):
                SavedPaymentMethod.objects.update_or_create(
                    user=order.user, provider='paystack', signature=authorization.get('signature') or authorization['authorization_code'],
                    defaults={'authorization_code': authorization['authorization_code'], 'brand': authorization.get('brand') or authorization.get('card_type', ''), 'bank': authorization.get('bank', ''), 'last4': authorization['last4'], 'exp_month': authorization.get('exp_month'), 'exp_year': authorization.get('exp_year')},
                )
            order.payment_status = Order.PAID; order.save(update_fields=['payment_status', 'updated_at'])
            return Response({'status': 'success', 'order': OrderSerializer(order).data})
        elif data.get('status') == 'failed':
            payment.status = 'failed'; payment.provider_response = data; payment.save(update_fields=['status', 'provider_response', 'updated_at'])
            return Response({'status': 'failed', 'order': OrderSerializer(payment.order).data})
        return Response({'status': 'pending', 'order': OrderSerializer(payment.order).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_retry(request, number):
    order = get_object_or_404(Order, number=number, user=request.user)
    if order.payment_status == Order.PAID: return error('This order is already paid.')
    if order.payment_status == Order.FAILED:
        order.payment_status = Order.PENDING; order.save(update_fields=['payment_status', 'updated_at'])
    return payment_initialize(request._request, number)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_methods_available(request):
    return Response({'methods': get_available_payment_methods()})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def orders(request): return Response(OrderSerializer(request.user.orders.prefetch_related('items', 'payments'), many=True).data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, number):
    order = get_object_or_404(Order.objects.prefetch_related('items', 'payments'), number=number)
    if order.user != request.user and not request.user.is_staff: return error('You do not have permission to view this order.', 403)
    return Response(OrderSerializer(order).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_initialize(request, number):
    order = get_object_or_404(Order, number=number, user=request.user)
    if order.payment_status == Order.PAID: return error('This order is already paid.')
    if order.payment_status == Order.FAILED: return error('This order payment failed. Use the retry endpoint to try again.')
    if order.payment_method != Order.PAYSTACK: return error('Payment can only be initialized for card or bank payment orders.')
    payment, _ = PaymentTransaction.objects.get_or_create(order=order, reference=f'AGB-{uuid4().hex[:18].upper()}', defaults={'amount': order.total, 'provider': Order.PAYSTACK})
    if not settings.PAYSTACK_SECRET_KEY:
        return Response({'reference': payment.reference, 'sandbox': True, 'authorization_url': None, 'detail': 'Paystack is not configured. Use webhook tests only.'})
    saved_method_id = request.data.get('saved_payment_method_id')
    saved_method = get_object_or_404(SavedPaymentMethod, pk=saved_method_id, user=request.user) if saved_method_id else None
    payload = {'email': request.user.email, 'amount': str(int(order.total * 100)), 'reference': payment.reference, 'currency': 'NGN', 'metadata': json.dumps({'order_number': order.number})}
    endpoint = 'https://api.paystack.co/transaction/initialize'
    if saved_method:
        endpoint = 'https://api.paystack.co/transaction/charge_authorization'
        payload['authorization_code'] = saved_method.authorization_code
    else:
        payload['channels'] = ['card', 'bank']
    if settings.PAYSTACK_CALLBACK_URL: payload['callback_url'] = settings.PAYSTACK_CALLBACK_URL
    try:
        remote_request = Request(endpoint, data=json.dumps(payload).encode(), headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}', 'Content-Type': 'application/json'}, method='POST')
        with urlopen(remote_request, timeout=15) as remote_response: result = json.loads(remote_response.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        return error(f'Unable to start secure card payment: {exc}')
    data = result.get('data', {})
    if not result.get('status'): return error(result.get('message', 'Unable to start secure card payment.'))
    payment.provider_response = data; payment.save(update_fields=['provider_response', 'updated_at'])
    return Response({'reference': payment.reference, 'sandbox': False, 'authorization_url': data.get('authorization_url') or data.get('open_url'), 'payment_pending_confirmation': True})
@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    signature = request.headers.get('x-paystack-signature', '')
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), request.body, hashlib.sha512).hexdigest()
    if not settings.PAYSTACK_SECRET_KEY or not hmac.compare_digest(signature, expected): return error('Invalid webhook signature.', 403)
    event = request.data
    if event.get('event') != 'charge.success': return Response(status=200)
    reference = event.get('data', {}).get('reference')
    with transaction.atomic():
        payment = get_object_or_404(PaymentTransaction.objects.select_for_update().select_related('order'), reference=reference)
        if payment.status == 'success': return Response(status=200)
        order = payment.order
        if Decimal(str(event['data'].get('amount', 0))) != order.total * 100: return error('Payment amount does not match.', 400)
        for item in order.items.select_related('product', 'variant'):
            subject = item.variant or item.product
            if not subject or subject.stock_quantity < item.quantity: return error('Stock unavailable.', 409)
            subject.stock_quantity -= item.quantity; subject.save(update_fields=['stock_quantity'])
        payment.status = 'success'; payment.provider_response = event['data']; payment.save()
        authorization = event['data'].get('authorization') or {}
        if authorization.get('reusable') and authorization.get('authorization_code') and authorization.get('last4'):
            SavedPaymentMethod.objects.update_or_create(
                user=order.user, provider=Order.PAYSTACK, signature=authorization.get('signature') or authorization['authorization_code'],
                defaults={'authorization_code': authorization['authorization_code'], 'brand': authorization.get('brand') or authorization.get('card_type', ''), 'bank': authorization.get('bank', ''), 'last4': authorization['last4'], 'exp_month': authorization.get('exp_month'), 'exp_year': authorization.get('exp_year')},
            )
        order.payment_status = Order.PAID; order.save(update_fields=['payment_status', 'updated_at'])
    return Response(status=200)
