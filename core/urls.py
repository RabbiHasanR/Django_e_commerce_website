from django.urls import path
from .views import checkout,HomeView,ProductDetailView,\
    add_to_cart,remove_form_cart,OrderSummaryView,remove_single_item_form_cart

app_name='core'
urlpatterns=[
    path('',HomeView.as_view(),name='item-list'),
    path('checkout/',checkout,name='checkout'),
    path('order-summary/',OrderSummaryView.as_view(),name='order-summary'),
    path('product/<slug>/',ProductDetailView.as_view(),name='product-detail'),
    path('add-to-cart/<slug>/',add_to_cart,name='add-to-cart'),
    path('remove-from-cart/<slug>/',remove_form_cart,name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/',remove_single_item_form_cart,name='remove-single-item-from-cart'),
]