from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    profile_picture_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.email


def unique_slug(instance, model, value):
    base = slugify(value) or 'item'
    slug, number = base, 2
    while model.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
        slug = f'{base}-{number}'
        number += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True, blank=True)
    image = models.FileField(upload_to='category_img', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, Category, self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='product_img', blank=True, null=True)
    featured = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='products', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def current_price(self):
        return self.sale_price if self.sale_price is not None else self.price

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, Product, self.name)
        if not self.sku:
            self.sku = f'AGB-{uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_img')
    alt_text = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=64, unique=True)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='product_img', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    @property
    def current_price(self):
        return self.price_override if self.price_override is not None else self.product.current_price

    def __str__(self):
        return f'{self.product.name} - {self.name}'


class Review(models.Model):
    RATING_CHOICES = [(number, f'{number} star') for number in range(1, 6)]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=RATING_CHOICES)
    review = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created']


class ProductRating(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='rating')
    average_rating = models.FloatField(default=0)
    total_reviews = models.PositiveIntegerField(default=0)


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=30)
    line1 = models.CharField(max_length=180)
    line2 = models.CharField(max_length=180, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    country = models.CharField(max_length=80, default='Nigeria')
    postal_code = models.CharField(max_length=24, blank=True)
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    def as_snapshot(self):
        return {field: getattr(self, field) for field in ('full_name', 'phone', 'line1', 'line2', 'city', 'state', 'country', 'postal_code')}


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']


class SavedPaymentMethod(models.Model):
    """A Paystack token and masked label; never a card number, CVV, or PIN."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_payment_methods')
    provider = models.CharField(max_length=32, default='paystack')
    authorization_code = models.CharField(max_length=128)
    signature = models.CharField(max_length=128)
    brand = models.CharField(max_length=80, blank=True)
    bank = models.CharField(max_length=100, blank=True)
    last4 = models.CharField(max_length=4)
    exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'provider', 'signature'], name='unique_user_payment_signature')]

    def __str__(self):
        return f'{self.brand or "Card"} •••• {self.last4}'


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.select_related('product', 'variant')), Decimal('0.00'))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cart', 'product', 'variant'], name='unique_cart_product_variant')]

    @property
    def available_stock(self):
        return self.variant.stock_quantity if self.variant else self.product.stock_quantity

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Coupon(models.Model):
    PERCENTAGE, FIXED = 'percentage', 'fixed'
    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=12, choices=[(PERCENTAGE, 'Percentage'), (FIXED, 'Fixed')])
    value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    starts_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def discount_for(self, subtotal):
        now = timezone.now()
        if not self.is_active or (self.starts_at and self.starts_at > now) or (self.expires_at and self.expires_at < now) or (self.usage_limit is not None and self.used_count >= self.usage_limit) or subtotal < self.minimum_order_amount:
            raise ValueError('This coupon is not valid for this cart.')
        discount = subtotal * self.value / Decimal('100') if self.discount_type == self.PERCENTAGE else self.value
        return min(discount, subtotal)


class ShippingRate(models.Model):
    state = models.CharField(max_length=80, blank=True, help_text='Leave blank for a nationwide rate')
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)


class Order(models.Model):
    PENDING, PAID, FAILED, REFUNDED = 'pending', 'paid', 'failed', 'refunded'
    NEW, PROCESSING, SHIPPED, DELIVERED, CANCELLED = 'new', 'processing', 'shipped', 'delivered', 'cancelled'
    PAYSTACK, COD, BANK_TRANSFER = 'paystack', 'cash_on_delivery', 'bank_transfer'
    PAYMENT_METHOD_CHOICES = [
        (PAYSTACK, 'Card / Bank (Paystack)'),
        (COD, 'Cash on Delivery'),
        (BANK_TRANSFER, 'Bank Transfer'),
    ]
    number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    shipping_address = models.JSONField()
    billing_address = models.JSONField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    coupon_code = models.CharField(max_length=40, blank=True)
    payment_status = models.CharField(max_length=12, choices=[(x, x.title()) for x in (PENDING, PAID, FAILED, REFUNDED)], default=PENDING)
    fulfillment_status = models.CharField(max_length=16, choices=[(x, x.title()) for x in (NEW, PROCESSING, SHIPPED, DELIVERED, CANCELLED)], default=NEW)
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES, default=PAYSTACK)
    tracking_number = models.CharField(max_length=100, blank=True)
    customer_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = f'AGB-{timezone.now():%Y%m%d}-{uuid4().hex[:7].upper()}'
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=160)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class PaymentTransaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=32, default='paystack')
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=24, default='initialized')
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SiteSetting(models.Model):
    company_name = models.CharField(max_length=120, default='A M TECH SOLUTIONS')
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    twitter_handle = models.CharField(max_length=60, blank=True, help_text='Without @')
    facebook_handle = models.CharField(max_length=60, blank=True, help_text='Username or page slug')
    instagram_handle = models.CharField(max_length=60, blank=True, help_text='Without @')
    linkedin_handle = models.CharField(max_length=60, blank=True, help_text='Username or page slug')
    bank_name = models.CharField(max_length=120, blank=True, help_text='e.g. GTBank')
    bank_account_name = models.CharField(max_length=160, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_instructions = models.TextField(blank=True, help_text='Instructions shown to customers during bank transfer checkout')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site setting'
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return self.company_name

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
