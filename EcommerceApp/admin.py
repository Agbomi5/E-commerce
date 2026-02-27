from django.contrib import admin
from .models import CustomUser, Category, Product, Review, ProductRating
from django.contrib.auth.admin import UserAdmin

# Register your models here.
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
admin.site.register(CustomUser, CustomUserAdmin)


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'featured']
admin.site.register(Product, ProductAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
admin.site.register(Category, CategoryAdmin)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'rating', 'review', 'created', 'updated']
admin.site.register(Review, ReviewAdmin)


class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'average_rating', 'total_reviews')
admin.site.register(ProductRating, ProductRatingAdmin)

