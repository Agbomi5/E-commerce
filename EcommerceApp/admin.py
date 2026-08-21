from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Address, Cart, CartItem, Category, Coupon, CustomUser, Order, OrderItem, PaymentTransaction, Product, ProductImage, ProductRating, ProductVariant, Review, SavedPaymentMethod, ShippingRate, SiteSetting, WishlistItem

admin.site.register(CustomUser, UserAdmin)

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'support_email', 'support_phone', 'bank_name', 'updated_at')
    fieldsets = (
        ('Company', {'fields': ('company_name',)}),
        ('Support', {'fields': ('support_email', 'support_phone')}),
        ('Social Media', {'fields': ('twitter_handle', 'facebook_handle', 'instagram_handle', 'linkedin_handle')}),
        ('Bank Transfer', {'fields': ('bank_name', 'bank_account_name', 'bank_account_number', 'bank_instructions')}),
    )

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'alt_text', 'sort_order')
    verbose_name = 'Additional product image'
    verbose_name_plural = 'Product gallery images'
class ProductVariantInline(admin.TabularInline): model = ProductVariant; extra = 1
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'sale_price', 'stock_quantity', 'featured', 'is_active')
    list_filter = ('featured', 'is_active', 'category')
    search_fields = ('name', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'user', 'total', 'payment_status', 'fulfillment_status', 'created_at')
    list_filter = ('payment_status', 'fulfillment_status', 'payment_method')
    search_fields = ('number', 'user__email', 'tracking_number')
    readonly_fields = ('number', 'subtotal', 'shipping_fee', 'discount', 'total', 'created_at', 'updated_at')

for model in (Category, Review, ProductRating, Address, Cart, CartItem, WishlistItem, SavedPaymentMethod, Coupon, ShippingRate, OrderItem, PaymentTransaction):
    admin.site.register(model)
