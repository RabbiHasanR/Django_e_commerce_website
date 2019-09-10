from django.shortcuts import render
from django.views.generic import ListView,DetailView
from .models import Item

# Create your views here.

class HomeView(ListView):
    model = Item
    template_name = 'home-page.html'


def checkout(request):
    context={}

    return render(request,'checkout-page.html',context)

def product_detail(request):
    context={}
    return render(request,'product-page.html',context)

class ProductDetailView(DetailView):
    model = Item
    template_name = 'product-page.html'
