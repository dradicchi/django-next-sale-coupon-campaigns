"""
Defines URL patterns for 'es_mvp' app.
"""
from django.urls import path
from django.views.generic.base import TemplateView
from . import views

app_name = 'es_mvp'

urlpatterns = [
    # Home page.
    path('', views.home, name='home'),
    # Page that list all sales.
    path('sales/', views.sales, name='sales'),
    # Detail page for a sale.
    path('sales/<int:sale_id>/', views.sale, name='sale'),
    # Page for adding a complete new sale.
    path('new_sale/', views.new_sale, name='new_sale'),
    # Page that list all campaigns.
    path('campaigns/', views.campaigns, name='campaigns'),
    # Detail page for a campaign.
    path('campaigns/<int:campaign_id>/', views.campaign, name='campaign'),
    # Page for adding a new campaign.
    path('new_campaign/', views.new_campaign, name='new_campaign'),
    # Page for editing a campaign.
    path('edit_campaign/<int:campaign_id>/', views.edit_campaign,
            name='edit_campaign'),
    # Page that list all coupons.
    path('coupons/', views.coupons, name='coupons'),
    # Detail page for a coupon.
    path('coupons/<int:coupon_id>/', views.coupon, name='coupon'),
    # Page that shows the store settings.
    path('edit_store_settings/', views.edit_store_settings, 
            name='edit_store_settings'),
    # Rules to third-party crawler services.
    path('robots.txt', TemplateView.as_view(
        template_name="es_mvp/robots.txt", content_type="text/plain"), 
            name='robots_txt'),
    ]  

