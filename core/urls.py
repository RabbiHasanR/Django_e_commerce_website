from django.urls import path
from .views import checkout,product_detail,HomeView,ProductDetailView

app_name='core'
urlpatterns=[
    path('',HomeView.as_view(),name='item-list'),
    path('checkout/',checkout,name='checkout'),
    path('product/<slug>/',ProductDetailView.as_view(),name='product-detail')
]