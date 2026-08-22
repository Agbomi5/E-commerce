from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import FileResponse
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def home(request):
    return FileResponse(
        open(settings.BASE_DIR / 'index.html', 'rb'),
        content_type='text/html'
    )


def frontend_file(request, filename):
    return FileResponse(
        open(settings.BASE_DIR / filename, 'rb')
    )


urlpatterns = [
    # Frontend
    path('', home, name='home'),
    path('index.html', home, name='index_html'),

    path('main.css', frontend_file, {'filename': 'main.css'}),
    path('main.js', frontend_file, {'filename': 'main.js'}),

    path('account.html', frontend_file, {'filename': 'account.html'}),
    path('auth.html', frontend_file, {'filename': 'auth.html'}),
    path('cart.html', frontend_file, {'filename': 'cart.html'}),
    path('category.html', frontend_file, {'filename': 'category.html'}),
    path('checkout.html', frontend_file, {'filename': 'checkout.html'}),
    path('product.html', frontend_file, {'filename': 'product.html'}),

    # Django admin
    path('admin/', admin.site.urls),

    # Django API
    path('api/', include('EcommerceApp.urls')),

    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )