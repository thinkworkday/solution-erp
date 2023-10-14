"""erpSolution URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings

from dashboard.views import handler404, handler500
import notifications.urls

handler404 = handler404
handler500 = handler500

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^', include('accounts.urls')),
    url(r'^', include('dashboard.urls')),
    url(r'^', include('sales.urls')),
    url(r'^', include('project.urls')),
    url(r'^', include('inventory.urls')),
    url(r'^', include('userprofile.urls')),
    url(r'^', include('maintenance.urls')),
    url(r'^', include('expenseclaim.urls')),
    url(r'^', include('siteprogress.urls')),
    url(r'^', include('toolbox.urls')),
    url('^inbox/notifications/', include(notifications.urls, namespace='notifications')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
