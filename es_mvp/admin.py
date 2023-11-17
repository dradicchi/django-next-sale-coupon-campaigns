from django.contrib import admin

from .models import Customer, Sale, Campaign, Coupon, StoreSettings

admin.site.register(Customer)
admin.site.register(Sale)
admin.site.register(Campaign)
admin.site.register(Coupon)
admin.site.register(StoreSettings)
