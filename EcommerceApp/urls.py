#from django.contrib import admin
from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
#from django.contrib import admin
#from EcommerceApp import admin
from . import views



urlpatterns = [
    #path('admin/', admin.site.urls),
    path('product_list/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('add_review/', views.add_review, name='add_review'),
    path('update_review/<int:pk>/', views.update_review, name='update_review'),
    path('delete_review/<int:pk>/', views.delete_review, name='delete_review'),
    path('search/', views.product_search, name='product_search'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/exists/<str:email>/', views.existing_user, name='existing_user'),
]

#if settings.DEBUG:
   # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)