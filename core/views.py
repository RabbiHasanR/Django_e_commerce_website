from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView,DetailView,View
from .models import Item,Order,OrderItem
from django.utils import timezone

# Create your views here.

class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = 'home-page.html'

class OrderSummaryView(LoginRequiredMixin,View):
    def get(self,*args,**kwargs):
        try:
            order=Order.objects.get(user=self.request.user,ordered=False)
            context={
                'object':order
            }
            return render(self.request, 'order_summary.html',context)
        except ObjectDoesNotExist:
            messages.error(self.request,'You don"t have active order')
            return redirect('/')


def checkout(request):
    context={}

    return render(request,'checkout-page.html',context)

class ProductDetailView(DetailView):
    model = Item
    template_name = 'product-page.html'

@login_required
def add_to_cart(request,slug):
    item=get_object_or_404(Item,slug=slug)
    order_item,created=OrderItem.objects.get_or_create(item=item,user=request.user,ordered=False)
    order_qs=Order.objects.filter(user=request.user,ordered=False)

    if order_qs.exists():
        order=order_qs[0]
        #check if order item in order

        if order.item.filter(item__slug=item.slug).exists():
            order_item.quantity+=1
            order_item.save()
            messages.info(request, 'This item quantity updated.')
            return redirect('core:order-summary')
        else:
            order.item.add(order_item)
            messages.info(request, 'This item was added your cart.')
            return redirect('core:order-summary')
    else:
        order_date=timezone.now()
        order=Order.objects.create(user=request.user,ordered_date=order_date)
        order.item.add(order_item)
        messages.info(request, 'This item was added your cart.')
        return redirect('core:order-summary')

@login_required
def remove_form_cart(request,slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order=order_qs[0]
        #check if order item in order

        if order.item.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            order.item.remove(order_item)
            messages.info(request, 'This item was removed your cart.')
            return redirect('core:order-summary')
        else:
            # add message saying item was not your cart
            messages.info(request, 'This item was not your cart.')
            return redirect('core:product-detail', slug=slug)
    else:
        # add message saying user doesn't have order
        messages.info(request, 'You don"t have active order.')
        return redirect('core:product-detail', slug=slug)


@login_required
def remove_single_item_form_cart(request,slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)

    if order_qs.exists():
        order=order_qs[0]
        #check if order item in order

        if order.item.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(item=item, user=request.user, ordered=False)[0]
            if order_item.quantity >1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.item.remove(order_item)
            messages.info(request, 'This item quantity was updated.')
            return redirect('core:order-summary')
        else:
            # add message saying item was not your cart
            messages.info(request, 'This item was not your cart.')
            return redirect('core:product-detail', slug=slug)
    else:
        # add message saying user doesn't have order
        messages.info(request, 'You don"t have active order.')
        return redirect('core:product-detail', slug=slug)