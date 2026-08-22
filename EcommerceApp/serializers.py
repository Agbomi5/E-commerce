from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Address, Cart, CartItem, Category, Order, OrderItem, PaymentTransaction, Product, ProductImage, ProductRating, ProductVariant, Review, SavedPaymentMethod, SiteSetting, WishlistItem


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_picture_url']
        read_only_fields = ['id', 'email']


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name']
    def create(self, validated_data):
        user = get_user_model()(**validated_data)
        user.set_unusable_password()
        user.save()
        return user


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'sort_order']


class ProductVariantSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'price_override', 'current_price', 'stock_quantity', 'image', 'is_active']


class ProductListSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'sale_price', 'current_price', 'slug', 'image', 'featured', 'sku', 'stock_quantity', 'in_stock', 'rating']
    def get_in_stock(self, obj): return obj.stock_quantity > 0 or obj.variants.filter(is_active=True, stock_quantity__gt=0).exists()
    def get_rating(self, obj):
        try: rating = obj.rating
        except ProductRating.DoesNotExist: return {'average_rating': 0, 'total_reviews': 0}
        return {'average_rating': rating.average_rating, 'total_reviews': rating.total_reviews}
    def get_image(self, obj):
        from django.conf import settings
        if not obj.image:
            return None
        if settings.USE_CLOUDINARY:
            import cloudinary
            try:
                return cloudinary.CloudinaryImage(str(obj.image)).build_url()
            except:
                pass
        url = obj.image.url
        if url.startswith('/'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'review', 'created', 'updated']
        read_only_fields = ['user', 'created', 'updated']


class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating
        fields = ['average_rating', 'total_reviews']


class ProductDetailSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    reviews = ReviewSerializer(many=True, read_only=True)
    rating = ProductRatingSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    similar_products = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'sale_price', 'current_price', 'sku', 'stock_quantity', 'is_active', 'metadata', 'slug', 'image', 'featured', 'category', 'images', 'variants', 'reviews', 'rating', 'similar_products']
    def get_similar_products(self, product):
        return ProductListSerializer(Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:6], many=True, context=self.context).data
    def get_image(self, obj):
        from django.conf import settings
        if not obj.image:
            return None
        if settings.USE_CLOUDINARY:
            import cloudinary
            try:
                return cloudinary.CloudinaryImage(str(obj.image)).build_url()
            except:
                pass
        url = obj.image.url
        if url.startswith('/'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url


class CategoryListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'slug']
    def get_image(self, obj):
        from django.conf import settings
        if not obj.image:
            return None
        if settings.USE_CLOUDINARY:
            import cloudinary
            try:
                return cloudinary.CloudinaryImage(str(obj.image)).build_url()
            except:
                pass
        url = obj.image.url
        if url.startswith('/'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url


class CategoryDetailSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'slug', 'products']
    def get_image(self, obj):
        from django.conf import settings
        if not obj.image:
            return None
        if settings.USE_CLOUDINARY:
            import cloudinary
            try:
                return cloudinary.CloudinaryImage(str(obj.image)).build_url()
            except:
                pass
        url = obj.image.url
        if url.startswith('/'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return url


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'full_name', 'phone', 'line1', 'line2', 'city', 'state', 'country', 'postal_code', 'is_default_shipping', 'is_default_billing']


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()
    class Meta:
        model = SavedPaymentMethod
        fields = ['id', 'provider', 'brand', 'bank', 'last4', 'exp_month', 'exp_year', 'label', 'created_at']
    def get_label(self, obj):
        expiry = f' · expires {obj.exp_month:02d}/{obj.exp_year}' if obj.exp_month and obj.exp_year else ''
        return f'{obj.brand or "Card"} •••• {obj.last4}{expiry}'


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(source='product', queryset=Product.objects.filter(is_active=True), write_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(source='variant', queryset=ProductVariant.objects.filter(is_active=True), write_only=True, required=False, allow_null=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'variant', 'product_id', 'variant_id', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['unit_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    class Meta:
        model = Cart
        fields = ['id', 'items', 'subtotal', 'coupon', 'updated_at']


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product_name', 'sku', 'unit_price', 'quantity', 'line_total']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['reference', 'provider', 'amount', 'status', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'number', 'items', 'shipping_address', 'billing_address', 'subtotal', 'shipping_fee', 'discount', 'total', 'coupon_code', 'payment_status', 'fulfillment_status', 'payment_method', 'tracking_number', 'customer_note', 'payments', 'created_at']


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['company_name', 'support_email', 'support_phone', 'twitter_handle', 'facebook_handle', 'instagram_handle', 'linkedin_handle', 'bank_name', 'bank_account_name', 'bank_account_number', 'bank_instructions']
