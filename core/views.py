from django.conf import settings
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import ListView,DetailView,View
from .models import Item,Order,OrderItem,BillingAddress,Payment,Cupon,Refund
from .forms import CheckoutForm,CuponForm,RefundForm
from django.utils import timezone

import random
import string
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.

def create_ref_code():
    return '.'.join(random.choice(string.ascii_lowercase + string.digits))

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


class CheckoutView(View):
    def get(self,*args,**kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form=CheckoutForm()
            context={
                'form':form,
                'couponForm':CuponForm(),
                'order':order,
                'DISPLAY_COUPON_FORM': True,
            }
            return render(self.request,'checkout-page.html',context)
        except ObjectDoesNotExist:
            messages.info(self.request, 'You don not have an active order')
            return redirect('core:checkout')

    def post(self,*args,**kwargs):
        form=CheckoutForm(self.request.POST or None)
        try:
            order=Order.objects.get(user=self.request.user,ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                zip = form.cleaned_data.get('zip')
                # TODO: Add functionality for these fields
                # same_shipping_address = form.cleaned_data.get(' same_shipping_address')
                # save_info = form.cleaned_data.get('save_info')
                payment_options = form.cleaned_data.get('payment_options')
                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    zip=zip
                )
                billing_address.save()
                order.billing_address=billing_address
                order.save()
                if payment_options=='S':
                    return redirect('core:payment',payment_option='stripe')
                elif payment_options=='P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(self.request,'Invalid payment options selected')
                    return redirect('core:checkout')
            messages.warning(self.request,'Failed Checkout')
            return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request,'You don"t have active order')
            return redirect('core:order-summary')

class PaymentView(View):
    def get(self,*args,**kwargs):
        #order
        order=Order.objects.get(user=self.request.user,ordered=False)
        if order.billing_address:
            context={
                'order':order,
                'DISPLAY_COUPON_FORM':False
            }
            return render(self.request,'payment.html',context)
        else:
            messages.error(self.request, 'You did not added a billing address')
            return redirect('core:checkout')

    def post(self,*args,**kwargs):
        token=self.request.POST.get('stripeToken')
        order=Order.objects.get(user=self.request.user,ordered=False)
        amount=int(order.get_total_order_price() * 100)

        try:
            charge = stripe.Charge.create(
                amount=amount,  # cents
                currency="usd",
                source=token,  # obtained with Stripe.js
                description="Charge for jenny.rosen@example.com"
            )

            # Create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total_order_price()
            payment.save()

            # Assign the payment to the order
            order_items=order.item.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            order.ordered = True
            order.payment = payment
            order.ref_code=create_ref_code()
            order.save()

            messages.success(self.request,'Your order was successful')
            return redirect('/')
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error', {})

            messages.error(self.request,f"{err.get('message')}")
            return redirect('/')
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request,'Rate limit error')
            return redirect('/')
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request,'Invalid request error')
            return redirect('/')
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request,'Authentication error')
            return redirect('/')
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request,'Api connection error')
            return redirect('/')
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request,'Stripe error')
            return redirect('/')
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            messages.error(self.request,'A serious error occurred.we have been notify')
            print('error:',e)
            return redirect('/')

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

def get_cupon(request,code):
    try:
        coupon = Cupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request,'This coupon does not exit')
        return redirect('core:checkout')

class AddCouponView(View):
    def post(self,*args,**kwargs):
        form=CuponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code=form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon=get_cupon(self.request,code)
                order.save()
                messages.success(self.request,'Successfully add coupon')
                return redirect('core:checkout')
            except ObjectDoesNotExist:
                messages.info(self.request,'You don not have an active order')
                return redirect('core:checkout')


class RequestRefundView(View):
    def get(self,*args,**kwargs):
        form=RefundForm()
        context={
            'form':form
        }
        return render(self.request,'request_refund.html',context)
    def post(self,*args,**kwargs):
        form=RefundForm(self.request.POST or None)
        if form.is_valid():
            ref_code=form.cleaned_data.get('ref_code')
            message=form.cleaned_data.get('message')
            email=form.cleaned_data.get('email')
            try:
                # edit the order
                order=Order.objects.get(ref_code=ref_code)
                order.refund_request=True
                order.save()

                # Store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()
                messages.info(self.request, 'Your request was received')
                return redirect('core:request-refund')
            except ObjectDoesNotExist:
                messages.info(self.request, 'The order does not exist')
                return redirect('core:request-refund')
