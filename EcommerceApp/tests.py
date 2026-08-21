import json
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import Client
from django.test import override_settings
from rest_framework.test import APIClient
from .models import Address, Cart, CartItem, Category, Coupon, Product, ShippingRate, WishlistItem

class CommerceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ada', email='ada@example.com', password='strong-password')
        self.product = Product.objects.create(name='Phone', description='A phone', price=Decimal('1000.00'), stock_quantity=3)
        self.client = APIClient(); self.client.login(username='ada', password='strong-password')

    def test_cart_rejects_more_than_stock(self):
        response = self.client.post('/cart/items/', {'product_id': self.product.id, 'quantity': 4}, format='json')
        self.assertEqual(response.status_code, 400)

    @override_settings(PAYSTACK_SECRET_KEY='sk_test_configured')
    def test_cart_and_checkout(self):
        self.client.post('/cart/items/', {'product_id': self.product.id, 'quantity': 2}, format='json')
        address = Address.objects.create(user=self.user, full_name='Ada', phone='0800', line1='1 Main', city='Lagos', state='Lagos')
        ShippingRate.objects.create(name='Lagos', state='Lagos', amount=Decimal('500.00'))
        response = self.client.post('/orders/create/', {'shipping_address_id': address.id, 'billing_address_id': address.id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(response.data['total']), Decimal('2500.00'))
        self.assertEqual(response.data['payment_status'], 'pending')
        self.assertEqual(response.data['fulfillment_status'], 'new')

    def test_checkout_does_not_create_an_order_without_payment_configuration(self):
        self.client.post('/cart/items/', {'product_id': self.product.id, 'quantity': 1}, format='json')
        address = Address.objects.create(user=self.user, full_name='Ada', phone='0800', line1='1 Main', city='Lagos', state='Lagos')
        ShippingRate.objects.create(name='Lagos', state='Lagos', amount=Decimal('500.00'))
        response = self.client.post('/orders/create/', {'shipping_address_id': address.id, 'billing_address_id': address.id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.user.orders.exists())

    def test_review_requires_authentication(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post('/add_review/', {'product_id': self.product.id, 'rating': 5, 'review': 'Great'}, format='json').status_code, 403)

    def test_customer_can_change_their_rating(self):
        first = self.client.post('/add_review/', {'product_id': self.product.id, 'rating': 3, 'review': 'Okay'}, format='json')
        updated = self.client.post('/add_review/', {'product_id': self.product.id, 'rating': 5, 'review': 'Excellent'}, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.product.reviews.get(user=self.user).rating, 5)

    def test_coupon_rules(self):
        coupon = Coupon.objects.create(code='SAVE10', discount_type=Coupon.PERCENTAGE, value=Decimal('10.00'), minimum_order_amount=Decimal('500.00'))
        self.assertEqual(coupon.discount_for(Decimal('1000.00')), Decimal('100.00'))
        with self.assertRaises(ValueError):
            coupon.discount_for(Decimal('100.00'))

    def test_email_only_login(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post('/auth/login/', {'email': self.user.email}, format='json').status_code, 200)

    def test_wishlist_can_save_list_and_remove_a_product(self):
        save = self.client.post(f'/wishlist/{self.product.id}/')
        self.assertEqual(save.status_code, 201)
        self.assertEqual(self.client.get('/wishlist/').data[0]['product']['id'], self.product.id)
        self.assertEqual(self.client.delete(f'/wishlist/{self.product.id}/').status_code, 204)
        self.assertFalse(WishlistItem.objects.filter(user=self.user, product=self.product).exists())

    def test_cross_origin_cart_and_logout_accept_csrf_token(self):
        client = Client(enforce_csrf_checks=True, HTTP_ORIGIN='http://127.0.0.1:8001')
        client.get('/auth/csrf/')
        token = client.cookies['csrftoken'].value
        login_response = client.post('/auth/login/', json.dumps({'email': self.user.email}), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(login_response.status_code, 200)
        # Django rotates the CSRF token when a user signs in.
        token = client.cookies['csrftoken'].value
        cart_response = client.post('/cart/items/', json.dumps({'product_id': self.product.id, 'quantity': 1}), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(cart_response.status_code, 201)
        self.assertEqual(client.post('/auth/logout/', content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 204)
